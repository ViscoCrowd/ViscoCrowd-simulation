"""Champ de guidage eikonal, resolu par Fast Marching (spec § 2.6, tache G2).

On cherche phi(x), le temps de parcours minimal jusqu'a la sortie pour un agent
qui se deplace a la vitesse locale F(x), en m/s :

    |grad phi(x)| = 1 / F(x),     phi = 0 sur la sortie.

La direction de guidage est la plus forte descente, e = -grad phi / |grad phi|.
Comme F depend du milieu, phi arbitre de lui-meme entre un chemin court mais
lent et un chemin long mais rapide. Un obstacle est un point ou F = 0 : le temps
de parcours y est infini, et le champ le contourne.

Fast Marching (Sethian, 1996)
-----------------------------

Sur une grille reguliere de pas h, on discretise |grad phi| = 1/F par differences
AMONT : dans chaque direction, on ne regarde que le voisin deja fixe le plus
proche de la sortie. Avec a et b ces deux valeurs, a <= b, et f = h / F le temps
de traversee d'une maille :

    phi = a + f                                   si b - a >= f
    phi = (a + b + sqrt(2 f^2 - (b - a)^2)) / 2   sinon

La premiere ligne est une onde qui arrive d'une seule direction, la seconde une
onde oblique. Le schema est causal : phi en un noeud ne depend que de voisins
plus petits. On fixe donc les noeuds par phi croissant, comme Dijkstra, avec un
tas : chaque noeud est fixe une fois, pour un cout O(n log n).

Ce qui est exact, ce qui est mesure
-----------------------------------

  - Une onde plane alignee sur la grille est EXACTE : sortie sur une colonne et
    vitesse ne dependant que de x donnent phi = integrale de x a L de 1/F, a
    1e-13 pres, bandes de milieux comprises quand leurs frontieres tombent sur
    des noeuds. Une frontiere entre deux noeuds coute au plus h |1/F1 - 1/F2|.
  - Ailleurs le schema est d'ordre 1 en h, et surestime phi (ecart minimal
    mesure -3e-14 s, donc nul aux arrondis pres). Source ponctuelle,
    F = 1 m/s, carre de 4 m : erreur maximale 0,103 ; 0,062 ; 0,037 s pour
    h = 0,1 ; 0,05 ; 0,025 m (erreur moyenne 0,057 ; 0,035 ; 0,021 s). La
    convergence est un peu plus lente que h, a cause de la singularite de la
    source ; elle est exacte sur les axes. La direction s'ecarte au pire de 7,1 ;
    5,2 ; 3,6 degres de la direction exacte.
  - Detour d'un obstacle de 1 x 1,5 m, F = 1 m/s : erreur maximale dans son ombre
    0,131 ; 0,090 ; 0,050 s pour les memes pas, sur un parcours d'environ 11 s.

Cout initial mesure : 0,16 s pour les 99 086 noeuds de l'emprise de la piscine
(48 x 20,5 m) a h = 0,1 m, calcules une fois. Apres le correctif d'interpolation
aux cretes, environ 0,21 ms par appel pour guider 500 agents sur le poste de revue.

Gradient et direction
---------------------

Le gradient est pris par les memes differences amont, au noeud : dans chaque
direction, la pente vers le voisin le plus petit, nulle si aucun voisin ne
descend. Sur une crete, ou les deux voisins sont egaux (derriere un obstacle
symetrique), on prend toujours le voisin d'indice inferieur : la symetrie est
brisee de facon deterministe, et l'agent contourne au lieu de buter.

Aux positions des agents, le gradient est interpole bilineairement entre les
quatre noeuds voisins, puis normalise. Si deux gradients qui contribuent forment
un angle obtus, la maille chevauche des branches de descente opposees : leur
moyenne pourrait annuler le guidage hors sortie. On choisit alors le gradient
non nul du noeud contributeur de plus petit phi (ordre fixe en cas d'egalite).
Ce choix local de branche ne garantit pas le chemin continu optimal. Un noeud
d'obstacle ou de sortie a un gradient nul : il ne contribue pas. Un agent dont
les quatre noeuds sont nuls recoit une direction nulle, ce que le contrat de
`pas_libre_milieux` admet pour un agent arrive ou dans une zone inaccessible.
"""

from __future__ import annotations

import heapq
import math
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from numbers import Integral

import numpy as np

from viscocrowd.core.state import State
from viscocrowd.core.verifications import exiger_fini, exiger_scalaire_fini
from viscocrowd.geometry.obstacle import ObstacleRectangle
from viscocrowd.model.milieu import CarteZones, Milieu, ParametresMilieu, _zones_valides

# Vitesse de deplacement maximale locale F (M,), en m/s, aux points (M, 2). 0 : infranchissable.
ChampVitesse = Callable[[np.ndarray], np.ndarray]

# Vrai (M,) pour les points (M, 2) de la sortie, ou phi = 0.
ZoneSortie = Callable[[np.ndarray], np.ndarray]


@dataclass(frozen=True)
class GrilleReguliere:
    """Noeuds (x_min + i h, y_min + j h), 0 <= i < nx, 0 <= j < ny. Longueurs en m."""

    x_min: float
    y_min: float
    pas: float
    nx: int
    ny: int

    def __post_init__(self) -> None:
        exiger_scalaire_fini("x_min", self.x_min)
        exiger_scalaire_fini("y_min", self.y_min)
        exiger_scalaire_fini("le pas de la grille", self.pas, strictement_positif=True)
        for nom in ("nx", "ny"):
            valeur = getattr(self, nom)
            if not (isinstance(valeur, Integral) and not isinstance(valeur, bool) and valeur >= 2):
                raise ValueError(f"{nom} doit etre un entier >= 2, recu {valeur}")

    @classmethod
    def couvrant(
        cls, x_min: float, x_max: float, y_min: float, y_max: float, pas: float
    ) -> GrilleReguliere:
        """Plus petite grille de pas donne qui couvre le rectangle, coin bas-gauche inclus."""
        exiger_scalaire_fini("le pas de la grille", pas, strictement_positif=True)
        if not (x_max > x_min and y_max > y_min):
            raise ValueError("le rectangle a couvrir doit etre d'aire strictement positive")
        # La tolerance evite qu'une division a peine superieure a l'entier, comme
        # 12 / 0,05 = 240,00000000000003, n'ajoute une colonne de noeuds.
        nx = math.ceil((x_max - x_min) / pas - 1e-9) + 1
        ny = math.ceil((y_max - y_min) / pas - 1e-9) + 1
        return cls(float(x_min), float(y_min), float(pas), nx, ny)

    @property
    def forme(self) -> tuple[int, int]:
        return self.nx, self.ny

    def noeuds(self) -> np.ndarray:
        """Coordonnees des noeuds, de forme (nx, ny, 2), en m."""
        x = self.x_min + self.pas * np.arange(self.nx)
        y = self.y_min + self.pas * np.arange(self.ny)
        return np.stack(np.meshgrid(x, y, indexing="ij"), axis=-1)


def fast_marching(
    vitesse: np.ndarray,
    sortie: np.ndarray,
    pas: float,
    temps_initial: np.ndarray | None = None,
) -> np.ndarray:
    """Temps de parcours minimal phi jusqu'a la sortie, en s, aux noeuds d'une grille.

    Args:
        vitesse: F aux noeuds, de forme (nx, ny), en m/s. Finie et positive ou
            nulle ; 0 marque un noeud infranchissable.
        sortie: noeuds sources, booleens de forme (nx, ny). Au moins un, et
            aucun sur un noeud infranchissable.
        pas: h, distance entre deux noeuds voisins, en m.
        temps_initial: phi impose aux sources, (nx, ny), en s, fini et positif
            ou nul ; 0 par defaut. Il represente le temps qui reste APRES la
            source, par exemple franchir un rebord puis rejoindre la porte :
            phi devient alors le temps total jusqu'a la sortie finale, et chaque
            point choisit la source qui le minimise.

    Returns:
        phi, de forme (nx, ny), en s : temps impose sur les sources (sauf si une
        autre source fait mieux), +inf sur les noeuds infranchissables ou qu'aucun
        chemin ne relie a une source.

    Raises:
        ValueError: si une entree est mal formee, non finie ou incoherente.
    """
    F = np.asarray(vitesse, dtype=float)
    S = np.asarray(sortie)
    if F.ndim != 2 or min(F.shape) < 2:
        raise ValueError(f"vitesse doit etre de forme (nx, ny), nx et ny >= 2, recu {F.shape}")
    if S.shape != F.shape or S.dtype != bool:
        raise ValueError(f"sortie doit etre un tableau booleen de forme {F.shape}")
    if not np.all(np.isfinite(F)):
        raise ValueError("vitesse contient des valeurs non finies (NaN ou infini)")
    if np.any(F < 0.0):
        raise ValueError("vitesse doit etre positive ou nulle en chaque noeud")
    exiger_scalaire_fini("le pas de la grille", pas, strictement_positif=True)
    if not S.any():
        raise ValueError("aucun noeud de sortie : le temps de parcours n'est pas defini")
    if np.any(S & (F == 0.0)):
        raise ValueError("un noeud de sortie est infranchissable (vitesse nulle)")
    if temps_initial is None:
        T0 = np.zeros(F.shape)
    else:
        T0 = np.asarray(temps_initial, dtype=float)
        if T0.shape != F.shape:
            raise ValueError(f"temps_initial doit etre de forme {F.shape}, recu {T0.shape}")
        if not (np.all(np.isfinite(T0[S])) and np.all(T0[S] >= 0.0)):
            raise ValueError("temps_initial doit etre fini et positif ou nul sur les sources")

    nx, ny = F.shape
    # Listes Python plutot que tableaux : la boucle accede element par element, et
    # l'indexation d'un tableau NumPy y est plusieurs fois plus lente.
    with np.errstate(divide="ignore"):
        traversee = np.where(F > 0.0, pas / F, np.inf).ravel().tolist()
    phi = [math.inf] * (nx * ny)
    fixe = bytearray(nx * ny)

    def candidat(q: int) -> float:
        i, j = divmod(q, ny)
        a = b = math.inf
        if i > 0 and fixe[q - ny]:
            a = phi[q - ny]
        if i < nx - 1 and fixe[q + ny] and phi[q + ny] < a:
            a = phi[q + ny]
        if j > 0 and fixe[q - 1]:
            b = phi[q - 1]
        if j < ny - 1 and fixe[q + 1] and phi[q + 1] < b:
            b = phi[q + 1]
        if a > b:
            a, b = b, a
        f = traversee[q]
        if b - a >= f:
            return a + f
        return 0.5 * (a + b + math.sqrt(2.0 * f * f - (b - a) ** 2))

    depart = T0.ravel()
    tas = [(float(depart[p]), p) for p in np.flatnonzero(S.ravel()).tolist()]
    for valeur, p in tas:
        phi[p] = valeur
    heapq.heapify(tas)
    while tas:
        _, p = heapq.heappop(tas)
        if fixe[p]:
            continue  # entree perimee : le noeud a deja ete fixe avec une valeur plus petite
        fixe[p] = 1
        i, j = divmod(p, ny)
        for q, existe in (
            (p - ny, i > 0),
            (p + ny, i < nx - 1),
            (p - 1, j > 0),
            (p + 1, j < ny - 1),
        ):
            if existe and not fixe[q] and traversee[q] < math.inf:
                valeur = candidat(q)
                if valeur < phi[q]:
                    phi[q] = valeur
                    heapq.heappush(tas, (valeur, q))
    return np.array(phi).reshape(nx, ny)


def _gradient_amont(phi: np.ndarray, pas: float) -> np.ndarray:
    """Gradient de phi aux noeuds, (nx, ny, 2), par differences amont. Voir le module."""
    composantes = []
    for axe in (0, 1):
        avant = np.full_like(phi, np.inf)
        apres = np.full_like(phi, np.inf)
        if axe == 0:
            avant[1:, :], apres[:-1, :] = phi[:-1, :], phi[1:, :]
        else:
            avant[:, 1:], apres[:, :-1] = phi[:, :-1], phi[:, 1:]
        # Egalite, sur une crete : le voisin d'indice inferieur, par convention fixe.
        par_avant = avant <= apres
        voisin = np.where(par_avant, avant, apres)
        descend = np.isfinite(phi) & (voisin < phi)
        with np.errstate(invalid="ignore"):
            pente = np.where(par_avant, phi - avant, apres - phi) / pas
        composantes.append(np.where(descend, pente, 0.0))
    return np.stack(composantes, axis=-1)


class ChampEikonal:
    """Temps de parcours phi et direction de guidage, a passer a `pas_libre_milieux`.

    Le champ est calcule une fois, a la construction, pour un domaine et une
    sortie fixes. L'objet est ensuite appelable comme `direction(etat)`.

    Attributes:
        grille: la grille de calcul.
        phi: temps de parcours aux noeuds, (nx, ny), en s, en lecture seule.
    """

    def __init__(
        self,
        grille: GrilleReguliere,
        vitesse: ChampVitesse,
        sortie: ZoneSortie,
        temps_sortie: Callable[[np.ndarray], np.ndarray] | None = None,
    ) -> None:
        """
        Args:
            grille: noeuds de calcul. Elle doit couvrir le domaine parcouru : un
                agent hors de la grille recoit la direction du bord le plus proche.
            vitesse: F aux points (M, 2), en m/s ; 0 hors des zones praticables.
            sortie: vrai aux points (M, 2) de la sortie.
            temps_sortie: temps restant (M,), en s, aux points de la sortie ; 0
                par defaut. Voir `fast_marching`.
        """
        points = grille.noeuds().reshape(-1, 2)
        F = np.asarray(vitesse(points), dtype=float)
        S = np.asarray(sortie(points))
        if F.shape != (points.shape[0],) or S.shape != (points.shape[0],):
            raise ValueError("vitesse et sortie doivent rendre une valeur par point")
        T0 = None
        if temps_sortie is not None:
            T0 = np.zeros(points.shape[0])
            T0[S] = np.asarray(temps_sortie(points[S]), dtype=float)
            T0 = T0.reshape(grille.forme)
        self._initialiser(grille, F.reshape(grille.forme), S.reshape(grille.forme), T0)

    def _initialiser(self, grille, F, S, T0) -> None:
        for nom, tableau in (("vitesse", F), ("sortie", S), ("temps_initial", T0)):
            if tableau is not None and np.shape(tableau) != grille.forme:
                raise ValueError(f"{nom} doit avoir la forme de la grille {grille.forme}")
        self.grille = grille
        self.phi = fast_marching(F, S, grille.pas, T0)
        self.phi.flags.writeable = False
        self._gradient = _gradient_amont(self.phi, grille.pas)

    @classmethod
    def depuis_tableaux(
        cls,
        grille: GrilleReguliere,
        vitesse: np.ndarray,
        sortie: np.ndarray,
        temps_initial: np.ndarray | None = None,
    ) -> ChampEikonal:
        """Champ calcule a partir de F, des sources et de leurs temps, deja aux noeuds (nx, ny)."""
        champ = cls.__new__(cls)
        champ._initialiser(grille, vitesse, sortie, temps_initial)
        return champ

    def direction(self, x: np.ndarray) -> np.ndarray:
        """Direction de guidage (N, 2) aux positions x (N, 2) : unitaire, ou nulle."""
        x = np.asarray(x, dtype=float)
        if x.ndim != 2 or x.shape[1] != 2:
            raise ValueError(f"x doit etre de forme (N, 2), recu {x.shape}")
        exiger_fini("Positions transmises au guidage.", x=x)
        g = self.grille
        u = (x[:, 0] - g.x_min) / g.pas
        w = (x[:, 1] - g.y_min) / g.pas
        i = np.clip(np.floor(u), 0, g.nx - 2).astype(np.int64)
        j = np.clip(np.floor(w), 0, g.ny - 2).astype(np.int64)
        tu = np.clip(u - i, 0.0, 1.0)[:, None]
        tw = np.clip(w - j, 0.0, 1.0)[:, None]
        G = self._gradient
        voisins = np.stack((G[i, j], G[i + 1, j], G[i, j + 1], G[i + 1, j + 1]), axis=1)
        poids = np.concatenate(((1 - tu) * (1 - tw), tu * (1 - tw), (1 - tu) * tw, tu * tw), axis=1)
        gradient = np.sum(poids[..., None] * voisins, axis=1)

        # Aux cretes, ne pas moyenner deux chemins opposes : cela creait un
        # equilibre artificiel entre les noeuds, malgre le departage amont.
        normes_voisines = np.hypot(voisins[..., 0], voisins[..., 1])
        actifs = (poids > 0.0) & (normes_voisines > 0.0)
        unitaires = voisins / np.where(normes_voisines > 0.0, normes_voisines, 1.0)[..., None]
        produits = np.einsum("nki,nli->nkl", unitaires, unitaires)
        opposees = np.any(
            (produits < -1e-12) & actifs[:, :, None] & actifs[:, None, :], axis=(1, 2)
        )
        if np.any(opposees):
            temps = np.stack(
                (self.phi[i, j], self.phi[i + 1, j], self.phi[i, j + 1], self.phi[i + 1, j + 1]),
                axis=1,
            )
            choix = np.argmin(np.where(actifs, temps, np.inf), axis=1)
            gradient[opposees] = voisins[np.flatnonzero(opposees), choix[opposees]]
        norme = np.hypot(gradient[:, 0], gradient[:, 1])
        return np.where(
            (norme > 0.0)[:, None], -gradient / np.where(norme > 0.0, norme, 1.0)[:, None], 0.0
        )

    def temps(self, x: np.ndarray) -> np.ndarray:
        """phi (N,), en s, interpole bilineairement aux positions x (N, 2).

        Seuls les noeuds de phi fini comptent, poids renormalises : pres d'un
        obstacle, le temps n'est pas tire vers l'infini. +inf si aucun des quatre
        noeuds n'est atteignable.
        """
        x = np.asarray(x, dtype=float)
        if x.ndim != 2 or x.shape[1] != 2:
            raise ValueError(f"x doit etre de forme (N, 2), recu {x.shape}")
        exiger_fini("Positions transmises au champ.", x=x)
        g = self.grille
        u = (x[:, 0] - g.x_min) / g.pas
        w = (x[:, 1] - g.y_min) / g.pas
        i = np.clip(np.floor(u), 0, g.nx - 2).astype(np.int64)
        j = np.clip(np.floor(w), 0, g.ny - 2).astype(np.int64)
        tu = np.clip(u - i, 0.0, 1.0)
        tw = np.clip(w - j, 0.0, 1.0)
        valeurs = np.stack(
            (self.phi[i, j], self.phi[i + 1, j], self.phi[i, j + 1], self.phi[i + 1, j + 1]), axis=1
        )
        poids = np.stack(((1 - tu) * (1 - tw), tu * (1 - tw), (1 - tu) * tw, tu * tw), axis=1)
        poids = np.where(np.isfinite(valeurs), poids, 0.0)
        total = poids.sum(axis=1)
        somme = np.sum(poids * np.where(np.isfinite(valeurs), valeurs, 0.0), axis=1)
        with np.errstate(invalid="ignore", divide="ignore"):
            return np.where(total > 0.0, somme / total, np.inf)

    def __call__(self, etat: State) -> np.ndarray:
        return self.direction(etat.x)


def vitesse_des_milieux(
    zone: CarteZones,
    parametres: Mapping[Milieu, ParametresMilieu],
    obstacles: Iterable[ObstacleRectangle] = (),
    marge: float = 0.0,
) -> ChampVitesse:
    """F(x) = vitesse souhaitee du milieu sous x, nulle pres des obstacles (spec § 2.6).

    Args:
        zone: milieu sous chaque point, comme pour `pas_libre_milieux`.
        parametres: parametres des milieux ; seule la vitesse s sert ici.
        obstacles: rectangles infranchissables.
        marge: distance, en m, en deca de laquelle un point est retire autour des
            obstacles. Le rayon des agents : le champ guide alors leur CENTRE, et
            le disque ne touche pas l'obstacle.
    """
    exiger_scalaire_fini("marge", marge)
    if not marge >= 0.0:
        raise ValueError(f"marge doit etre positive ou nulle, recu {marge}")
    obstacles = tuple(obstacles)
    taille = max(Milieu) + 1
    s = np.full(taille, np.nan)
    declare = np.zeros(taille, dtype=bool)
    for milieu, p in parametres.items():
        s[Milieu(milieu)] = p.vitesse
        declare[Milieu(milieu)] = True
    if not declare.any():
        raise ValueError("il faut les parametres d'au moins un milieu")

    def _vitesse(points: np.ndarray) -> np.ndarray:
        F = s[_zones_valides(zone(points), points.shape[0], declare)]
        for obstacle in obstacles:
            F[obstacle.distance(points) <= marge] = 0.0
        return F

    return _vitesse
