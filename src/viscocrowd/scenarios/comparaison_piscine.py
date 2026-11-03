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

Lorsque deux variantes produisent exactement le meme ``ParametresMilieu`` (par
exemple lorsque le sec et le mouille partagent la meme vitesse de consigne ou le
meme temps de relaxation), elles sont regroupees par ``regrouper_variantes`` et
ne sont simulees qu'une seule fois.

Mesures par graine et par variante, portant sur TOUS les agents :
  - t50, t90, t100 : instants d'evacuation definitive (en s), delegues a Sorties ;
  - attente_eau : temps moyen passe dans le bassin avant franchissement (en s) ;
  - duree_plage : temps moyen de traversee de la plage jusqu'a la porte (en s) ;
  - debit_porte : debit specifique moyen au passage de la porte (en pers/(m.s)),
    calcule par ``debit_seyfried`` comme Delta N / (Delta t * b) entre la
    premiere et la derniere sortie definitive, selon le meme estimateur qu'en E0.

Les populations initiales et les graines sont strictement appariees pour que les
ecarts mesures ne relevent que des proprietes physiques des milieux. Toute
projection non convergee ou toute simulation trop courte pour que chaque agent
franchisse le bord et sorte (``ProtocoleIncomplet``) interrompt le protocole sans
moyennage silencieux.
"""

from __future__ import annotations

import math

import numpy as np

from viscocrowd.model.milieu import Milieu, ParametresMilieu
from viscocrowd.scenarios.comparaison_mouille import (
    VARIANTES,
    ProtocoleIncomplet,
    mouille_de_variante,
)
from viscocrowd.scenarios.goulot import debit_seyfried
from viscocrowd.scenarios.piscine import ParametresPiscine, simuler_piscine

__all__ = [
    "LIBELLES",
    "MESURES",
    "UNITES",
    "VARIANTES",
    "ProtocoleIncomplet",
    "comparer",
    "mesurer",
    "mouille_de_variante",
    "regrouper_variantes",
]

LIBELLES = {
    "reference": "référence (mouillé = sec, E1)",
    "vitesse": "vitesse seule",
    "relaxation": "relaxation seule",
    "adherence": "adhérence seule",
    "vitesse+adherence": "vitesse + adhérence",
    "complet": "complet (sol mouillé réel, E2)",
}

MESURES = ("t50", "t90", "t100", "attente_eau", "duree_plage", "debit_porte")
UNITES = {
    "t50": "s",
    "t90": "s",
    "t100": "s",
    "attente_eau": "s",
    "duree_plage": "s",
    "debit_porte": "pers/(m.s)",
}


def _valider_variantes(variantes: list[str] | tuple[str, ...] | None) -> tuple[str, ...]:
    noms = tuple(variantes) if variantes is not None else tuple(VARIANTES)
    if not noms:
        raise ValueError("il faut au moins une variante")
    if len(set(noms)) != len(noms):
        raise ValueError("les variantes doivent etre distinctes")
    for nom in noms:
        if nom not in VARIANTES:
            raise ValueError(f"variante inconnue {nom!r} ; attendu : {', '.join(VARIANTES)}")
    return noms


def regrouper_variantes(
    sec: ParametresMilieu,
    mouille: ParametresMilieu,
    variantes: list[str] | tuple[str, ...] | None = None,
) -> dict[str, tuple[str, ...]]:
    """Regroupe les variantes qui produisent exactement le meme ParametresMilieu.

    Pour chaque groupe d'equivalence physique, la cle retenue est ``"reference"``
    si elle figure dans le groupe, sinon ``"complet"`` si elle y figure, sinon la
    premiere variante du groupe dans l'ordre demande.
    """
    noms = _valider_variantes(variantes)
    par_milieu: dict[ParametresMilieu, list[str]] = {}
    for nom in noms:
        cible = mouille_de_variante(nom, sec, mouille)
        par_milieu.setdefault(cible, []).append(nom)
    groupes: dict[str, tuple[str, ...]] = {}
    for equivalents in par_milieu.values():
        if "reference" in equivalents:
            representant = "reference"
        elif "complet" in equivalents:
            representant = "complet"
        else:
            representant = equivalents[0]
        groupes[representant] = tuple(equivalents)
    return groupes


def mesurer(p: ParametresPiscine) -> dict[str, float]:
    """Execute le scenario piscine et extrait les observables d'evacuation.

    Chaque mesure porte sur TOUS les agents : si un agent n'a pas franchi le
    bassin ou n'est pas sorti avant la fin de l'horizon ``p.duree``, la fonction
    leve ``ProtocoleIncomplet`` au lieu de moyenner une sous-population.

    Args:
        p: configuration physique complete du scenario piscine.

    Returns:
        Dictionnaire associant chaque indicateur de MESURES a sa valeur scalaire.

    Raises:
        ProjectionNonConvergee: si une projection geometrique n'a pas converge.
        ProtocoleIncomplet: si au moins un agent n'a pas termine l'evacuation.
    """
    pas_total = max(1, math.ceil(p.duree / p.dt))
    r = simuler_piscine(p, archiver_tous=pas_total)
    r.projection.verifier_convergence()

    n = p.n_agents
    manquants_sortie = int(np.sum(~np.isfinite(r.sorties)))
    if manquants_sortie > 0:
        raise ProtocoleIncomplet(
            f"{manquants_sortie} agent(s) sur {n} non sortis avant {p.duree} s : allonger la duree"
        )
    if r.franchissements.shape[0] != n:
        manquants_eau = n - int(r.franchissements.shape[0])
        raise ProtocoleIncomplet(
            f"{manquants_eau} agent(s) sur {n} sans franchissement du bassin avant {p.duree} s : "
            "allonger la duree"
        )

    attente_eau = float(np.mean(r.franchissements[:, 2]))
    agents_franchis = r.franchissements[:, 0].astype(np.intp)
    duree_plage = float(np.mean(r.sorties[agents_franchis] - r.franchissements[:, 3]))
    largeur_porte = float(p.geometrie["largeur_porte"])
    debit_porte = debit_seyfried(r.sorties, largeur_porte)

    return {
        "t50": r.temps_evacuation(0.5),
        "t90": r.temps_evacuation(0.9),
        "t100": r.temps_evacuation(1.0),
        "attente_eau": attente_eau,
        "duree_plage": duree_plage,
        "debit_porte": debit_porte,
    }


def comparer(
    configuration: dict,
    graines: list[int],
    variantes: list[str] | None = None,
) -> dict[str, np.ndarray]:
    """Mesures de chaque variante, de forme (len(graines), len(MESURES)).

    Les variantes qui produisent exactement le meme ``ParametresMilieu`` ne sont
    simulees qu'une seule fois et partagent les memes mesures.

    Args:
        configuration: configuration YAML de la piscine, deja chargee en memoire.
        graines: liste d'entiers distincts servant de graines de placement initial.
        variantes: liste optionnelle de noms distincts de variantes a restreindre.

    Returns:
        Tableau bidimensionnel de mesures pour chaque variante demandee.
    """
    graines = list(graines)
    if not graines:
        raise ValueError("il faut au moins une graine")
    if any(type(g) is not int or g < 0 for g in graines):
        raise ValueError("chaque graine doit etre un entier positif ou nul")
    if len(set(graines)) != len(graines):
        raise ValueError("les graines doivent etre distinctes")

    noms = _valider_variantes(variantes)

    base = configuration["parametres"]
    temoin = ParametresPiscine(**base, graine=0)
    eau = temoin.parametres_milieux[Milieu.EAU]
    sec = temoin.parametres_milieux[Milieu.SEC]
    mouille = temoin.parametres_milieux[Milieu.MOUILLE]

    deja_calcules: dict[ParametresMilieu, np.ndarray] = {}
    resultats: dict[str, np.ndarray] = {}
    for nom in noms:
        var_mouille = mouille_de_variante(nom, sec, mouille)
        if var_mouille not in deja_calcules:
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
            deja_calcules[var_mouille] = np.array(lignes, dtype=float)
        resultats[nom] = deja_calcules[var_mouille].copy()
    return resultats
