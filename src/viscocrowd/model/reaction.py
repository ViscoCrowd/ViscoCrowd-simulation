"""Temps de reaction a l'alarme : chaque baigneur ne part qu'apres un delai (facultatif).

Dans une evacuation reelle, personne ne part au meme instant : il faut entendre l'alarme,
comprendre, decider (le temps de « pre-mouvement » de la litterature sur l'evacuation, que
ISO/TR 16738 et Purser et Bensilum (2001) decrivent par une loi a queue a droite, souvent
log-normale ; A VERIFIER sur les originaux avant de citer). Dans une piscine, un nageur
sous l'eau ou au bout du bassin reagit plus tard qu'un baigneur au bord. Ce module tire un
instant de reaction par agent :

    t_i = exp(log(mediane) + dispersion * Z_i),   Z_i ~ N(0, 1)

`mediane` (s) est la mediane de la loi, `dispersion` l'ecart-type de log(t). Aucune valeur
n'existe pour une piscine : ce sont des HYPOTHESES a balayer. Le scenario arrete la
direction de l'agent tant que t < t_i (voir `scenarios.piscine`).

Pourquoi c'est utile au sujet : etaler les departs desynchronise les arrivees au goulot,
ce qui est precisement le mecanisme de l'hypothese « tampon » de la problematique.

Les tirages ont leur propre flux : activer l'option ne change ni les positions initiales
(flux par defaut), ni les chutes (flux 1), ni la navigation (flux 2, #163).
"""

from __future__ import annotations

import numpy as np

from viscocrowd.core.rng import generateur
from viscocrowd.core.verifications import exiger_scalaire_fini

FLUX_REACTION = 3


def instants_reaction(n: int, mediane: float, dispersion: float, graine: int) -> np.ndarray:
    """Instant de reaction (n,) de chaque agent, en s, tire une fois pour toutes.

    Args:
        n: nombre d'agents.
        mediane: mediane de la loi log-normale, en s, strictement positive.
        dispersion: ecart-type de log(t), sans unite, positif ou nul ; 0 donne `mediane`
            a tous les agents (depart simultane, mais retarde).
        graine: graine de la simulation.
    """
    exiger_scalaire_fini("mediane", mediane, strictement_positif=True)
    exiger_scalaire_fini("dispersion", dispersion)
    if dispersion < 0:
        raise ValueError("dispersion doit etre positive ou nulle")
    if dispersion == 0.0:
        return np.full(n, float(mediane))
    z = generateur(graine, flux=FLUX_REACTION).standard_normal(n)
    return np.exp(np.log(mediane) + dispersion * z)
