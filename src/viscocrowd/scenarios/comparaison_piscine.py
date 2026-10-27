"""Comparaison appariee E1/E2 : effet du sol mouille sur l'evacuation de piscine.

Dans la continuite de la comparaison du couloir (issue #50) et des objectifs du
jalon J5 (issue #59), ce protocole separe les composantes du sol mouille sur le
scenario complet de la piscine :

  - E1 (reference) : sol mouille strictement identique au sec ;
  - vitesse : seule la vitesse de consigne sur carrelage mouille change ;
  - relaxation : seul le temps de relaxation sur carrelage mouille change ;
  - adherence : seule l'acceleration maximale admissible change ;
  - vitesse+adherence : vitesse de consigne et adherence changent ;
  - E2 (complet) : sol mouille reel avec l'ensemble de ses parametres.

Mesures par graine et par variante :
  - t50, t90, t100 : instants d'evacuation definitive (en s), delegues a Sorties ;
  - attente_eau : temps moyen passe dans le bassin avant franchissement (en s) ;
  - duree_plage : temps moyen de traversee de la plage jusqu'a la porte (en s) ;
  - debit_porte : debit specifique moyen au passage de la porte (en pers/(m.s)) ;
  - non_sortis : nombre d'agents encore presents a la fin de l'horizon de calcul.

Les populations initiales et les graines sont strictement appariees pour que les
ecarts mesures ne relevent que des proprietes physiques des milieux.
"""

from __future__ import annotations

import math
from dataclasses import replace

import numpy as np

from viscocrowd.model.milieu import ParametresMilieu
from viscocrowd.scenarios.piscine import ParametresPiscine, simuler_piscine

VARIANTES: dict[str, tuple[str, ...]] = {
    "reference": (),
    "vitesse": ("vitesse",),
    "relaxation": ("relaxation",),
    "adherence": ("acceleration_max",),
    "vitesse+adherence": ("vitesse", "acceleration_max"),
    "complet": ("vitesse", "relaxation", "acceleration_max"),
}

LIBELLES = {
    "reference": "référence (mouillé = sec, E1)",
    "vitesse": "vitesse seule",
    "relaxation": "relaxation seule",
    "adherence": "adhérence seule",
    "vitesse+adherence": "vitesse + adhérence",
    "complet": "complet (sol mouillé réel, E2)",
}

MESURES = ("t50", "t90", "t100", "attente_eau", "duree_plage", "debit_porte", "non_sortis")
UNITES = {
    "t50": "s",
    "t90": "s",
    "t100": "s",
    "attente_eau": "s",
    "duree_plage": "s",
    "debit_porte": "pers/(m.s)",
    "non_sortis": "pers",
}


def mouille_de_variante(
    nom: str, sec: ParametresMilieu, mouille: ParametresMilieu
) -> ParametresMilieu:
    """Parametres du mouille pour une variante : ceux du sec, sauf ceux qu'elle reprend."""
    if nom not in VARIANTES:
        raise ValueError(f"variante inconnue {nom!r} ; attendu : {', '.join(VARIANTES)}")
    return replace(sec, **{champ: getattr(mouille, champ) for champ in VARIANTES[nom]})


def mesurer(p: ParametresPiscine) -> dict[str, float]:
    """Execute le scenario piscine et extrait les observables d'evacuation.

    Args:
        p: configuration physique complete du scenario piscine.

    Returns:
        Dictionnaire associant chaque indicateur de MESURES a sa valeur scalaire.
    """
    r = simuler_piscine(p)
    sortis_instants = np.sort(r.sorties[np.isfinite(r.sorties)])
    n = p.n_agents
    non_sortis = float(n - len(sortis_instants))

    t50 = r.temps_evacuation(0.5)
    t90 = r.temps_evacuation(0.9)
    t100 = r.temps_evacuation(1.0)

    largeur_porte = float(p.geometrie["largeur_porte"])
    if len(sortis_instants) >= 2:
        duree_flux = sortis_instants[-1] - sortis_instants[0]
        debit_porte = (
            (len(sortis_instants) - 1) / (duree_flux * largeur_porte)
            if duree_flux > 0
            else math.nan
        )
    else:
        debit_porte = math.nan

    if r.franchissements.size > 0:
        attente_eau = float(np.mean(r.franchissements[:, 2]))
        fins_franchissement = {int(ligne[0]): ligne[3] for ligne in r.franchissements}
        temps_plage = [
            r.sorties[i] - fins_franchissement[i]
            for i in np.flatnonzero(np.isfinite(r.sorties))
            if i in fins_franchissement
        ]
        duree_plage = float(np.mean(temps_plage)) if temps_plage else math.nan
    else:
        attente_eau = math.nan
        duree_plage = math.nan

    return {
        "t50": t50,
        "t90": t90,
        "t100": t100,
        "attente_eau": attente_eau,
        "duree_plage": duree_plage,
        "debit_porte": debit_porte,
        "non_sortis": non_sortis,
    }


def comparer(
    configuration: dict,
    graines: list[int],
    variantes: list[str] | None = None,
) -> dict[str, np.ndarray]:
    """Mesures de chaque variante, de forme (len(graines), len(MESURES)).

    Args:
        configuration: configuration YAML de la piscine, deja chargee en memoire.
        graines: liste d'entiers servant de graines de placement initial.
        variantes: liste optionnelle de noms de variantes a restreindre.

    Returns:
        Tableau bidimensionnel de mesures pour chaque variante.
    """
    if not graines:
        raise ValueError("il faut au moins une graine")
    noms = tuple(variantes) if variantes is not None else tuple(VARIANTES)
    for nom in noms:
        if nom not in VARIANTES:
            raise ValueError(f"variante inconnue {nom!r} ; attendu : {', '.join(VARIANTES)}")

    base = configuration["parametres"]
    milieux = base["parametres_milieux"]
    sec = (
        milieux["SEC"]
        if isinstance(milieux["SEC"], ParametresMilieu)
        else ParametresMilieu(**dict(milieux["SEC"]))
    )
    mouille = (
        milieux["MOUILLE"]
        if isinstance(milieux["MOUILLE"], ParametresMilieu)
        else ParametresMilieu(**dict(milieux["MOUILLE"]))
    )
    eau = (
        milieux["EAU"]
        if isinstance(milieux["EAU"], ParametresMilieu)
        else ParametresMilieu(**dict(milieux["EAU"]))
    )

    resultats = {}
    for nom in noms:
        var_mouille = mouille_de_variante(nom, sec, mouille)
        table_milieux = {
            "EAU": eau,
            "SEC": sec,
            "MOUILLE": var_mouille,
        }
        lignes = []
        for graine in graines:
            p = ParametresPiscine(
                **(base | {"parametres_milieux": table_milieux}),
                graine=graine,
            )
            mesures = mesurer(p)
            lignes.append([mesures[m] for m in MESURES])
        resultats[nom] = np.array(lignes)
    return resultats
