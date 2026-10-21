"""Couloir rectiligne, ferme en amont et prolonge sans limite en aval."""

from dataclasses import dataclass

import numpy as np

from viscocrowd.core.verifications import exiger_fini, exiger_scalaire_fini
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
        x, r = np.asarray(x, dtype=float), np.asarray(r, dtype=float)
        if x.ndim != 2 or x.shape[1] != 2 or r.shape != (x.shape[0],):
            raise ValueError("x et r doivent etre de formes (N, 2) et (N,)")
        exiger_fini(x=x, r=r)
        exiger_scalaire_fini("t", t)
        if np.any((r <= 0) | (2 * r > self.largeur)):
            raise ValueError("chaque rayon doit etre positif et tenir dans le couloir")
        return x, r

    def projeter(self, x: np.ndarray, r: np.ndarray, t: float) -> np.ndarray:
        """Projection exacte sur les trois demi-plans, puis hors des obstacles."""
        x, r = self._entrees(x, r, t)
        resultat = x.copy()
        resultat[:, 0] = np.maximum(x[:, 0], r)
        resultat[:, 1] = np.clip(x[:, 1], -self.largeur / 2 + r, self.largeur / 2 - r)
        for obstacle in self.obstacles:
            resultat = obstacle.repousser(resultat, r)
        return resultat

    def violation(self, x: np.ndarray, r: np.ndarray, t: float) -> float:
        """Depassement maximal des parois et des obstacles (m), nul si tous les disques tiennent."""
        x, r = self._entrees(x, r, t)
        return float(
            max(
                np.max(r - x[:, 0], initial=0.0),
                np.max(np.abs(x[:, 1]) + r - self.largeur / 2, initial=0.0),
                *(obstacle.violation(x, r) for obstacle in self.obstacles),
            )
        )

    @property
    def section_sortie(self) -> tuple[np.ndarray, np.ndarray]:
        """Segment oriente pour compter positivement les passages vers +x."""
        return (
            np.array([self.longueur, -self.largeur / 2]),
            np.array([self.longueur, self.largeur / 2]),
        )
