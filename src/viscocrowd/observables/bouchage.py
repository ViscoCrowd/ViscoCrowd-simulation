"""Intervalles entre sorties successives : la signature des bouchons devant la porte.

Le temps d'evacuation t100 dit QUAND la foule a fini de sortir, pas COMMENT. Les etudes de
bouchage aux goulots (Zuriguel et al., 2014, Sci. Rep. 4, 7324 ; a verifier sur l'original
avant de citer) regardent l'intervalle Delta entre deux passages successifs de la porte : un
ecoulement fluide donne des Delta courts et resserres ; des bouchons qui finissent par ceder
donnent une queue lourde a la distribution P(Delta > tau). C'est elle qui montre l'effet
« faster-is-slower » (bouchons plus longs quand la panique monte), pas une moyenne de t100.

Limite propre a ce modele : il n'a pas de bruit dynamique, et un bouchon peut ne jamais se
defaire (evacuation incomplete). Les agents jamais sortis ne donnent pas d'intervalle ; ils
sont COMPTES a part (`resumer`), jamais retires en silence.

Toutes les durees sont en secondes.
"""

from __future__ import annotations

import numpy as np


def intervalles_sorties(sorties: np.ndarray) -> np.ndarray:
    """Intervalles (s) entre sorties successives, apres tri ; NaN (jamais sorti) ignore.

    Args:
        sorties: (N,) instant de passage de la porte de chaque agent, NaN s'il n'est pas sorti.

    Returns:
        (M - 1,) differences des M instants finis tries ; vide si moins de deux sorties.
    """
    instants = np.sort(np.asarray(sorties, dtype=float).ravel())
    instants = instants[np.isfinite(instants)]
    return np.diff(instants)


def survie(intervalles: np.ndarray, seuils: np.ndarray) -> np.ndarray:
    """P(Delta > tau) pour chaque seuil tau (inegalite stricte) ; NaN sans intervalle."""
    intervalles = np.asarray(intervalles, dtype=float).ravel()
    seuils = np.asarray(seuils, dtype=float).ravel()
    if intervalles.size == 0:
        return np.full(seuils.shape, np.nan)
    return np.mean(intervalles[None, :] > seuils[:, None], axis=1)


def resumer(sorties: np.ndarray, seuil_bouchon: float = 1.0) -> dict[str, float | int]:
    """Bilan d'une evacuation : sorties, completude et intervalles.

    Args:
        sorties: (N,) instants de sortie, NaN pour un agent jamais sorti.
        seuil_bouchon: intervalle (s) au-dela duquel on parle de bouchon. 1 s par defaut :
            convention a discuter, pas une valeur de la litterature.

    Returns:
        `n_sortis`, `incomplete` (1 si un agent n'est jamais sorti), et sur les intervalles :
        `mediane`, `max` (s) et `p_bouchon` = P(Delta > seuil_bouchon) ; NaN sans intervalle.
    """
    sorties = np.asarray(sorties, dtype=float).ravel()
    intervalles = intervalles_sorties(sorties)
    sortis = int(np.isfinite(sorties).sum())
    vide = intervalles.size == 0
    return {
        "n_sortis": sortis,
        "incomplete": int(sortis < sorties.size),
        "mediane": float("nan") if vide else float(np.median(intervalles)),
        "max": float("nan") if vide else float(intervalles.max()),
        "p_bouchon": float(survie(intervalles, np.array([seuil_bouchon]))[0]),
    }
