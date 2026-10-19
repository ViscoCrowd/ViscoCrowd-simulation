"""Effet du sol sur la marche : temps de relaxation et adherence (spec § 2.4).

Chaque agent cherche a passer de sa vitesse actuelle v a sa vitesse desiree U.
Le sol limite la facon dont il peut le faire, par deux parametres :

  - tau, le TEMPS DE RELAXATION (s) : la rapidite avec laquelle l'agent corrige
    l'ecart entre v et U. Sans autre limite, il en rattrape environ 63 % en un
    temps tau (la part 1 - 1/e d'une relaxation exponentielle) ;
  - a_max, l'ACCELERATION MAXIMALE (m/s^2) : la traction que le sol peut fournir.
    Demander plus, c'est glisser. Sur carrelage mouille elle est faible : on ne
    peut ni freiner ni tourner vite. C'est le terme d'inertie de la problematique.

    a       = (U - v) / tau, ramenee a la norme a_max si elle la depasse
    v_libre = v + dt * a

La borne porte sur la NORME de l'acceleration, pas sur chacune de ses deux
composantes. Borner composante par composante changerait la direction de
l'acceleration : un agent qui veut freiner en diagonale freinerait de travers.
Ramener la norme garde la direction voulue et ne reduit que l'intensite.

Ce module ne connait ni la geometrie ni le guidage : il recoit U, tau et a_max
deja evalues pour chaque agent. Les valeurs des trois milieux (eau, carrelage
mouille, sol sec) et la carte qui les associe a une position relevent de la
tache C6 du planning ; aucune n'est fixee ici.
"""

from __future__ import annotations

import numpy as np

from viscocrowd.core.verifications import exiger_fini


def _verifier_parametre(nom: str, valeur: np.ndarray | float, n: int) -> np.ndarray:
    """Rend le parametre en tableau (N,), fini et strictement positif."""
    tableau = np.broadcast_to(np.asarray(valeur, dtype=float), (n,))
    exiger_fini("Un parametre de milieu doit etre un nombre fini.", **{nom: tableau})
    if np.any(tableau <= 0.0):
        raise ValueError(f"{nom} doit etre strictement positif pour chaque agent")
    return tableau


def acceleration(
    v: np.ndarray,
    u: np.ndarray,
    relaxation: np.ndarray | float,
    acceleration_max: np.ndarray | float,
) -> np.ndarray:
    """Acceleration de chaque agent vers sa vitesse desiree, bornee par le sol.

    Args:
        v: vitesses actuelles, de forme (N, 2), en m/s.
        u: vitesses desirees, de forme (N, 2), en m/s.
        relaxation: tau, scalaire ou de forme (N,), en s. Strictement positif.
        acceleration_max: a_max, scalaire ou de forme (N,), en m/s^2.
            Strictement positive.

    Returns:
        Les accelerations, de forme (N, 2), en m/s^2, de norme au plus a_max.

    Raises:
        ValueError: si une entree est non finie, ou si tau ou a_max n'est pas
            strictement positif.
    """
    v, u = np.asarray(v, dtype=float), np.asarray(u, dtype=float)
    if v.shape != u.shape or v.ndim != 2 or v.shape[1] != 2:
        raise ValueError(f"v et u doivent etre de forme (N, 2), recu {v.shape} et {u.shape}")
    exiger_fini("Vitesses d'entree du milieu.", v=v, u=u)
    n = v.shape[0]
    tau = _verifier_parametre("relaxation", relaxation, n)
    a_max = _verifier_parametre("acceleration_max", acceleration_max, n)

    a_voulue = (u - v) / tau[:, None]
    norme = np.linalg.norm(a_voulue, axis=1)

    # Facteur de reduction : 1 si l'agent reste dans l'adherence, a_max / |a|
    # sinon. Un agent deja a sa vitesse desiree a |a| = 0 : facteur 1, sans
    # division par zero.
    facteur = np.minimum(1.0, a_max / np.where(norme > 0.0, norme, np.inf))
    return a_voulue * facteur[:, None]


def vitesse_libre(
    v: np.ndarray,
    u: np.ndarray,
    relaxation: np.ndarray | float,
    acceleration_max: np.ndarray | float,
    dt: float,
) -> np.ndarray:
    """Vitesse avant contraintes apres un pas dt : v + dt * a (spec § 2.4).

    C'est la vitesse libre du schema semi-implicite : la projection
    (exclusion, parois) s'applique ensuite, dans `core.integrator`.

    Args:
        v, u, relaxation, acceleration_max: voir `acceleration`.
        dt: pas de temps, en s. Strictement positif.

    Returns:
        Les vitesses libres, de forme (N, 2), en m/s.
    """
    if not (np.isfinite(dt) and dt > 0.0):
        raise ValueError(f"le pas de temps doit etre fini et strictement positif, recu {dt}")
    return np.asarray(v, dtype=float) + dt * acceleration(v, u, relaxation, acceleration_max)
