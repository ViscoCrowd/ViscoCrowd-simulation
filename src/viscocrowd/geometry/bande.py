"""Bande x >= 0, y_bas <= y <= y_haut, percee d'obstacles : couloir et salle E0.

Le couloir (G1/G2) et la salle du goulot (E0) sont la meme geometrie : un mur du
fond en x = 0, deux murs lateraux, rien en aval, et des rectangles a contourner
(un pilier, ou les deux blocs du mur perce par le goulot). Les controles d'entree,
la projection et la violation sont ecrits une seule fois ici. Une correction
atteint ainsi les deux scenarios a la fois.

La projection ramene d'abord dans la bande, puis hors de chaque obstacle, coins
arrondis compris (`ObstacleRectangle.repousser`).
"""

from __future__ import annotations

from collections.abc import Iterable

import numpy as np

from viscocrowd.core.verifications import exiger_fini, exiger_scalaire_fini
from viscocrowd.geometry.obstacle import ObstacleRectangle


def disques(x: np.ndarray, r: np.ndarray, t: float) -> tuple[np.ndarray, np.ndarray]:
    """Centres (N, 2) et rayons (N,) en flottants finis, a un instant t fini."""
    x, r = np.asarray(x, dtype=float), np.asarray(r, dtype=float)
    if x.ndim != 2 or x.shape[1] != 2 or r.shape != (x.shape[0],):
        raise ValueError("x et r doivent etre de formes (N, 2) et (N,)")
    exiger_fini(x=x, r=r)
    exiger_scalaire_fini("t", t)
    return x, r


def projeter_bande(
    x: np.ndarray,
    r: np.ndarray,
    y_bas: float,
    y_haut: float,
    obstacles: Iterable[ObstacleRectangle],
) -> np.ndarray:
    """Centres ramenes a r des murs de la bande, puis hors de chaque obstacle."""
    resultat = x.copy()
    resultat[:, 0] = np.maximum(x[:, 0], r)
    resultat[:, 1] = np.clip(x[:, 1], y_bas + r, y_haut - r)
    for obstacle in obstacles:
        resultat = obstacle.repousser(resultat, r)
    return resultat


def violation_bande(
    x: np.ndarray,
    r: np.ndarray,
    y_bas: float,
    y_haut: float,
    obstacles: Iterable[ObstacleRectangle],
) -> float:
    """Depassement maximal (m) des murs et des obstacles, nul si tous les disques tiennent."""
    centre, demi = (y_bas + y_haut) / 2, (y_haut - y_bas) / 2
    return float(
        max(
            np.max(r - x[:, 0], initial=0.0),
            np.max(np.abs(x[:, 1] - centre) + r - demi, initial=0.0),
            *(obstacle.violation(x, r) for obstacle in obstacles),
        )
    )
