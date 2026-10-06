"""Etat d'un systeme de particules.

Toutes les grandeurs sont en unites SI :
    x  position           m
    v  vitesse            m/s
    r  rayon              m
    t  temps              s
"""

from __future__ import annotations

from dataclasses import dataclass, replace

import numpy as np

# Acceleration gravitationnelle terrestre, axe vertical oriente vers le haut.
GRAVITE = np.array([0.0, -9.81])  # m/s^2


@dataclass(frozen=True)
class State:
    """Etat instantane de N particules dans le plan.

    Immuable : chaque pas de temps produit un nouvel etat. Cela evite les
    mutations accidentelles d'un historique de trajectoires, qui sont une
    source classique de resultats faux et difficiles a diagnostiquer.
    """

    x: np.ndarray  # (N, 2) positions, m
    v: np.ndarray  # (N, 2) vitesses, m/s
    r: np.ndarray  # (N,)   rayons, m
    t: float = 0.0  # s

    def __post_init__(self) -> None:
        if self.x.ndim != 2 or self.x.shape[1] != 2:
            raise ValueError(f"x doit etre de forme (N, 2), recu {self.x.shape}")
        if self.v.shape != self.x.shape:
            raise ValueError(f"v {self.v.shape} doit avoir la meme forme que x {self.x.shape}")
        if self.r.shape != (self.x.shape[0],):
            raise ValueError(f"r doit etre de forme ({self.x.shape[0]},), recu {self.r.shape}")
        if np.any(self.r <= 0.0):
            raise ValueError("tous les rayons doivent etre strictement positifs")

    @property
    def n(self) -> int:
        """Nombre de particules."""
        return self.x.shape[0]

    def advanced(self, *, x: np.ndarray, v: np.ndarray, t: float) -> State:
        """Nouvel etat au temps t, de memes rayons."""
        return replace(self, x=x, v=v, t=t)

    @classmethod
    def single(
        cls,
        position: tuple[float, float],
        vitesse: tuple[float, float] = (0.0, 0.0),
        rayon: float = 0.05,
    ) -> State:
        """Etat a une seule particule. Pratique pour les cas de validation."""
        return cls(
            x=np.array([position], dtype=float),
            v=np.array([vitesse], dtype=float),
            r=np.array([rayon], dtype=float),
        )
