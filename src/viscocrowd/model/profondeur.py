"""Profondeur variable du bassin : la vitesse des nageurs depend de la profondeur (option).

La vitesse dans l'eau de la reference vient de V = 0,53 M^(-0,19), M = d^2/2 en eau calme
(d'apres shirvani2020, eq. 1 ; journal du 25 octobre 2026), soit 0,69 m/s a d = 0,7 m. Elle
est donc proportionnelle a d^(-0,38) : marcher dans une eau plus profonde est plus lent.
Avec une profondeur qui varie le long du bassin, chaque nageur avance a

    v(x) = v_eau * (d(x) / 0,7)^(-0,38)

ou v_eau est la vitesse du YAML (celle de 0,7 m). La profondeur varie lineairement en x,
d'un bord du bassin a l'autre.

Domaine : Bernardini et al. (2020), d'apres shirvani2021these, ont mesure en eau calme de
0,2 a 0,7 m. Le code accepte 0,2 a 1,0 m pour representer un petit bain ; AU-DELA DE 0,7 M,
C'EST UNE EXTRAPOLATION de la loi, a signaler. Plus profond, on nage : la formule ne
s'applique plus.
"""

from __future__ import annotations

import numpy as np

from viscocrowd.geometry.obstacle import ObstacleRectangle

PROFONDEUR_REFERENCE = 0.7  # m : profondeur de la vitesse `EAU.vitesse` du YAML
PROFONDEUR_MIN = 0.2  # m : plus faible profondeur mesuree (Bernardini et al. 2020)
PROFONDEUR_MAX = 1.0  # m : extrapolation au-dela de 0,7 m, petit bain au plus
EXPOSANT = -0.38  # V proportionnel a (d^2)^-0,19


def profondeur(
    x: np.ndarray, bassin: ObstacleRectangle, gauche: float, droite: float
) -> np.ndarray:
    """Profondeur (N,) sous chaque position (N, 2), en m, lineaire en x, bornee aux bords.

    Args:
        gauche, droite: profondeurs au bord gauche (x_min) et droit (x_max) du bassin, en m.
    """
    s = (np.asarray(x, dtype=float)[:, 0] - bassin.x_min) / (bassin.x_max - bassin.x_min)
    s = np.clip(s, 0.0, 1.0)
    return gauche + (droite - gauche) * s


def facteur_profondeur(d: np.ndarray) -> np.ndarray:
    """Facteur (sans unite) de la vitesse dans l'eau a la profondeur d (m) : (d / 0,7)^-0,38."""
    d = np.asarray(d, dtype=float)
    if not np.all(np.isfinite(d)) or np.any(d < PROFONDEUR_MIN) or np.any(d > PROFONDEUR_MAX):
        domaine = f"[{PROFONDEUR_MIN} ; {PROFONDEUR_MAX}] m"
        raise ValueError(f"profondeur hors du domaine {domaine} de la loi de vitesse")
    return (d / PROFONDEUR_REFERENCE) ** EXPOSANT
