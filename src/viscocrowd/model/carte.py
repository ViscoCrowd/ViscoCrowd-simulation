"""Cartes des milieux : bandes verticales (couloir) et piscine, independantes du guidage."""

from dataclasses import dataclass

import numpy as np

from viscocrowd.core.verifications import exiger_fini
from viscocrowd.geometry.piscine import Piscine
from viscocrowd.model.milieu import Milieu


@dataclass(frozen=True)
class CarteBandes:
    """K frontieres en metres, K+1 milieux ; une frontiere appartient a sa droite."""

    frontieres: tuple[float, ...]
    milieux: tuple[Milieu, ...]

    def __post_init__(self) -> None:
        frontieres = np.asarray(self.frontieres, dtype=float)
        if frontieres.ndim != 1 or np.any(np.diff(frontieres) <= 0):
            raise ValueError("frontieres doit etre une suite strictement croissante")
        exiger_fini(frontieres=frontieres)
        if len(self.milieux) != len(frontieres) + 1:
            raise ValueError("il faut un milieu de plus que de frontieres")
        object.__setattr__(self, "frontieres", tuple(float(f) for f in frontieres))
        object.__setattr__(self, "milieux", tuple(Milieu(m) for m in self.milieux))

    def __call__(self, x: np.ndarray) -> np.ndarray:
        """Milieu (N,) sous les centres (N, 2), selon le contrat de #30."""
        x = np.asarray(x, dtype=float)
        if x.ndim != 2 or x.shape[1] != 2:
            raise ValueError("x doit etre de forme (N, 2)")
        exiger_fini(x=x)
        indices = np.searchsorted(self.frontieres, x[:, 0], side="right")
        return np.asarray(self.milieux, dtype=np.int64)[indices]


@dataclass(frozen=True)
class CartePiscine:
    """EAU dans le bassin, MOUILLE a moins de `largeur_mouillee` de son bord, SEC au-dela."""

    piscine: Piscine

    def __call__(self, x: np.ndarray) -> np.ndarray:
        """Milieu (N,) sous les centres (N, 2)."""
        x = np.asarray(x, dtype=float)
        if x.ndim != 2 or x.shape[1] != 2:
            raise ValueError("x doit etre de forme (N, 2)")
        exiger_fini(x=x)
        milieu = np.full(x.shape[0], Milieu.SEC, dtype=np.int64)
        milieu[self.piscine.bassin.distance(x) <= self.piscine.largeur_mouillee] = Milieu.MOUILLE
        milieu[self.piscine.dans_bassin(x)] = Milieu.EAU
        return milieu
