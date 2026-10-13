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

from viscocrowd.core.verifications import exiger_fini, exiger_scalaire_fini

# Acceleration gravitationnelle terrestre, axe vertical oriente vers le haut.
GRAVITE = np.array([0.0, -9.81])  # m/s^2


def _gele(tableau: np.ndarray) -> np.ndarray:
    """Rend une vue en lecture seule du tableau, copiee si besoin.

    Copier n'est necessaire que si l'appelant garde une reference modifiable :
    sans cela, `State(x=x_init, ...)` puis `x_init[0, 0] = 5` modifiait l'etat
    apres coup. Un tableau deja en lecture seule ne peut venir que d'un autre
    State, donc le partager ne risque rien.
    """
    tableau = np.asarray(tableau, dtype=float)
    if tableau.flags.writeable:
        tableau = tableau.copy()
        tableau.setflags(write=False)
    return tableau


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
        # `frozen=True` n'interdit que la REAFFECTATION d'un attribut, pas la
        # modification du contenu d'un tableau NumPy : `etat.r[0] = 99` passait,
        # et comme `advanced()` partage le tableau des rayons, toute la
        # trajectoire changeait d'un coup. L'immuabilite annoncee n'existait pas.
        # On gele donc le contenu : copie si le tableau est encore modifiable,
        # puis passage en lecture seule. Un tableau deja gele vient forcement
        # d'un autre State : le partager est sans danger, et evite de recopier
        # les rayons a chaque pas de temps.
        object.__setattr__(self, "x", _gele(self.x))
        object.__setattr__(self, "v", _gele(self.v))
        object.__setattr__(self, "r", _gele(self.r))

        if self.x.ndim != 2 or self.x.shape[1] != 2:
            raise ValueError(f"x doit etre de forme (N, 2), recu {self.x.shape}")
        if self.v.shape != self.x.shape:
            raise ValueError(f"v {self.v.shape} doit avoir la meme forme que x {self.x.shape}")
        if self.r.shape != (self.x.shape[0],):
            raise ValueError(f"r doit etre de forme ({self.x.shape[0]},), recu {self.r.shape}")
        # Avant le test de signe : `NaN <= 0` est faux, un rayon NaN passerait sinon.
        exiger_fini("Un etat corrompu ne doit pas pouvoir avancer.", x=self.x, v=self.v, r=self.r)
        # L'instant fait partie de l'etat. Un t non fini rend la projection du
        # domaine mobile non finie a son tour, et le diagnostic accuserait alors
        # les positions au lieu de l'horloge.
        exiger_scalaire_fini("t", self.t)
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
