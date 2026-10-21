"""Obstacle fixe rectangulaire, aligne sur les axes (pilier, gradin, mobilier).

Le guidage le contourne (G2) : `distance` sert a retirer des points de passage
du champ eikonal, avec une marge egale au rayon des agents, et a mesurer en
validation la distance a laquelle un agent est passe de l'obstacle.

L'obstacle n'est PAS une contrainte de la projection : seul le guidage l'evite.
Un agent pousse par ses voisins pourrait donc y entrer. L'ajouter a l'ensemble
admissible releve de l'extension de G5 avec obstacles.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from viscocrowd.core.verifications import exiger_fini, exiger_scalaire_fini


@dataclass(frozen=True)
class ObstacleRectangle:
    """Rectangle [x_min, x_max] x [y_min, y_max], en metres."""

    x_min: float
    x_max: float
    y_min: float
    y_max: float

    def __post_init__(self) -> None:
        for nom in ("x_min", "x_max", "y_min", "y_max"):
            exiger_scalaire_fini(nom, getattr(self, nom))
        # Forme positive, comme ailleurs : une comparaison avec NaN est toujours fausse.
        if not (self.x_max > self.x_min and self.y_max > self.y_min):
            raise ValueError(
                "l'obstacle doit avoir une largeur et une hauteur strictement positives"
            )

    def distance(self, x: np.ndarray) -> np.ndarray:
        """Distance euclidienne (m) de chaque point (M, 2) au rectangle, nulle a l'interieur."""
        x = np.asarray(x, dtype=float)
        if x.ndim != 2 or x.shape[1] != 2:
            raise ValueError(f"x doit etre de forme (M, 2), recu {x.shape}")
        exiger_fini(x=x)
        dx = np.maximum(np.maximum(self.x_min - x[:, 0], x[:, 0] - self.x_max), 0.0)
        dy = np.maximum(np.maximum(self.y_min - x[:, 1], x[:, 1] - self.y_max), 0.0)
        return np.hypot(dx, dy)
