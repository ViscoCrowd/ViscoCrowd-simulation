"""Configuration -> banc d'essai existant -> archive exploitable hors ligne."""

import platform
from dataclasses import asdict
from pathlib import Path

import numpy as np

from viscocrowd import __version__
from viscocrowd.io.configuration import lire_configuration
from viscocrowd.io.trajectoires import Trajectoire, ecrire_trajectoire
from viscocrowd.scenarios.bille_boite import ParametresBille, simuler_bille
from viscocrowd.scenarios.tassement import (
    ParametresTassement,
    positions_initiales,
    simuler_tassement,
)


def _parametres(config: dict) -> ParametresBille | ParametresTassement:
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


def executer_configuration(configuration: str | Path, sortie: str | Path) -> Trajectoire:
    """Archive uniquement un calcul fini, confine et converge ; aucun affichage."""
    config = lire_configuration(configuration)
    p = _parametres(config)
    if Path(sortie).exists():
        raise FileExistsError(f"la sortie existe deja : {sortie}")
    if Path(sortie).suffix != ".npz":
        raise ValueError("la trajectoire doit porter l'extension .npz")
    # Une projection ne doit pas masquer une configuration initiale inadmissible.
    if isinstance(p, ParametresTassement):
        initiales = positions_initiales(p)
    else:
        c, s = np.cos(p.theta0), np.sin(p.theta0)
        initiales = np.asarray(p.position_initiale) @ np.array([[c, -s], [s, c]])
    if np.any(np.abs(initiales) + p.rayon > p.demi_largeur):
        raise ValueError("positions initiales hors de la boite")

    if isinstance(p, ParametresTassement):
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
    effectifs = {k: v.tolist() if isinstance(v, np.ndarray) else v for k, v in asdict(p).items()}
    effectifs.pop("graine", None)
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
            "unites": {"t": "s", "x": "m", "v": "m/s", "rayons": "m"},
            "validation": validation,
        },
    )
    ecrire_trajectoire(sortie, donnees)
    return donnees
