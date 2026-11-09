"""Salle rectangulaire prolongee par un goulot : le banc d'etalonnage E0.

    y
    ^   +-----------------------------+
    |   |                             +-----------------+
    |   |           salle             |     goulot      |  -> dehors
    |   |                             +-----------------+
    |   +-----------------------------+                   -> x
        0                             L                 L + l

Le goulot, de largeur b et de longueur l, est centre sur le mur de droite. Le mur
perce est represente par deux blocs pleins (`ObstacleRectangle`) qui bordent le
goulot ; la salle n'a pas d'autre mur a droite et le goulot debouche sur
l'exterieur. C'est donc la bande de `geometry.bande`, comme le couloir, avec les
deux blocs pour obstacles : projection et violation y sont partagees. Comme le
goulot est plus large qu'un diametre, les deux blocs ne se disputent jamais un
meme disque.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from viscocrowd.core.verifications import exiger_scalaire_fini
from viscocrowd.geometry.bande import disques, projeter_bande, violation_bande
from viscocrowd.geometry.obstacle import ObstacleRectangle


@dataclass(frozen=True)
class SalleGoulot:
    """Longueurs en metres."""

    longueur: float
    largeur: float
    largeur_goulot: float
    longueur_goulot: float

    def __post_init__(self) -> None:
        for nom in ("longueur", "largeur", "largeur_goulot", "longueur_goulot"):
            exiger_scalaire_fini(nom, getattr(self, nom), strictement_positif=True)
        if self.largeur_goulot > self.largeur:
            raise ValueError("le goulot ne peut pas etre plus large que la salle")

    @property
    def bords_goulot(self) -> tuple[float, float]:
        """Ordonnees des deux murs du goulot, en m."""
        centre = self.largeur / 2
        return centre - self.largeur_goulot / 2, centre + self.largeur_goulot / 2

    def entree(self, decalage: float = 0.0) -> tuple[np.ndarray, np.ndarray]:
        """Segment en travers du goulot a `decalage` m de son entree, oriente vers +x."""
        bas, haut = self.bords_goulot
        x = self.longueur + decalage
        return np.array([x, bas]), np.array([x, haut])

    @property
    def murs_goulot(self) -> tuple[ObstacleRectangle, ObstacleRectangle]:
        """Les deux blocs de mur qui bordent le goulot, en bas et en haut."""
        bas, haut = self.bords_goulot
        fin = self.longueur + self.longueur_goulot
        # Blocs prolonges au-dela de la salle d'au moins une longueur de goulot : un centre
        # tombe dans un bloc en ressort toujours par une face qui donne sur la salle ou le
        # goulot, jamais par le dos du bloc, hors de la salle.
        marge = self.longueur_goulot
        return (
            ObstacleRectangle(self.longueur, fin, -marge, bas),
            ObstacleRectangle(self.longueur, fin, haut, self.largeur + marge),
        )

    def _entrees(self, x, r, t):
        x, r = disques(x, r, t)
        if np.any(r <= 0.0) or np.any(2 * r >= self.largeur_goulot):
            raise ValueError("chaque rayon doit etre positif et passer le goulot")
        return x, r

    def projeter(self, x: np.ndarray, r: np.ndarray, t: float = 0.0) -> np.ndarray:
        """Centres ramenes dans la bande de la salle, puis hors des deux blocs du goulot.

        Les blocs sont repousses exactement, coins ARRONDIS compris : un disque glisse
        autour de l'angle d'entree au lieu de s'y caler. Une premiere version, union
        de deux rectangles en espace des centres, y creait un coin vif ou deux murs
        orthogonaux coincaient un agent, appui ideal pour une arche.
        """
        x, r = self._entrees(x, r, t)
        return projeter_bande(x, r, 0.0, self.largeur, self.murs_goulot)

    def violation(self, x: np.ndarray, r: np.ndarray, t: float = 0.0) -> float:
        """Plus grand depassement d'un mur, en m."""
        x, r = self._entrees(x, r, t)
        return violation_bande(x, r, 0.0, self.largeur, self.murs_goulot)

    def admissible(self, points: np.ndarray, rayon: float) -> np.ndarray:
        """Vrai (M,) pour les centres admissibles d'un disque de rayon donne."""
        r = np.full(points.shape[0], rayon)
        return np.hypot(*(self.projeter(points, r) - points).T) <= 1e-12
