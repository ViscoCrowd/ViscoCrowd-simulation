"""Obstacle fixe rectangulaire, aligne sur les axes (pilier, gradin, mobilier).

Deux usages :

  - le guidage le contourne (G2) : `distance` retire des points de passage du
    champ eikonal, avec une marge egale au rayon des agents ;
  - la projection le respecte : `repousser` ramene hors de l'obstacle le centre
    de tout disque qui le chevauche, comme une paroi. Sans cela, seul le guidage
    l'evitait, et un agent pousse par ses voisins pouvait y entrer.

L'exterieur d'un rectangle n'est pas convexe, mais sa projection reste explicite.
Un disque de rayon r chevauche l'obstacle quand son centre est dans le rectangle
gonfle de r, aux coins arrondis. On le ramene au point le plus proche du bord de
ce rectangle gonfle :

  - centre hors du rectangle : le long de la droite qui le joint au point le plus
    proche du rectangle, a la distance r ;
  - centre dans le rectangle : par la face la plus proche, a la distance r.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from viscocrowd.core.verifications import exiger_fini, exiger_scalaire_fini


def _points(x: np.ndarray) -> np.ndarray:
    x = np.asarray(x, dtype=float)
    if x.ndim != 2 or x.shape[1] != 2:
        raise ValueError(f"x doit etre de forme (M, 2), recu {x.shape}")
    exiger_fini(x=x)
    return x


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
        x = _points(x)
        dx = np.maximum(np.maximum(self.x_min - x[:, 0], x[:, 0] - self.x_max), 0.0)
        dy = np.maximum(np.maximum(self.y_min - x[:, 1], x[:, 1] - self.y_max), 0.0)
        return np.hypot(dx, dy)

    def _distance_signee(self, x: np.ndarray) -> np.ndarray:
        """Distance au bord, negative a l'interieur (moins la profondeur), en m."""
        dedans = np.minimum.reduce(
            [x[:, 0] - self.x_min, self.x_max - x[:, 0], x[:, 1] - self.y_min, self.y_max - x[:, 1]]
        )
        return np.where(dedans > 0.0, -dedans, self.distance(x))

    def repousser(self, x: np.ndarray, r: np.ndarray) -> np.ndarray:
        """Centres (M, 2) ramenes a la distance r au moins de l'obstacle. Voir le module."""
        x = _points(x)
        r = np.broadcast_to(np.asarray(r, dtype=float), (x.shape[0],))
        resultat = x.copy()
        proche = np.clip(x, [self.x_min, self.y_min], [self.x_max, self.y_max])
        ecart = x - proche
        d = np.hypot(ecart[:, 0], ecart[:, 1])

        dehors = (d > 0.0) & (d < r)
        resultat[dehors] = proche[dehors] + ecart[dehors] * (r[dehors] / d[dehors])[:, None]

        # Centre dans le rectangle (bord compris) : sortie par la face la plus proche.
        dedans = d == 0.0
        if np.any(dedans):
            p, rr = x[dedans], r[dedans]
            profondeurs = np.stack(
                [
                    p[:, 0] - self.x_min,
                    self.x_max - p[:, 0],
                    p[:, 1] - self.y_min,
                    self.y_max - p[:, 1],
                ],
                axis=1,
            )
            face = np.argmin(profondeurs, axis=1)
            sortie = p.copy()
            sortie[face == 0, 0] = self.x_min - rr[face == 0]
            sortie[face == 1, 0] = self.x_max + rr[face == 1]
            sortie[face == 2, 1] = self.y_min - rr[face == 2]
            sortie[face == 3, 1] = self.y_max + rr[face == 3]
            resultat[dedans] = sortie
        return resultat

    def violation(self, x: np.ndarray, r: np.ndarray) -> float:
        """Plus grand chevauchement (m) entre un disque et l'obstacle, nul si aucun."""
        x = _points(x)
        r = np.broadcast_to(np.asarray(r, dtype=float), (x.shape[0],))
        return float(np.max(r - self._distance_signee(x), initial=0.0))
