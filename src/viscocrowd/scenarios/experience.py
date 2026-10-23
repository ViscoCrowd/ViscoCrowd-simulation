"""Configuration -> banc d'essai existant -> archive exploitable hors ligne."""

import json
import platform
from dataclasses import asdict
from pathlib import Path

import numpy as np

from viscocrowd import __version__
from viscocrowd.io.configuration import lire_configuration
from viscocrowd.io.provenance import provenance_code
from viscocrowd.io.trajectoires import Trajectoire, ecrire_trajectoire
from viscocrowd.scenarios.bille_boite import ParametresBille, simuler_bille
from viscocrowd.scenarios.couloir import ParametresCouloir, simuler_couloir
from viscocrowd.scenarios.piscine import (
    NOMS_ETATS,
    ParametresPiscine,
    ResultatPiscine,
    simuler_piscine,
)
from viscocrowd.scenarios.tassement import (
    ParametresTassement,
    positions_initiales,
    simuler_tassement,
)


def _parametres(
    config: dict,
) -> ParametresBille | ParametresTassement | ParametresCouloir | ParametresPiscine:
    for nom, classe in (("couloir", ParametresCouloir), ("piscine", ParametresPiscine)):
        if config["scenario"] == nom:
            try:
                return classe(**config["parametres"], graine=config["graine"])
            except TypeError as erreur:
                raise ValueError(
                    f"parametres de {nom} manquants ou inconnus : {erreur}"
                ) from erreur
    classe = ParametresBille if config["scenario"] == "bille_boite" else ParametresTassement
    valeurs = asdict(classe())
    valeurs.pop("graine", None)
    inconnus = set(config["parametres"]) - set(valeurs)
    if inconnus:
        raise ValueError(f"parametres inconnus : {sorted(inconnus)}")
    valeurs.update(config["parametres"])
    for nom, valeur in valeurs.items():
        if nom == "n_agents":
            if type(valeur) is not int or valeur <= 0:
                raise ValueError("n_agents doit etre un entier strictement positif")
        elif nom in ("gravite", "position_initiale", "vitesse_initiale"):
            tableau = np.asarray(valeur)
            if tableau.shape != (2,) or tableau.dtype.kind not in "fiu":
                raise ValueError(f"{nom} doit etre un vecteur de deux nombres reels")
            valeurs[nom] = tableau.astype(float)
        elif type(valeur) not in (int, float):
            raise ValueError(f"{nom} doit etre un nombre reel")
        if not np.all(np.isfinite(valeurs[nom])):
            raise ValueError(f"{nom} doit etre fini")
        if nom in ("demi_largeur", "rayon", "masse", "dt", "tolerance") and valeur <= 0:
            raise ValueError(f"{nom} doit etre strictement positif")
    if valeurs["duree"] < 0:
        raise ValueError("duree doit etre positive ou nulle")
    if valeurs["rayon"] >= valeurs["demi_largeur"]:
        raise ValueError("rayon doit etre inferieur a demi_largeur")
    if classe is ParametresTassement:
        return classe(**valeurs, graine=config["graine"])
    return classe(**valeurs)


def executer_configuration(
    configuration: str | Path, sortie: str | Path, *, archiver_tous: int = 1
) -> Trajectoire:
    """Archive uniquement un calcul fini, confine et converge ; aucun affichage."""
    code = provenance_code()
    config = lire_configuration(configuration)
    p = _parametres(config)
    if type(archiver_tous) is not int or archiver_tous < 1:
        raise ValueError("archiver_tous doit etre un entier strictement positif")
    if archiver_tous != 1 and not isinstance(p, ParametresPiscine):
        raise ValueError("l'archivage espace est disponible pour le scenario piscine")
    if Path(sortie).exists():
        raise FileExistsError(f"la sortie existe deja : {sortie}")
    if Path(sortie).suffix != ".npz":
        raise ValueError("la trajectoire doit porter l'extension .npz")
    # Une projection ne doit pas masquer une configuration initiale inadmissible.
    if isinstance(p, (ParametresCouloir, ParametresPiscine)):
        initiales = np.empty((0, 2))  # placement deja controle par les parametres
    elif isinstance(p, ParametresTassement):
        initiales = positions_initiales(p)
    else:
        c, s = np.cos(p.theta0), np.sin(p.theta0)
        initiales = np.asarray(p.position_initiale) @ np.array([[c, -s], [s, c]])
    if not isinstance(p, (ParametresCouloir, ParametresPiscine)) and np.any(
        np.abs(initiales) + p.rayon > p.demi_largeur
    ):
        raise ValueError("positions initiales hors de la boite")

    evenements = None
    if isinstance(p, (ParametresTassement, ParametresCouloir, ParametresPiscine)):
        if isinstance(p, ParametresPiscine):
            resultat = simuler_piscine(p, archiver_tous=archiver_tous)
            evenements = _evenements_piscine(resultat)
        elif isinstance(p, ParametresCouloir):
            resultat = simuler_couloir(p)
        else:
            resultat = simuler_tassement(p)
        resultat.projection.verifier_convergence()
        parois = resultat.violation_paroi_max()
        validation = {
            "non_convergences": resultat.projection.non_convergences,
            "recouvrement_max_m": resultat.projection.recouvrement_max,
        }
    else:
        resultat = simuler_bille(p)
        parois = resultat.violation_max()
        validation = {}
    if not parois <= 1e-14:
        raise ValueError(f"violation des parois : {parois} m > 1e-14 m")
    validation["violation_paroi_max_m"] = parois
    brut = p.en_dictionnaire() if isinstance(p, ParametresPiscine) else asdict(p)
    effectifs = json.loads(json.dumps(brut, default=lambda v: v.tolist(), allow_nan=False))
    effectifs.pop("graine", None)
    metadonnees_evenements = {} if evenements is None else {"evenements": evenements}
    etats = None
    if isinstance(p, ParametresPiscine):
        # Sans les etats, un sorti pose au point `dehors` ou un agent pose sur le bord
        # serait relu comme un disque actif par un controle hors ligne.
        etats = resultat.etats
        metadonnees_evenements["etats"] = list(NOMS_ETATS)  # nom du code k : etats[k]
    if provenance_code() != code:
        raise ValueError(
            "la provenance du code a change pendant le calcul ; "
            "relancer avec un depot stable avant d'archiver"
        )
    donnees = Trajectoire(
        t=resultat.t,
        x=resultat.x,
        v=resultat.v,
        rayons=np.full(resultat.x.shape[1], p.rayon),
        metadonnees={
            "configuration": {**config, "parametres": effectifs},
            "versions": {
                "viscocrowd": __version__,
                "python": platform.python_version(),
                "numpy": np.__version__,
            },
            "code": code,
            "unites": {"t": "s", "x": "m", "v": "m/s", "rayons": "m"},
            "validation": validation,
            "archivage": {
                "tous_les_pas": archiver_tous,
                "dt_simulation_s": p.dt,
                "premier_et_dernier_instants": True,
                "validation_tous_les_pas": True,
            },
            **metadonnees_evenements,
        },
        etats=etats,
    )
    ecrire_trajectoire(sortie, donnees)
    return donnees


def _evenements_piscine(resultat: ResultatPiscine) -> dict:
    """Franchissements et sorties en JSON ; un agent jamais sorti a une sortie nulle."""
    return {
        "franchissements": [
            {
                "agent": int(a),
                "site": int(k),
                "nature": resultat.natures[int(k)],
                "debut": d,
                "fin": f,
            }
            for a, k, d, f in resultat.franchissements.tolist()
        ],
        "sorties": [float(s) if np.isfinite(s) else None for s in resultat.sorties],
        "unites": {"debut": "s", "fin": "s", "sorties": "s"},
    }
