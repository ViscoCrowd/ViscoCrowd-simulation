"""Couloir rectiligne, ferme en amont et prolonge sans limite en aval."""

from dataclasses import dataclass

import numpy as np

from viscocrowd.core.verifications import exiger_scalaire_fini
from viscocrowd.geometry.bande import disques, projeter_bande, violation_bande
from viscocrowd.geometry.obstacle import ObstacleRectangle


@dataclass(frozen=True)
class Couloir:
    """Domaine x >= 0, |y| <= largeur/2 ; section de sortie en x = longueur.

    Longueur et largeur en metres. Les parois laterales continuent apres la
    section : les agents restent simules, sans retrait ni etat absorbant.
    La meme geometrie fournit projection, diagnostic et segment de mesure.

    Les obstacles sont des contraintes du domaine, comme les parois. Les parois
    sont projetees d'abord, les obstacles ensuite : ce second pas reste exact pour
    les parois tant que chaque obstacle laisse au moins un diametre d'agent
    entre lui et chaque paroi, et entre deux obstacles. Le scenario le verifie ;
    `violation` le mesure de toute facon.
    """

    longueur: float
    largeur: float
    obstacles: tuple[ObstacleRectangle, ...] = ()

    def __post_init__(self) -> None:
        for nom in ("longueur", "largeur"):
            exiger_scalaire_fini(nom, getattr(self, nom), strictement_positif=True)
        obstacles = tuple(self.obstacles)
        if not all(isinstance(o, ObstacleRectangle) for o in obstacles):
            raise ValueError("obstacles doit contenir des ObstacleRectangle")
        if any(
            o.x_min <= 0.0 or o.y_min <= -self.largeur / 2 or o.y_max >= self.largeur / 2
            for o in obstacles
        ):
            raise ValueError("chaque obstacle doit etre strictement a l'interieur du couloir")
        object.__setattr__(self, "obstacles", obstacles)

    def _entrees(self, x, r, t):
        x, r = disques(x, r, t)
        if np.any((r <= 0) | (2 * r > self.largeur)):
            raise ValueError("chaque rayon doit etre positif et tenir dans le couloir")
        return x, r

    def projeter(self, x: np.ndarray, r: np.ndarray, t: float) -> np.ndarray:
        """Projection exacte sur les trois demi-plans, puis hors des obstacles."""
        x, r = self._entrees(x, r, t)
        return projeter_bande(x, r, -self.largeur / 2, self.largeur / 2, self.obstacles)

    def violation(self, x: np.ndarray, r: np.ndarray, t: float) -> float:
        """Depassement maximal des parois et des obstacles (m), nul si tous les disques tiennent."""
        x, r = self._entrees(x, r, t)
        return violation_bande(x, r, -self.largeur / 2, self.largeur / 2, self.obstacles)

    @property
    def section_sortie(self) -> tuple[np.ndarray, np.ndarray]:
        """Segment oriente pour compter positivement les passages vers +x."""
        return (
            np.array([self.longueur, -self.largeur / 2]),
            np.array([self.longueur, self.largeur / 2]),
        )
