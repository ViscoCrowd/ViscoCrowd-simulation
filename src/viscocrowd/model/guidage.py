"""Premier guidage analytique, pour le banc de couloir sans obstacle (G1)."""

import numpy as np

from viscocrowd.core.state import State


def direction_aval(etat: State) -> np.ndarray:
    """Vers +x, avant comme apres la section de sortie.

    Dans un couloir sans obstacle ou la vitesse F > 0 ne depend que de x,
    phi(x) = integrale de x a L de 1/F(s) ds donne e = -grad(phi)/|grad(phi)|
    = (1, 0). Aucun detour ni choix d'echelle n'est resolu ici : c'est le cas
    analytique auquel le futur champ eikonal pourra etre compare.
    """
    resultat = np.zeros((etat.n, 2))
    resultat[:, 0] = 1.0
    return resultat
