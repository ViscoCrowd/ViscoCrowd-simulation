"""Couloir rectiligne, ferme en amont et prolonge sans limite en aval."""

from dataclasses import dataclass

import numpy as np

from viscocrowd.core.verifications import exiger_fini, exiger_scalaire_fini


@dataclass(frozen=True)
class Couloir:
    """Domaine x >= 0, |y| <= largeur/2 ; section de sortie en x = longueur.

    Longueur et largeur en metres. Les parois laterales continuent apres la
    section : les agents restent simules, sans retrait ni etat absorbant.
    La meme geometrie fournit projection, diagnostic et segment de mesure.
    """

    longueur: float
    largeur: float

    def __post_init__(self) -> None:
        for nom in ("longueur", "largeur"):
            exiger_scalaire_fini(nom, getattr(self, nom), strictement_positif=True)

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
        """Projection exacte sur les trois demi-plans, avec marge egale au rayon."""
        x, r = self._entrees(x, r, t)
        resultat = x.copy()
        resultat[:, 0] = np.maximum(x[:, 0], r)
        resultat[:, 1] = np.clip(x[:, 1], -self.largeur / 2 + r, self.largeur / 2 - r)
        return resultat

    def violation(self, x: np.ndarray, r: np.ndarray, t: float) -> float:
        """Depassement maximal des parois (m), nul si tous les disques tiennent."""
        x, r = self._entrees(x, r, t)
        return float(
            max(
                np.max(r - x[:, 0], initial=0.0),
                np.max(np.abs(x[:, 1]) + r - self.largeur / 2, initial=0.0),
            )
        )

    @property
    def section_sortie(self) -> tuple[np.ndarray, np.ndarray]:
        """Segment oriente pour compter positivement les passages vers +x."""
        return (
            np.array([self.longueur, -self.largeur / 2]),
            np.array([self.longueur, self.largeur / 2]),
        )
