"""Densite et vitesse de Voronoi dans une zone de mesure (spec § 3, tache M1).

Compter les agents d'une zone donne une densite en paliers entiers : un agent
qui entre fait sauter la valeur de 1/|M|. La methode de Voronoi de Steffen &
Seyfried (2010) attribue a chaque agent i la cellule Ci des points plus proches
de lui que de tout autre, et la densite locale 1/|Ci| sur cette cellule. Dans une
zone de mesure M :

    rho_V = (1/|M|) * somme_i |Ci inter M| / |Ci|          (pers/m^2)
    v_V   = (1/|M|) * somme_i |vi| |Ci inter M|            (m/s)

Un agent ne compte plus 0 ou 1 : il compte la fraction de sa cellule qui tombe
dans M. La mesure varie continument quand les agents bougent.

Cellules bornees
----------------

Les cellules des agents du bord sont infinies. On les borne par la salle, un
rectangle, en ajoutant le reflet de chaque agent par rapport a chacun des quatre
murs : la mediatrice entre un agent et son reflet est le mur lui-meme. Pour un
domaine convexe comme un rectangle, ce procede donne EXACTEMENT les cellules
decoupees par la salle (les cellules pavent la salle).

Le calcul des cellules est confie a `scipy.spatial.Voronoi` (calcul geometrique
generaliste, cf. issue #19) ; le decoupage par la zone de mesure, les aires et
les moyennes sont ecrits ici. `mesures_voronoi` rend densite et vitesse d'un
meme calcul de cellules, comme le demande un diagramme fondamental.

Limite de portee
----------------

La salle est un rectangle aligne sur les axes, et tous les agents doivent etre
strictement dedans. Le procede des reflets vaut pour tout polygone convexe, mais
il n'est ecrit ici que pour un rectangle. La salle du goulot n'est pas convexe et
le couloir est ouvert en aval : on ne peut pas y mesurer en ecartant simplement
les agents hors du rectangle. Cela creerait un faux mur a la coupe, ou les
cellules voisines seraient trop grandes et la densite sous-estimee. Pour M8,
il faudra soit une zone de mesure loin de toute coupe, soit decouper les cellules
par le vrai domaine.

Repli sans Voronoi : `densite_comptage(x, zone)`, N dans M divise par |M|. Il
ne demande pas de salle.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.spatial import QhullError, Voronoi

from viscocrowd.core.verifications import (
    TOLERANCE_UNITAIRE,
    exiger_fini,
    exiger_scalaire_fini,
)


@dataclass(frozen=True)
class Rectangle:
    """[x_min, x_max] x [y_min, y_max], en m : salle ou zone de mesure."""

    x_min: float
    x_max: float
    y_min: float
    y_max: float

    def __post_init__(self) -> None:
        for nom in ("x_min", "x_max", "y_min", "y_max"):
            exiger_scalaire_fini(nom, getattr(self, nom))
        if not (self.x_max > self.x_min and self.y_max > self.y_min):
            raise ValueError("le rectangle doit etre d'aire strictement positive")

    @property
    def aire(self) -> float:
        return (self.x_max - self.x_min) * (self.y_max - self.y_min)

    def contient(self, autre: Rectangle) -> bool:
        return (
            self.x_min <= autre.x_min
            and autre.x_max <= self.x_max
            and self.y_min <= autre.y_min
            and autre.y_max <= self.y_max
        )


def _positions(x: np.ndarray, salle: Rectangle) -> np.ndarray:
    x = np.asarray(x, dtype=float)
    if x.ndim != 2 or x.shape[1] != 2 or x.shape[0] == 0:
        raise ValueError(f"x doit etre de forme (N, 2), N >= 1, recu {x.shape}")
    exiger_fini("Positions transmises a la mesure de densite.", x=x)
    if np.unique(x, axis=0).shape[0] != x.shape[0]:
        raise ValueError("les centres doivent etre distincts pour mesurer leur densite")
    # Strictement a l'interieur : un agent sur un mur coinciderait avec son reflet.
    if np.any(
        (x[:, 0] <= salle.x_min)
        | (x[:, 0] >= salle.x_max)
        | (x[:, 1] <= salle.y_min)
        | (x[:, 1] >= salle.y_max)
    ):
        raise ValueError("chaque agent doit etre strictement a l'interieur de la salle")
    return x


def _polygone(p: np.ndarray) -> np.ndarray:
    """Sommets (K, 2) en flottants : accepte aussi une liste, refuse une autre forme."""
    p = np.asarray(p, dtype=float)
    if p.size == 0:
        return p.reshape(0, 2)
    if p.ndim != 2 or p.shape[1] != 2:
        raise ValueError(f"un polygone doit etre de forme (K, 2), recu {p.shape}")
    exiger_fini("Sommets d'un polygone.", p=p)
    return p


def aire_polygone(p: np.ndarray) -> float:
    """Aire (m^2) d'un polygone (K, 2) aux sommets ordonnes, formule du lacet."""
    p = _polygone(p)
    if p.shape[0] < 3:
        return 0.0
    x, y = p[:, 0], p[:, 1]
    return 0.5 * abs(float(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1))))


def decouper(p: np.ndarray, zone: Rectangle) -> np.ndarray:
    """Intersection d'un polygone convexe (K, 2) et d'un rectangle (Sutherland-Hodgman)."""
    p = _polygone(p)
    # Chaque demi-plan : (axe, borne, garde le cote >= borne si sens = +1).
    for axe, borne, sens in (
        (0, zone.x_min, 1.0),
        (0, zone.x_max, -1.0),
        (1, zone.y_min, 1.0),
        (1, zone.y_max, -1.0),
    ):
        if p.shape[0] == 0:
            break
        suivant = np.roll(p, -1, axis=0)
        d, d_suivant = sens * (p[:, axe] - borne), sens * (suivant[:, axe] - borne)
        sortie = []
        for k in range(p.shape[0]):
            if d[k] >= 0.0:
                sortie.append(p[k])
            if (d[k] >= 0.0) != (d_suivant[k] >= 0.0):
                s = d[k] / (d[k] - d_suivant[k])
                sortie.append(p[k] + s * (suivant[k] - p[k]))
        p = np.array(sortie).reshape(-1, 2)
    return p


def cellules(x: np.ndarray, salle: Rectangle) -> list[np.ndarray]:
    """Cellule de Voronoi (K, 2) de chaque agent, decoupee par la salle, sommets ordonnes."""
    return _cellules_et_aires(x, salle)[0]


def _cellules_et_aires(x: np.ndarray, salle: Rectangle) -> tuple[list[np.ndarray], np.ndarray]:
    x = _positions(x, salle)
    reflets = [
        x,
        np.column_stack((2 * salle.x_min - x[:, 0], x[:, 1])),
        np.column_stack((2 * salle.x_max - x[:, 0], x[:, 1])),
        np.column_stack((x[:, 0], 2 * salle.y_min - x[:, 1])),
        np.column_stack((x[:, 0], 2 * salle.y_max - x[:, 1])),
    ]
    try:
        diagramme = Voronoi(np.concatenate(reflets))
    except QhullError as erreur:
        raise ValueError(
            "partition de Voronoi degeneree : centres numeriquement inseparables"
        ) from erreur
    regions = diagramme.point_region[: x.shape[0]]
    if np.unique(regions).size != x.shape[0]:
        raise ValueError("partition de Voronoi degeneree : plusieurs centres partagent une cellule")
    resultat = []
    for i in range(x.shape[0]):
        region = diagramme.regions[diagramme.point_region[i]]
        if -1 in region or not region:
            # ValueError comme tous les cas degeneres : un appelant qui ecarte les
            # instantanes degeneres n'a qu'une exception a attraper.
            raise ValueError("partition de Voronoi degeneree : cellule non bornee")
        sommets = diagramme.vertices[region]
        # Ordre angulaire autour de l'agent : la cellule est convexe et le contient.
        angles = np.arctan2(sommets[:, 1] - x[i, 1], sommets[:, 0] - x[i, 0])
        resultat.append(sommets[np.argsort(angles)])
    aires = np.array([aire_polygone(p) for p in resultat])
    if not np.all(np.isfinite(aires) & (aires > 0.0)) or not np.isclose(
        aires.sum(), salle.aire, rtol=1e-8, atol=0.0
    ):
        raise ValueError("partition de Voronoi degeneree : les cellules ne pavent pas la salle")
    return resultat, aires


def _fractions(x: np.ndarray, salle: Rectangle, zone: Rectangle) -> tuple[np.ndarray, np.ndarray]:
    """Aires |Ci| et |Ci inter M| de chaque agent, en m^2, d'un seul calcul de cellules."""
    if not salle.contient(zone):
        raise ValueError("la zone de mesure doit etre incluse dans la salle")
    polygones, aires = _cellules_et_aires(x, salle)
    dans_zone = np.empty_like(aires)
    for i, p in enumerate(polygones):
        (x0, y0), (x1, y1) = p.min(axis=0), p.max(axis=0)
        # Boite englobante d'abord : la plupart des cellules sont toutes dedans ou toutes
        # dehors, et le decoupage n'est utile qu'aux cellules a cheval sur le bord de M.
        if zone.x_min <= x0 and x1 <= zone.x_max and zone.y_min <= y0 and y1 <= zone.y_max:
            dans_zone[i] = aires[i]
        elif x1 <= zone.x_min or x0 >= zone.x_max or y1 <= zone.y_min or y0 >= zone.y_max:
            dans_zone[i] = 0.0
        else:
            dans_zone[i] = aire_polygone(decouper(p, zone))
    return aires, dans_zone


def _vitesses(v: np.ndarray, x: np.ndarray, direction) -> np.ndarray:
    """Vitesse scalaire de chaque agent, en m/s : norme, ou composante sur `direction`."""
    v = np.asarray(v, dtype=float)
    if v.shape != np.shape(x):
        raise ValueError("v doit avoir la forme de x")
    exiger_fini("Vitesses transmises a la mesure de vitesse.", v=v)
    if direction is None:
        return np.hypot(v[:, 0], v[:, 1])
    e = np.asarray(direction, dtype=float)
    if e.shape != (2,) or not abs(np.hypot(*e) - 1.0) <= TOLERANCE_UNITAIRE:
        raise ValueError("direction doit etre un vecteur unitaire (2,)")
    return v @ e


def densite_voronoi(x: np.ndarray, salle: Rectangle, zone: Rectangle) -> float:
    """Densite de Voronoi dans la zone de mesure, en pers/m^2. Voir le module."""
    aires, dans_zone = _fractions(x, salle, zone)
    return float(np.sum(dans_zone / aires) / zone.aire)


def vitesse_voronoi(
    x: np.ndarray, v: np.ndarray, salle: Rectangle, zone: Rectangle, direction=None
) -> float:
    """Vitesse de Voronoi dans la zone, en m/s : norme, ou composante sur `direction`."""
    vitesses = _vitesses(v, x, direction)
    _, dans_zone = _fractions(x, salle, zone)
    return float(np.sum(vitesses * dans_zone) / zone.aire)


def mesures_voronoi(
    x: np.ndarray, v: np.ndarray, salle: Rectangle, zone: Rectangle, direction=None
) -> tuple[float, float]:
    """(densite en pers/m^2, vitesse en m/s) d'un meme calcul de cellules.

    Identiques a `densite_voronoi` et `vitesse_voronoi`, pour moitie moins de calcul :
    un point du diagramme fondamental demande les deux a chaque instant.
    """
    vitesses = _vitesses(v, x, direction)
    aires, dans_zone = _fractions(x, salle, zone)
    return (
        float(np.sum(dans_zone / aires) / zone.aire),
        float(np.sum(vitesses * dans_zone) / zone.aire),
    )


def densite_comptage(x: np.ndarray, zone: Rectangle) -> float:
    """Repli sans Voronoi : agents dont le centre est dans la zone, divise par |M|."""
    x = np.asarray(x, dtype=float)
    if x.ndim != 2 or x.shape[1] != 2:
        raise ValueError(f"x doit etre de forme (N, 2), recu {x.shape}")
    exiger_fini("Positions transmises au comptage.", x=x)
    dedans = (
        (x[:, 0] >= zone.x_min)
        & (x[:, 0] < zone.x_max)
        & (x[:, 1] >= zone.y_min)
        & (x[:, 1] < zone.y_max)
    )
    return float(np.sum(dedans) / zone.aire)
