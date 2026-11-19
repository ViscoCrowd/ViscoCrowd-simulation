"""Couloir circulaire : anneau rayon_interieur <= |x| <= rayon_exterieur, centre a l'origine.

Un couloir droit periodique demanderait de raccorder les contacts a travers la couture,
donc de modifier la projection du moteur. L'anneau est periodique par construction : le
moteur reste tel quel, et la geometrie se resume a deux contraintes radiales. C'est le
dispositif des experiences de Jelic et al. (2012) et de Seyfried et al. (2005).
"""

from dataclasses import dataclass

import numpy as np

from viscocrowd.core.verifications import exiger_scalaire_fini
from viscocrowd.geometry.bande import disques


@dataclass(frozen=True)
class Anneau:
    """Rayons en m. Les murs sont les deux cercles ; il n'y a ni entree ni sortie."""

    rayon_interieur: float
    rayon_exterieur: float

    def __post_init__(self) -> None:
        for nom in ("rayon_interieur", "rayon_exterieur"):
            exiger_scalaire_fini(nom, getattr(self, nom), strictement_positif=True)
        if self.rayon_exterieur <= self.rayon_interieur:
            raise ValueError("rayon_exterieur doit depasser rayon_interieur")

    @property
    def aire(self) -> float:
        """Surface de marche, en m^2 : celle qui sert a definir la densite."""
        return float(np.pi * (self.rayon_exterieur**2 - self.rayon_interieur**2))

    def _entrees(self, x, r, t):
        x, r = disques(x, r, t)
        if np.any((r <= 0) | (2 * r > self.rayon_exterieur - self.rayon_interieur)):
            raise ValueError("chaque rayon doit etre positif et tenir dans l'anneau")
        return x, r

    def projeter(self, x: np.ndarray, r: np.ndarray, t: float) -> np.ndarray:
        """Projection exacte : chaque centre est ramene radialement entre les deux murs.

        Le mur interieur rend le domaine non convexe, mais la projection d'un point sur
        une couronne reste unique hors du centre, ou aucun agent ne peut se trouver.
        """
        x, r = self._entrees(x, r, t)
        distance = np.hypot(x[:, 0], x[:, 1])
        if np.any(distance == 0.0):
            raise ValueError("un centre d'agent est au centre de l'anneau : direction indefinie")
        cible = np.clip(distance, self.rayon_interieur + r, self.rayon_exterieur - r)
        return x * (cible / distance)[:, None]

    def violation(self, x: np.ndarray, r: np.ndarray, t: float) -> float:
        """Depassement maximal des deux murs (m), nul si tous les disques tiennent."""
        x, r = self._entrees(x, r, t)
        distance = np.hypot(x[:, 0], x[:, 1])
        depassement = np.maximum(
            self.rayon_interieur + r - distance, distance - (self.rayon_exterieur - r)
        )
        return float(np.max(depassement, initial=0.0))
