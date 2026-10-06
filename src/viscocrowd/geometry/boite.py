"""Boite carree en rotation uniforme, et projection sur cette boite.

Cas de validation du module : une bille confinee dans une boite carree de
demi-largeur R, centree a l'origine, tournant a la vitesse angulaire omega.

La formule de projection implementee ici (correction cote par cote) donne la
projection orthogonale EXACTE sur le carre, pour deux raisons geometriques
specifiques :

  - deux cotes adjacents ont des normales orthogonales, donc corriger selon
    l'une ne modifie pas la quantite contrainte par l'autre : les corrections
    ne se genent pas ;
  - deux cotes opposes ne peuvent pas etre violes simultanement, ce qui
    demanderait x.n > R-r et -x.n > R-r, impossible des que R > r.

C'est un heureux accident de geometrie, et non une methode generale. Des que
le domaine cessera d'etre un rectangle, ou des que la contrainte d'exclusion
entre agents entrera en jeu, il faudra passer a un procede ITERATIF
(cf. viscocrowd.geometry.projection, jalon 2).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class BoiteTournante:
    """Carre de demi-largeur R, centre a l'origine, en rotation uniforme.

    Attributes:
        demi_largeur: R, en metres.
        omega: vitesse angulaire, en rad/s. Zero donne une boite fixe.
        theta0: angle initial, en radians.
    """

    demi_largeur: float
    omega: float = 0.0
    theta0: float = 0.0

    def __post_init__(self) -> None:
        if self.demi_largeur <= 0.0:
            raise ValueError("la demi-largeur doit etre strictement positive")

    def theta(self, t: float) -> float:
        """Angle de la boite au temps t, en radians."""
        return self.theta0 + self.omega * t

    def normales(self, t: float) -> np.ndarray:
        """Les quatre normales sortantes au temps t, de forme (4, 2)."""
        angles = self.theta(t) + np.arange(4) * (np.pi / 2.0)
        return np.stack([np.cos(angles), np.sin(angles)], axis=1)

    def projeter(self, x: np.ndarray, r: np.ndarray, t: float) -> np.ndarray:
        """Projette les positions x sur la boite a l'instant t.

        Args:
            x: positions libres, de forme (N, 2).
            r: rayons, de forme (N,).
            t: instant d'ARRIVEE, celui auquel la contrainte doit etre evaluee.

        Returns:
            Les positions admissibles, de forme (N, 2).
        """
        x_projete = np.array(x, dtype=float, copy=True)
        marge = self.demi_largeur - r  # (N,)

        for normale in self.normales(t):
            # Pour chaque cote viole, on ramene le point sur ce cote en le
            # deplacant selon la normale, de la quantite strictement necessaire.
            depassement = np.maximum(x_projete @ normale - marge, 0.0)  # (N,)
            x_projete -= depassement[:, None] * normale[None, :]

        return x_projete

    def violation(self, x: np.ndarray, r: np.ndarray, t: float) -> float:
        """Plus grand depassement de contrainte, en metres.

        Indicateur de validation n_1 : doit rester nul a la precision machine
        pres. Une valeur non nulle signale une projection mal implementee.
        """
        marge = self.demi_largeur - r  # (N,)
        depassements = x @ self.normales(t).T - marge[:, None]  # (N, 4)
        return float(np.max(depassements))

    def vitesse_entrainement(self, x: np.ndarray) -> np.ndarray:
        """Vitesse du solide en rotation aux points x : omega * x_perpendiculaire.

        Indicateur de validation n_2 : une fois l'energie dissipee, la bille
        doit tourner solidairement avec la boite, donc v doit tendre vers cette
        vitesse.
        """
        x_perp = np.stack([-x[:, 1], x[:, 0]], axis=1)
        return self.omega * x_perp
