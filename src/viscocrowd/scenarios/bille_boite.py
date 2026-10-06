"""Scenario de validation : une bille dans une boite en rotation.

Ce scenario ne fait pas partie de la problematique ViscoCrowd. Il sert de banc
d'essai du moteur : c'est le cas de reference du module, dont le comportement
attendu est connu analytiquement, et il verifie que le couple
« pas semi-implicite + projection » est correctement implemente AVANT qu'on
lui ajoute la moindre complexite liee a la foule.

Les parametres par defaut sont ceux suggeres par le sujet d'introduction.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from viscocrowd.core.integrator import chute_libre, trajectoire
from viscocrowd.core.state import GRAVITE, State
from viscocrowd.geometry.boite import BoiteTournante


@dataclass(frozen=True)
class ParametresBille:
    """Parametres du scenario, en unites SI.

    Note : la masse n'intervient nulle part dans le schema final, elle se
    simplifie dans la formulation par minimisation. C'est attendu — la chute
    libre ne depend pas de la masse — mais on la conserve pour le calcul de
    l'energie, qui, lui, en depend.
    """

    demi_largeur: float = 1.0  # R, m
    rayon: float = 0.05  # r, m
    masse: float = 1.0  # kg
    omega: float = 1.0  # rad/s
    dt: float = 1e-3  # s
    duree: float = 20.0  # s
    position_initiale: tuple[float, float] = (0.3, 0.5)  # m
    vitesse_initiale: tuple[float, float] = (0.0, 0.0)  # m/s
    theta0: float = 0.0  # rad
    gravite: np.ndarray = field(default_factory=lambda: GRAVITE.copy())  # m/s^2


@dataclass(frozen=True)
class ResultatBille:
    """Trajectoire simulee et grandeurs de validation."""

    t: np.ndarray  # (P,)      s
    x: np.ndarray  # (P, 1, 2) m
    v: np.ndarray  # (P, 1, 2) m/s
    boite: BoiteTournante
    parametres: ParametresBille

    def violation_max(self) -> float:
        """Plus grand depassement de contrainte sur toute la simulation, en m.

        Doit rester nul a la precision machine pres (ordre de 1e-16).
        """
        rayons = np.full(self.x.shape[1], self.parametres.rayon)
        return max(
            self.boite.violation(self.x[p], rayons, float(self.t[p])) for p in range(self.t.size)
        )


def simuler_bille(parametres: ParametresBille | None = None) -> ResultatBille:
    """Simule le scenario et rend la trajectoire complete."""
    p = parametres or ParametresBille()

    boite = BoiteTournante(
        demi_largeur=p.demi_largeur,
        omega=p.omega,
        theta0=p.theta0,
    )

    etat_initial = State.single(
        position=p.position_initiale,
        vitesse=p.vitesse_initiale,
        rayon=p.rayon,
    )

    t, x, v = trajectoire(
        etat_initial,
        dt=p.dt,
        duree=p.duree,
        vitesse_libre=chute_libre(p.gravite),
        projection=boite.projeter,
    )

    return ResultatBille(t=t, x=x, v=v, boite=boite, parametres=p)
