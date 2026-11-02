"""Energie mecanique, observable de validation.

Pour une particule de masse m dans un champ de pesanteur g :

    E = (1/2) m |v|^2 - m g . x       en joules

Le second terme est l'energie potentielle de pesanteur : avec g = (0, -9.81),
-g.x vaut +9.81 * x_vertical, qui croit bien avec l'altitude.

Comportement attendu, et pourquoi il discrimine une erreur :

  - boite FIXE (omega = 0) : l'energie est non croissante. En vol libre, le
    schema semi-implicite la fait decroitre de exactement (1/2) dt^2 |g|^2 par
    pas, et chaque choc mou en dissipe une part sous forme de chaleur. Une
    energie qui remonte signale une erreur.
  - boite EN ROTATION (omega != 0) : la paroi mobile travaille et peut injecter
    de l'energie dans le systeme. La decroissance n'est alors plus un invariant,
    et c'est la vitesse d'entrainement qu'il faut surveiller a la place.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from viscocrowd.core.state import GRAVITE
from viscocrowd.io.trajectoires import Trajectoire


def energie_mecanique(
    x: np.ndarray,
    v: np.ndarray,
    masse: np.ndarray | float = 1.0,
    gravite: np.ndarray = GRAVITE,
) -> np.ndarray:
    """Energie mecanique totale du systeme, en joules.

    Args:
        x: positions, de forme (..., N, 2), en metres.
        v: vitesses, de forme (..., N, 2), en m/s.
        masse: masse des particules, scalaire ou de forme (N,), en kg.
        gravite: vecteur gravite, de forme (2,), en m/s^2.

    Returns:
        L'energie totale, de forme (...) : un scalaire par instant.
    """
    masse_arr = np.asarray(masse, dtype=float)

    cinetique = 0.5 * masse_arr * np.sum(v**2, axis=-1)  # (..., N)
    potentielle = -masse_arr * (x @ gravite)  # (..., N)

    return np.sum(cinetique + potentielle, axis=-1)


def ecart_entrainement(v: np.ndarray, v_solide: np.ndarray) -> np.ndarray:
    """Norme de l'ecart entre la vitesse reelle et la vitesse d'entrainement.

    Doit tendre vers zero une fois l'energie disponible dissipee : la particule
    se stabilise dans un coin et tourne solidairement avec le domaine.

    Returns:
        L'ecart maximal sur les particules, de forme (...), en m/s.
    """
    return np.max(np.linalg.norm(v - v_solide, axis=-1), axis=-1)


def energie_mecanique_trajectoire(
    archive: Trajectoire | str | Path,
    masse: np.ndarray | float = 1.0,
    gravite: np.ndarray = GRAVITE,
    *,
    autoriser_espace: bool = False,
) -> np.ndarray:
    """Energie mecanique calculee sur les pas d'une archive.

    Par defaut, refuse toute archive espacee (K > 1, issue #73), car une montee
    d'energie ou un pic de dissipation entre deux images non enregistrees ne
    serait pas detecte. `autoriser_espace=True` permet d'evaluer l'energie ponctuelle
    aux seuls pas conserves.
    """
    if isinstance(archive, (str, Path)):
        from viscocrowd.io.trajectoires import lire_trajectoire

        donnees = lire_trajectoire(archive)
    elif isinstance(archive, Trajectoire):
        donnees = archive
    else:
        raise TypeError(
            f"source de trajectoire invalide (attendu Trajectoire, str ou Path, "
            f"recu {type(archive).__name__})"
        )
    if not autoriser_espace:
        donnees.exiger_complete("le calcul de l'energie mecanique")
    return energie_mecanique(donnees.x, donnees.v, masse=masse, gravite=gravite)
