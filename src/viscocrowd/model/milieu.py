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

Ce module ne connait ni la geometrie ni le guidage. `acceleration` et
`vitesse_libre` recoivent U, tau et a_max deja evalues pour chaque agent ;
`pas_libre_milieux` les assemble a partir de trois pieces fournies par
ailleurs (contrat propose dans l'issue #26) :

    direction(etat) -> (N, 2)      guidage, vecteurs unitaires    (G1/G2)
    zone(x)         -> (N,)        milieu sous chaque agent       (C6)
    parametres      {Milieu: ParametresMilieu}, avec unites       (C6)

Les valeurs des trois milieux et la carte qui les associe a une position
relevent de la tache C6 du planning ; aucune n'est fixee ici.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from enum import IntEnum

import numpy as np

from viscocrowd.core.integrator import VitesseLibre
from viscocrowd.core.state import State
from viscocrowd.core.verifications import (
    TOLERANCE_UNITAIRE,
    exiger_fini,
    exiger_scalaire_fini,
)
from viscocrowd.model.espacement import facteur_espacement


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
    exiger_scalaire_fini("le pas de temps dt", dt, strictement_positif=True)
    return np.asarray(v, dtype=float) + dt * acceleration(v, u, relaxation, acceleration_max)


class Milieu(IntEnum):
    """Les trois sols de la piscine. La valeur entiere est celle que rend `zone`."""

    EAU = 0
    MOUILLE = 1
    SEC = 2


@dataclass(frozen=True)
class ParametresMilieu:
    """Ce que le sol impose a la marche, pour un milieu (spec § 2.3 et 2.4).

    Attributes:
        relaxation: tau, en s. Strictement positif.
        acceleration_max: a_max, en m/s^2. Strictement positive.
        vitesse: vitesse souhaitee s, en m/s. Positive ou nulle : un milieu ou
            l'on ne cherche pas a avancer est un cas limite admissible.
    """

    relaxation: float
    acceleration_max: float
    vitesse: float

    def __post_init__(self) -> None:
        # Forme positive : `NaN <= 0` est faux, un NaN passerait sinon.
        for nom in ("relaxation", "acceleration_max"):
            exiger_scalaire_fini(nom, getattr(self, nom), strictement_positif=True)
        exiger_scalaire_fini("vitesse", self.vitesse)
        if not self.vitesse >= 0.0:
            raise ValueError(f"vitesse doit etre positive ou nulle, recu {self.vitesse}")


# Direction de guidage (N, 2) de chaque agent, vecteurs unitaires (ou nuls).
Direction = Callable[[State], np.ndarray]

# Milieu (N,) sous chaque position (N, 2), en valeurs de `Milieu`.
CarteZones = Callable[[np.ndarray], np.ndarray]

# Tolerance sur la norme d'une direction : un gradient non normalise doit etre refuse.
_TOLERANCE_UNITAIRE = TOLERANCE_UNITAIRE


def pas_libre_milieux(
    direction: Direction,
    zone: CarteZones,
    parametres: Mapping[Milieu, ParametresMilieu],
    *,
    facteur_vitesse: float = 1.0,
    temps_espacement: float | None = None,
    avancement: Callable[[np.ndarray], np.ndarray] | None = None,
) -> VitesseLibre:
    """Vitesse libre d'agents guides sur des sols differents, pour `core.integrator`.

    A chaque pas, pour chaque agent :

        m       = zone(x)                               milieu sous l'agent
        U       = facteur_vitesse * s[m] * direction    vitesse desiree
        v_libre = vitesse_libre(v, U, tau[m], a_max[m], dt)

    Le milieu est evalue a la position du DEBUT du pas, coherent avec un pas
    libre explicite : un agent qui franchit une frontiere prend les parametres
    du nouveau sol au pas suivant. L'erreur reste d'ordre 1 en dt, mais elle est
    AMPLIFIEE par le contraste d'adherence. Mesure, freinage de 1,5 m/s a travers
    une frontiere sec (5,9 m/s^2) | mouille (1 m/s^2) : erreur sur le point
    d'arret entre 2,0 dt et 6,9 dt selon la position de la frontiere dans le pas,
    contre 0,8 dt sans frontiere. Le pas qui chevauche la frontiere freine avec
    l'adherence du sec, et l'ecart de vitesse se paie ensuite sur le mouille, a
    a_max plus faible.

    Args:
        direction: guidage, (N, 2) vecteurs unitaires ou nuls (un agent arrive
            peut ne plus avoir de direction). Toute norme non nulle differente
            de 1 a 1e-9 pres est refusee : un gradient non normalise multiplierait
            la vitesse souhaitee sans que rien ne le signale.
        zone: milieu sous chaque agent, (N,) entiers parmi les valeurs de `Milieu`.
        parametres: les parametres de chaque milieu utilise. Un scenario peut
            n'en declarer qu'une partie, comme l'etalonnage E0 en sol sec seul ;
            un agent sur un milieu non declare leve alors une erreur.
        facteur_vitesse: multiplie toutes les vitesses souhaitees, pour le
            niveau de panique de la spec § 2.3. Positif ou nul.
        temps_espacement: T (s) de la relation vitesse-espacement de
            `model.espacement` : la vitesse souhaitee est ramenee a jeu / T
            derriere un meneur. None, par defaut, la desactive.
        avancement: temps restant jusqu'a la sortie (N,) aux positions (N, 2),
            en s ; ordonne les agents pour la relation vitesse-espacement, dont
            le meneur doit etre plus avance. Exige si `temps_espacement` est donne.

    Returns:
        Une fonction (etat, dt) -> v_libre, a passer a `pas_semi_implicite`,
        `simuler` ou `trajectoire`.

    Raises:
        ValueError: a la construction si `parametres` est vide ou si
            `facteur_vitesse` est invalide ; a chaque pas si `zone` ou
            `direction` rend une valeur mal formee, non finie ou hors contrat.
    """
    if not parametres:
        raise ValueError("il faut les parametres d'au moins un milieu")
    exiger_scalaire_fini("facteur_vitesse", facteur_vitesse)
    if not facteur_vitesse >= 0.0:
        raise ValueError(f"facteur_vitesse doit etre positif ou nul, recu {facteur_vitesse}")
    if temps_espacement is not None:
        exiger_scalaire_fini("temps_espacement", temps_espacement, strictement_positif=True)
        if avancement is None:
            # Sans ordre d'avancement, des cycles d'attente redeviendraient possibles.
            raise ValueError("temps_espacement exige une fonction avancement")

    # Tables indexees par la valeur du milieu. NaN pour un milieu non declare :
    # jamais lu, puisque `declare` est controle avant toute indexation.
    taille = max(Milieu) + 1
    tau, a_max, s = (np.full(taille, np.nan) for _ in range(3))
    declare = np.zeros(taille, dtype=bool)
    for milieu, p in parametres.items():
        m = Milieu(milieu)
        tau[m], a_max[m], s[m] = p.relaxation, p.acceleration_max, p.vitesse
        declare[m] = True

    def _vitesse(etat: State, dt: float) -> np.ndarray:
        m = _zones_valides(zone(etat.x), etat.n, declare)
        e = np.asarray(direction(etat), dtype=float)
        if e.shape != (etat.n, 2):
            raise ValueError(f"direction doit etre de forme ({etat.n}, 2), recu {e.shape}")
        exiger_fini("Le guidage a rendu une direction non finie.", direction=e)
        normes = np.hypot(e[:, 0], e[:, 1])
        non_unitaires = np.flatnonzero(
            (normes != 0.0) & (np.abs(normes - 1.0) > _TOLERANCE_UNITAIRE)
        )
        if non_unitaires.size:
            raise ValueError(
                f"direction doit etre unitaire ou nulle pour les agents "
                f"{non_unitaires[:5].tolist()} — gradient non normalise ?"
            )

        vitesse = facteur_vitesse * s[m]
        if temps_espacement is not None:
            avance = np.asarray(avancement(etat.x), dtype=float)
            vitesse = vitesse * facteur_espacement(
                etat.x, etat.r, e, avance, vitesse, temps_espacement
            )
        u = vitesse[:, None] * e
        return vitesse_libre(etat.v, u, tau[m], a_max[m], dt)

    return _vitesse


def _zones_valides(m: np.ndarray, n: int, declare: np.ndarray) -> np.ndarray:
    """Controle la sortie de `zone` et la rend en indices entiers (N,)."""
    m = np.asarray(m)
    if m.shape != (n,):
        raise ValueError(f"zone doit rendre un tableau de forme ({n},), recu {m.shape}")
    if not np.issubdtype(m.dtype, np.integer):
        # Un flottant (ou un NaN) indexerait de travers ou pas du tout : on refuse.
        raise ValueError(f"zone doit rendre des entiers (valeurs de Milieu), recu {m.dtype}")
    hors_milieux = (m < 0) | (m >= declare.size)
    non_declares = ~hors_milieux & ~declare[np.where(hors_milieux, 0, m)]
    fautifs = np.flatnonzero(hors_milieux | non_declares)
    if fautifs.size:
        raise ValueError(
            f"milieu inconnu ou sans parametres sous les agents {fautifs[:5].tolist()} "
            f"(valeurs {np.unique(m[fautifs]).tolist()})"
        )
    return m
