"""Diagramme fondamental de Weidmann : la reference de la litterature.

Les consignes demandent de confronter les resultats a un resultat connu. Pour
une foule, c'est le diagramme fondamental de Weidmann (1993), qui donne la
vitesse de marche en fonction de la densite :

    v(rho) = v0 * (1 - exp(-gamma * (1/rho - 1/rho_max)))

et le debit specifique s'en deduit par J = rho * v.

Lecture : a faible densite, chacun marche a sa vitesse libre v0, mais il passe
peu de monde. Plus la foule est dense, plus il passe de monde... jusqu'a ce que
la gene ralentisse tout le monde. A rho_max, plus personne n'avance. Le debit
trace en fonction de la densite forme donc une colline, de sommet environ
1,22 pers/m/s vers 1,75 pers/m^2.

Constantes : v0 = 1,34 m/s, gamma = 1,913 pers/m^2, rho_max = 5,4 pers/m^2,
valeurs couramment reprises de Weidmann, U. (1993), Transporttechnik der
Fussgaenger, ETH Zurich. A verifier sur la source primaire avant citation.
"""

from __future__ import annotations

import numpy as np

V0 = 1.34  # vitesse de marche libre, m/s
GAMMA = 1.913  # parametre de forme, pers/m^2
RHO_MAX = 5.4  # densite a laquelle la marche s'arrete, pers/m^2


def vitesse(rho: np.ndarray | float) -> np.ndarray:
    """Vitesse de marche de Weidmann, en m/s, pour une densite en pers/m^2.

    Nulle au-dela de rho_max ; tend vers v0 quand la densite tend vers zero.
    """
    rho = np.asarray(rho, dtype=float)
    # A densite nulle, 1/rho est infini et l'exponentielle vaut zero : v = v0.
    # On evite la division par zero en remplacant rho = 0 par une valeur sans effet.
    inverse = np.divide(1.0, rho, out=np.full_like(rho, np.inf), where=rho > 0.0)
    v = V0 * (1.0 - np.exp(-GAMMA * (inverse - 1.0 / RHO_MAX)))
    return np.where(rho < RHO_MAX, v, 0.0)


def debit_specifique(rho: np.ndarray | float) -> np.ndarray:
    """Debit specifique de Weidmann, J = rho * v(rho), en pers/m/s."""
    rho = np.asarray(rho, dtype=float)
    return rho * vitesse(rho)
