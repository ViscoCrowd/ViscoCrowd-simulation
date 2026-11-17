"""Navigation locale par heuristiques visuelles (Moussaid, Helbing et Theraulaz, 2011) (#158).

Le guidage eikonal donne a tous le meme plus court chemin : sur la plage, il longe le
bord du bassin a un rayon pres, et comme rien n'ecarte un agent de cette ligne, les
baigneurs marchaient en file indienne contre le bord, puis en deux lignes vers la porte
(90 % des positions a moins de 21 cm du bord, mesure du 17 novembre, #158). Un pieton
reel regarde devant lui et choisit un chemin libre.

Ce module reprend les deux heuristiques de Moussaid et al. (2011, PNAS 108(17),
p. 6884-6888), verifiees sur l'original :

1. Direction. Dans son champ de vision, de -phi a +phi autour de sa ligne de visee, le
   pieton choisit la direction alpha qui minimise la distance a sa destination,

       d(alpha)^2 = d_max^2 + f(alpha)^2 - 2 d_max f(alpha) cos(alpha_0 - alpha),

   ou alpha_0 est la direction de la destination et f(alpha) la distance a la premiere
   collision s'il marchait dans la direction alpha a sa vitesse souhaitee v0, compte
   tenu de la vitesse et de la taille des autres, plafonnee a l'horizon d_max.
2. Vitesse. v_des = min(v0, d_h / tau), ou d_h est la distance au premier obstacle
   dans la direction choisie, a l'instant t.

La vitesse relaxe ensuite vers v_des e_des comme partout (`model.milieu`, temps tau et
borne d'adherence a_max du sol). Les valeurs par defaut sont celles de l'article :
tau = 0,5 s, phi = 75 deg et d_max = 10 m (fig. 2), v0 tire selon une loi normale de
moyenne 1,3 m/s et d'ecart-type 0,2 m/s (fig. 3), soit un coefficient de variation de
0,15.

Adaptations, et pourquoi
------------------------

- La destination n'est pas un point : c'est la porte, derriere le coin du bassin.
  alpha_0 est donc la direction du champ eikonal (`model.guidage_piscine`), celle du
  plus court chemin. C'est elle que l'heuristique corrige localement.
- Les forces de contact de l'article (k g(r_i + r_j - d_ij)) sont remplacees par la
  projection du moteur, comme partout dans ce projet : l'exclusion reste dure.
- Les heuristiques ne s'appliquent qu'aux agents sur la plage. Nager n'est pas marcher,
  et les nageurs restent guides par le champ de l'eau. Les obstacles vus sur la plage
  sont les murs, le bassin, les montants de la porte, les obstacles fixes et les autres
  agents de la plage.
- Un rectangle est vu gonfle du rayon de l'agent, a coins vifs : un peu prudent aux
  angles, ce qui ne change pas le choix de direction a la resolution angulaire utilisee.
- La vitesse souhaitee de chaque agent est la vitesse du sol multipliee par un facteur
  individuel tire une fois (`facteurs_individuels`) : les sols et le facteur de panique
  gardent leur sens, et la dispersion relative est celle de l'article.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

from viscocrowd.core.rng import generateur
from viscocrowd.core.verifications import exiger_scalaire_fini
from viscocrowd.geometry.grille import paires_candidates
from viscocrowd.geometry.obstacle import ObstacleRectangle

# Les positions initiales lisent le flux principal, les chutes le flux 1.
FLUX_NAVIGATION = 2

# En dessous de cette fraction de v0, la ligne de visee est la direction de la
# destination : un agent a l'arret (reintroduit sur la plage) n'a pas de cap.
_CAP_MINIMAL = 0.1

# Marge (m) retiree au rayon face aux murs et aux obstacles. La projection tolere un
# recouvrement de 1e-6 m : un agent pose contre le bassin est alors DANS le rectangle
# gonfle de son rayon, et toutes ses directions donnaient une distance libre nulle. Le
# premier essai s'arretait ainsi contre le bord, sans jamais atteindre la porte.
_MARGE_PAROI = 1e-3


@dataclass(frozen=True)
class ParametresNavigation:
    """Parametres des heuristiques, valeurs par defaut de Moussaid et al. (2011).

    Attributes:
        champ_vision: demi-angle phi du champ de vision, en degres (75, fig. 2).
        horizon: distance d_max au-dela de laquelle rien n'est vu, en m (10, fig. 2).
        directions: nombre de directions examinees dans le champ, impair pour que la
            ligne de visee en fasse partie.
        dispersion_vitesse: coefficient de variation de la vitesse souhaitee entre
            agents (0,2 / 1,3, fig. 3) ; 0 rend tous les agents identiques.
        temps_anticipation: tau de la seconde heuristique, en s ; None prend le temps
            de relaxation du sol, comme l'article, qui utilise le meme tau.
    """

    champ_vision: float = 75.0
    horizon: float = 10.0
    directions: int = 31
    dispersion_vitesse: float = 0.15
    temps_anticipation: float | None = None

    def __post_init__(self) -> None:
        exiger_scalaire_fini("champ_vision", self.champ_vision, strictement_positif=True)
        if self.champ_vision > 180.0:
            raise ValueError("champ_vision est un demi-angle : au plus 180 degres")
        exiger_scalaire_fini("horizon", self.horizon, strictement_positif=True)
        if type(self.directions) is not int or self.directions < 3 or self.directions % 2 == 0:
            raise ValueError("directions doit etre un entier impair d'au moins 3")
        exiger_scalaire_fini("dispersion_vitesse", self.dispersion_vitesse)
        if not 0.0 <= self.dispersion_vitesse < 0.5:
            raise ValueError("dispersion_vitesse doit etre dans [0 ; 0,5[")
        if self.temps_anticipation is not None:
            exiger_scalaire_fini(
                "temps_anticipation", self.temps_anticipation, strictement_positif=True
            )

    @property
    def facteur_maximal(self) -> float:
        """Plus grand facteur individuel de vitesse que `facteurs_individuels` peut rendre."""
        return 1.0 + 3.0 * self.dispersion_vitesse


def facteurs_individuels(n: int, parametres: ParametresNavigation, graine: int) -> np.ndarray:
    """Facteur (n,) de vitesse souhaitee de chaque agent, tire une fois pour toutes.

    Loi normale de moyenne 1 et d'ecart-type `dispersion_vitesse`, tronquee a trois
    ecarts-types : sans troncature, un tirage rare donnerait une vitesse negative ou
    depasserait le deplacement par pas que le scenario autorise. Les tirages ont leur
    propre flux : activer la navigation ne change pas les positions initiales.
    """
    sigma = parametres.dispersion_vitesse
    if sigma == 0.0:
        return np.ones(n)
    tirage = generateur(graine, flux=FLUX_NAVIGATION).normal(1.0, sigma, n)
    return np.clip(tirage, 1.0 - 3.0 * sigma, 1.0 + 3.0 * sigma)


def _distance_boite_pleine(
    px: np.ndarray,
    py: np.ndarray,
    e: np.ndarray,
    bornes: tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray],
) -> np.ndarray:
    """Distance (N, K) avant d'entrer dans la boite pleine [x0, x1] x [y0, y1].

    Methode des tranches. Un point deja dedans donne 0 ; une boite derriere le point ou
    hors du rayon, inf. Les bornes peuvent dependre de l'agent (rayon), de forme (N, 1).
    """
    x0, x1, y0, y1 = bornes
    with np.errstate(divide="ignore", invalid="ignore"):
        inv_x, inv_y = 1.0 / e[..., 0], 1.0 / e[..., 1]
        t1, t2 = (x0 - px) * inv_x, (x1 - px) * inv_x
        t3, t4 = (y0 - py) * inv_y, (y1 - py) * inv_y
    # Direction parallele a une tranche : dedans (toujours) ou dehors (jamais).
    dedans_x = (px > x0) & (px < x1)
    dedans_y = (py > y0) & (py < y1)
    nul_x, nul_y = e[..., 0] == 0.0, e[..., 1] == 0.0
    tx_min = np.where(nul_x, np.where(dedans_x, -np.inf, np.inf), np.minimum(t1, t2))
    tx_max = np.where(nul_x, np.where(dedans_x, np.inf, -np.inf), np.maximum(t1, t2))
    ty_min = np.where(nul_y, np.where(dedans_y, -np.inf, np.inf), np.minimum(t3, t4))
    ty_max = np.where(nul_y, np.where(dedans_y, np.inf, -np.inf), np.maximum(t3, t4))
    entree = np.maximum(tx_min, ty_min)
    sortie = np.minimum(tx_max, ty_max)
    touche = (entree <= sortie) & (sortie >= 0.0)
    return np.where(touche, np.maximum(entree, 0.0), np.inf)


def _distance_disque(
    px: np.ndarray, py: np.ndarray, e: np.ndarray, cx: float, cy: float, rr: np.ndarray
) -> np.ndarray:
    """Distance (N, K) avant que le point n'entre dans le disque de centre c et de rayon rr.

    Un point deja dedans ne compte que s'il s'enfonce : il peut toujours s'eloigner.
    """
    ox, oy = px - cx, py - cy
    b = ox * e[..., 0] + oy * e[..., 1]  # (N, K)
    c = ox**2 + oy**2 - rr**2  # (N, 1)
    delta = b**2 - c
    t = -b - np.sqrt(np.maximum(delta, 0.0))
    dedans = c <= 0.0
    return np.where(
        dedans,
        np.where(b < 0.0, 0.0, np.inf),
        np.where((delta >= 0.0) & (t >= 0.0), t, np.inf),
    )


def _distance_rectangles(
    x: np.ndarray, r: np.ndarray, e: np.ndarray, rectangles: Sequence[ObstacleRectangle]
) -> np.ndarray:
    """Distance (N, K) le long de chaque direction avant de toucher un rectangle.

    Un disque de rayon r touche le rectangle quand son centre entre dans le rectangle
    gonfle de r, aux coins ARRONDIS : deux bandes (gonflees en x seulement, puis en y
    seulement) et quatre disques de rayon r aux sommets. C'est la geometrie de la
    projection (`ObstacleRectangle.repousser`) : une premiere version a coins vifs
    figeait les baigneurs qui glissaient le long du coin arrondi d'un montant, et la
    porte se bouchait.
    """
    d = np.full(e.shape[:2], np.inf)
    px, py = x[:, None, 0], x[:, None, 1]
    rr = r[:, None]
    for rect in rectangles:
        bandes = (
            (rect.x_min - rr, rect.x_max + rr, rect.y_min + 0.0 * rr, rect.y_max + 0.0 * rr),
            (rect.x_min + 0.0 * rr, rect.x_max + 0.0 * rr, rect.y_min - rr, rect.y_max + rr),
        )
        for bornes in bandes:
            d = np.minimum(d, _distance_boite_pleine(px, py, e, bornes))
        for cx in (rect.x_min, rect.x_max):
            for cy in (rect.y_min, rect.y_max):
                d = np.minimum(d, _distance_disque(px, py, e, cx, cy, rr))
    return d


def _distance_boite(
    x: np.ndarray, r: np.ndarray, e: np.ndarray, boite: tuple[float, float, float, float]
) -> np.ndarray:
    """Distance (N, K) avant que le disque ne sorte de la boite [x0, x1] x [y0, y1]."""
    x0, x1, y0, y1 = boite
    px, py, rr = x[:, None, 0], x[:, None, 1], r[:, None]
    d = np.full(e.shape[:2], np.inf)
    with np.errstate(divide="ignore", invalid="ignore"):
        for borne, coord, comp, signe in (
            (x0 + rr, px, e[..., 0], -1.0),
            (x1 - rr, px, e[..., 0], 1.0),
            (y0 + rr, py, e[..., 1], -1.0),
            (y1 - rr, py, e[..., 1], 1.0),
        ):
            vers_le_mur = signe * comp > 0.0
            t = (borne - coord) / comp
            d = np.where(vers_le_mur, np.minimum(d, np.maximum(t, 0.0)), d)
    return d


def _collisions_pietons(
    x: np.ndarray,
    v: np.ndarray,
    r: np.ndarray,
    v0: np.ndarray,
    e: np.ndarray,
    portee: float,
    *,
    figes: bool,
) -> np.ndarray:
    """Distance (N, K) parcourue par i avant de toucher un autre agent, inf sinon.

    i marche a v0_i dans la direction e[i, k] ; j garde sa vitesse actuelle, ou reste
    immobile si `figes` (seconde heuristique : le premier obstacle a l'instant t). Deux
    disques deja en contact qui se rapprochent donnent 0.
    """
    n, k = e.shape[:2]
    d = np.full((n, k), np.inf)
    paires = paires_candidates(x, r, marge=portee)
    if paires.size == 0:
        return d
    i = np.concatenate((paires[:, 0], paires[:, 1]))
    j = np.concatenate((paires[:, 1], paires[:, 0]))
    p = (x[j] - x[i])[:, None, :]  # (P, 1, 2)
    vj = np.zeros_like(p) if figes else v[j][:, None, :]
    w = vj - v0[i][:, None, None] * e[i]  # (P, K, 2), vitesse relative de j vu de i
    somme = (r[i] + r[j])[:, None]
    pp = np.sum(p * p, axis=-1)  # (P, 1)
    pw = np.sum(p * w, axis=-1)  # (P, K)
    ww = np.sum(w * w, axis=-1)
    c = pp - somme**2
    delta = pw**2 - ww * c
    with np.errstate(divide="ignore", invalid="ignore"):
        t = np.where(c <= 0.0, 0.0, (-pw - np.sqrt(np.maximum(delta, 0.0))) / ww)
    rapproche = pw < 0.0
    collision = rapproche & ((c <= 0.0) | (delta >= 0.0)) & (ww > 0.0)
    distance = np.where(collision, v0[i][:, None] * np.maximum(t, 0.0), np.inf)
    np.minimum.at(d, i, distance)
    return d


@dataclass(frozen=True)
class ScenePlage:
    """Ce qu'un baigneur voit sur la plage : une boite et des rectangles.

    Attributes:
        boite: [x0, x1] x [y0, y1] ou les centres restent, en m ; x1 est pris au-dela
            du couloir de la porte, que seuls les montants bornent.
        rectangles: bassin, montants de la porte et obstacles fixes.
    """

    boite: tuple[float, float, float, float]
    rectangles: tuple[ObstacleRectangle, ...]


def vitesses_souhaitees(
    x: np.ndarray,
    v: np.ndarray,
    r: np.ndarray,
    v0: np.ndarray,
    e0: np.ndarray,
    tau: np.ndarray,
    scene: ScenePlage,
    parametres: ParametresNavigation,
) -> np.ndarray:
    """Vitesse souhaitee (N, 2) de chaque agent selon les deux heuristiques.

    Args:
        x, v, r: positions (N, 2), vitesses (N, 2) et rayons (N,) des agents de la plage.
        v0: vitesse souhaitee de chacun (N,), en m/s, facteur individuel compris.
        e0: direction unitaire de la destination (N, 2), celle du champ eikonal ; un
            agent sans direction (vecteur nul) reste sans vitesse souhaitee.
        tau: temps de relaxation du sol sous chacun (N,), en s ; sert a la seconde
            heuristique si `temps_anticipation` n'est pas fixe.
        scene: murs et obstacles de la plage.
        parametres: champ de vision, horizon, resolution, temps d'anticipation.
    """
    n = x.shape[0]
    u = np.zeros((n, 2))
    if n == 0:
        return u
    d_max = parametres.horizon
    a0 = np.arctan2(e0[:, 1], e0[:, 0])
    vitesse = np.hypot(v[:, 0], v[:, 1])
    cap = np.where(vitesse > _CAP_MINIMAL * np.maximum(v0, 1e-12), np.arctan2(v[:, 1], v[:, 0]), a0)
    demi = np.deg2rad(parametres.champ_vision)
    angles = cap[:, None] + np.linspace(-demi, demi, parametres.directions)[None, :]
    e = np.stack((np.cos(angles), np.sin(angles)), axis=-1)  # (N, K, 2)

    # Premiere heuristique : f(alpha), puis la direction qui rapproche le plus.
    r_paroi = np.maximum(r - _MARGE_PAROI, 0.0)
    statique = np.minimum(
        _distance_boite(x, r_paroi, e, scene.boite),
        _distance_rectangles(x, r_paroi, e, scene.rectangles),
    )
    f = np.minimum(statique, _collisions_pietons(x, v, r, v0, e, d_max, figes=False))
    f = np.minimum(f, d_max)
    d2 = d_max**2 + f**2 - 2.0 * d_max * f * np.cos(a0[:, None] - angles)
    choix = np.argmin(d2, axis=1)
    rang = np.arange(n)
    e_des = e[rang, choix]

    # Seconde heuristique : distance au premier obstacle dans cette direction, a l'instant t.
    e_choisie = e_des[:, None, :]
    d_h = np.minimum(
        statique[rang, choix],
        _collisions_pietons(x, v, r, v0, e_choisie, d_max, figes=True)[:, 0],
    )
    d_h = np.minimum(d_h, d_max)
    tau_h = tau if parametres.temps_anticipation is None else parametres.temps_anticipation
    v_des = np.minimum(v0, d_h / tau_h)
    sans_but = np.hypot(e0[:, 0], e0[:, 1]) == 0.0
    v_des = np.where(sans_but, 0.0, v_des)
    u = v_des[:, None] * e_des
    return u
