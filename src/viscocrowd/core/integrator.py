"""Schema d'integration en temps : semi-implicite, puis projection.

Ce module est le coeur du moteur et ne connait rien a la notion de foule. Il
integre un systeme de particules soumis a des contraintes, quelles qu'elles
soient. Toute la semantique « foule » vit dans viscocrowd.model.

Un pas se decompose en trois temps :

    1. pas libre      : on calcule ou la particule irait sans contrainte ;
    2. projection     : on ramene la configuration dans l'ensemble admissible ;
    3. relecture de v : v = (x_nouveau - x_ancien) / dt.

L'etape 3 est celle qui porte toute la physique du choc. La vitesse n'est pas
transportee d'un pas a l'autre : elle est deduite du deplacement reellement
effectue. Si la projection a annule le deplacement normal, elle annule du meme
coup la composante normale de la vitesse — traduction discrete de la loi de
choc mou.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator

import numpy as np

from viscocrowd.core.state import State

# Calcule la vitesse libre (N, 2) a partir de l'etat courant et du pas de temps.
VitesseLibre = Callable[[State, float], np.ndarray]

# Ramene des positions libres (N, 2) dans l'ensemble admissible, au temps donne.
Projection = Callable[[np.ndarray, np.ndarray, float], np.ndarray]


def pas_semi_implicite(
    etat: State,
    dt: float,
    vitesse_libre: VitesseLibre,
    projection: Projection | None = None,
) -> State:
    """Avance l'etat d'un pas de temps dt.

    Args:
        etat: configuration au temps t.
        dt: pas de temps, en secondes. Strictement positif.
        vitesse_libre: rend la vitesse (N, 2) avant prise en compte des
            contraintes. C'est ici qu'interviennent la gravite, le frottement
            du milieu et la vitesse desiree des agents.
        projection: ramene les positions libres dans l'ensemble admissible.
            Si None, le pas est libre (aucune contrainte).

    Returns:
        La configuration au temps t + dt.
    """
    if dt <= 0.0:
        raise ValueError(f"le pas de temps doit etre strictement positif, recu {dt}")

    t_arrivee = etat.t + dt

    v_libre = vitesse_libre(etat, dt)
    x_libre = etat.x + dt * v_libre

    if projection is None:
        return etat.advanced(x=x_libre, v=v_libre, t=t_arrivee)

    # La projection est evaluee a l'instant d'ARRIVEE : si le domaine bouge,
    # la contrainte porte sur sa position en t + dt, pas en t. Inverser les
    # deux produit un programme qui semble fonctionner mais dont le
    # comportement en domaine rapidement mobile est faux.
    x_nouveau = projection(x_libre, etat.r, t_arrivee)

    # LE CHOC EST ICI.
    v_nouveau = (x_nouveau - etat.x) / dt

    return etat.advanced(x=x_nouveau, v=v_nouveau, t=t_arrivee)


def chute_libre(gravite: np.ndarray) -> VitesseLibre:
    """Vitesse libre d'une particule en chute libre : v + dt * g."""

    def _vitesse(etat: State, dt: float) -> np.ndarray:
        return etat.v + dt * gravite

    return _vitesse


def simuler(
    etat_initial: State,
    dt: float,
    duree: float,
    vitesse_libre: VitesseLibre,
    projection: Projection | None = None,
) -> Iterator[State]:
    """Genere la suite des etats de t=0 a t>=duree, etat initial inclus.

    Rendu sous forme de generateur : une campagne de simulation peut agreger
    ses observables au vol sans conserver toute la trajectoire en memoire.
    """
    n_pas = int(np.ceil(duree / dt))

    etat = etat_initial
    yield etat
    for _ in range(n_pas):
        etat = pas_semi_implicite(etat, dt, vitesse_libre, projection)
        yield etat


def trajectoire(
    etat_initial: State,
    dt: float,
    duree: float,
    vitesse_libre: VitesseLibre,
    projection: Projection | None = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Simule et rend la trajectoire complete.

    Returns:
        (t, x, v) de formes (P,), (P, N, 2) et (P, N, 2), ou P est le nombre
        de pas enregistres.
    """
    etats = list(simuler(etat_initial, dt, duree, vitesse_libre, projection))
    t = np.array([e.t for e in etats])
    x = np.stack([e.x for e in etats])
    v = np.stack([e.v for e in etats])
    return t, x, v
