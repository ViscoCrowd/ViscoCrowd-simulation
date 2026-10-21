"""Etalonnage E0 : debit d'un goulot sec, sur le protocole de Seyfried et al. (2009).

Les experiences de Seyfried et al. (2009, tableau 2) mesurent le debit specifique
J_s = Delta N / (Delta t * b) d'une foule de 20 a 60 personnes, partie d'une zone
d'attente a 3,3 pers/m^2 dont le centre est a 3 m de l'entree d'un goulot de
2,8 m de long et de largeur b = 0,8 a 1,2 m. Le passage est compte a 0,4 m apres
l'entree du goulot. Mesures : J_s de 1,61 a 2,31 pers/(m.s) selon b et N.

Ce banc reproduit ce protocole pour comparer notre modele a une mesure connue, en
sol sec seul, avant toute campagne piscine (spec § 4, E0). Il n'ajuste rien : il
mesure. Le choix d'un eventuel reglage (rayon, vitesse) releve du groupe.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from viscocrowd.core.integrator import pas_semi_implicite
from viscocrowd.core.rng import generateur
from viscocrowd.core.state import State
from viscocrowd.geometry.projection import ProjectionExclusion
from viscocrowd.geometry.salle import SalleGoulot
from viscocrowd.model.eikonal import ChampEikonal, GrilleReguliere
from viscocrowd.model.milieu import Milieu, ParametresMilieu, pas_libre_milieux
from viscocrowd.observables.debit import franchissements


@dataclass(frozen=True)
class ParametresGoulot:
    """Tous les choix du banc, explicites dans le YAML, en unites SI."""

    longueur: float  # salle, m
    largeur: float  # salle, m
    largeur_goulot: float  # b, m
    longueur_goulot: float  # m
    n_agents: int
    rayon: float  # m
    densite_initiale: float  # pers/m^2 dans la zone d'attente
    distance_attente: float  # m, du centre de la zone d'attente a l'entree du goulot
    largeur_attente: float  # m
    bruit: float  # m, perturbation du reseau initial
    sec: dict  # relaxation, acceleration_max, vitesse
    facteur_vitesse: float
    dispersion_rayon: float  # rayons uniformes dans [r (1 - d), r (1 + d)]
    bruit_direction: float  # rad, ecart-type stationnaire de l'angle de la direction
    correlation_bruit: float  # s, temps de correlation de ce bruit
    position_mesure: float  # m apres l'entree du goulot
    dt: float
    duree: float
    tolerance: float
    pas_guidage: float
    graine: int

    def __post_init__(self) -> None:
        if type(self.n_agents) is not int or self.n_agents < 2:
            raise ValueError("n_agents doit etre un entier >= 2")
        if type(self.graine) is not int or self.graine < 0:
            raise ValueError("graine doit etre un entier positif ou nul")
        for nom in (
            "longueur",
            "largeur",
            "largeur_goulot",
            "longueur_goulot",
            "rayon",
            "densite_initiale",
            "distance_attente",
            "largeur_attente",
            "bruit",
            "facteur_vitesse",
            "dispersion_rayon",
            "bruit_direction",
            "correlation_bruit",
            "position_mesure",
            "dt",
            "duree",
            "tolerance",
            "pas_guidage",
        ):
            valeur = getattr(self, nom)
            if type(valeur) not in (int, float) or not np.isfinite(valeur):
                raise ValueError(f"{nom} doit etre un nombre reel fini")
            peut_etre_nul = nom in ("bruit", "dispersion_rayon", "bruit_direction")
            if valeur < 0 or (not peut_etre_nul and valeur == 0):
                raise ValueError(f"{nom} hors domaine")
        if self.dispersion_rayon >= 1.0:
            raise ValueError("dispersion_rayon doit etre inferieure a 1")
        sec = self.sec if isinstance(self.sec, ParametresMilieu) else ParametresMilieu(**self.sec)
        object.__setattr__(self, "sec", sec)
        SalleGoulot(self.longueur, self.largeur, self.largeur_goulot, self.longueur_goulot)
        if 2 * self.rayon_max >= self.largeur_goulot:
            raise ValueError("un agent doit pouvoir passer le goulot")
        if self.position_mesure >= self.longueur_goulot:
            raise ValueError("la ligne de mesure doit etre dans le goulot")
        rayon_min = self.rayon * (1 - self.dispersion_rayon)
        if self.dt > sec.relaxation or self.dt * self.facteur_vitesse * sec.vitesse > rayon_min / 5:
            raise ValueError("dt trop grand : dt <= tau et deplacement par pas <= rayon/5")
        if self.pas_guidage > rayon_min:
            raise ValueError("pas_guidage doit etre inferieur ou egal au plus petit rayon")
        a = self.pas_reseau
        if a - 2 * self.bruit < 2 * self.rayon_max:
            raise ValueError(
                "densite initiale trop forte pour ce rayon : les disques se recouvrent"
            )
        _reseau_attente(self)  # controle la place disponible dans la salle

    @property
    def rayon_max(self) -> float:
        return self.rayon * (1 + self.dispersion_rayon)

    @property
    def pas_reseau(self) -> float:
        """Pas du reseau hexagonal de densite `densite_initiale`, en m."""
        return float(np.sqrt(2.0 / (np.sqrt(3.0) * self.densite_initiale)))

    @property
    def geometrie(self) -> SalleGoulot:
        return SalleGoulot(self.longueur, self.largeur, self.largeur_goulot, self.longueur_goulot)


def _reseau_attente(p: ParametresGoulot) -> np.ndarray:
    """Les N noeuds d'un reseau hexagonal les plus proches du centre de la zone d'attente.

    Le reseau couvre la largeur de la zone ; on garde les N noeuds de plus petit ecart
    en x au centre. La zone a ainsi la densite voulue et son centre a la distance
    voulue du goulot, quel que soit N, sans arrondi de profondeur a gerer.
    """
    a = p.pas_reseau
    h = a * np.sqrt(3) / 2
    centre_x = p.longueur - p.distance_attente
    y_min = p.largeur / 2 - p.largeur_attente / 2
    y_max = p.largeur / 2 + p.largeur_attente / 2
    lignes = np.arange(y_min + h / 2, y_max, h)
    if lignes.size == 0:
        raise ValueError("la zone d'attente est plus etroite qu'une rangee")
    demi = p.n_agents / lignes.size / 2 * a + a
    points = [
        [x, y]
        for k, y in enumerate(lignes)
        for x in np.arange(centre_x - demi + (a / 2 if k % 2 else 0.0), centre_x + demi, a)
    ]
    points = np.array(points)
    garde = np.argsort(np.abs(points[:, 0] - centre_x), kind="stable")[: p.n_agents]
    points = points[garde]
    marge = p.rayon_max + p.bruit
    bas, haut = points.min(axis=0), points.max(axis=0)
    if np.any(bas < marge) or np.any(haut > np.array([p.longueur, p.largeur]) - marge):
        raise ValueError("la zone d'attente doit tenir dans la salle")
    return points


def tirages_initiaux(p: ParametresGoulot) -> tuple[np.ndarray, np.ndarray, np.random.Generator]:
    """Positions (N, 2) et rayons (N,) initiaux, et le generateur qui produira le bruit.

    Un seul generateur, initialise par la graine, sert a tout dans l'ordre : positions,
    rayons, puis bruit de direction pas apres pas. Aucun alea n'echappe a la graine.
    """
    rng = generateur(p.graine)
    x = _reseau_attente(p)
    x = x + rng.uniform(-p.bruit, p.bruit, size=x.shape)
    r = p.rayon * (1 + rng.uniform(-p.dispersion_rayon, p.dispersion_rayon, size=p.n_agents))
    return x, r, rng


@dataclass(frozen=True)
class ResultatGoulot:
    t: np.ndarray
    x: np.ndarray
    rayons: np.ndarray
    passages: np.ndarray  # (N,) instant de passage de la ligne de mesure, NaN sinon
    debit_specifique: float  # pers/(m.s), fenetre centrale de 80 % des passages
    projection: ProjectionExclusion
    parametres: ParametresGoulot

    def violation_paroi_max(self) -> float:
        g = self.parametres.geometrie
        return max(g.violation(x, self.rayons, t) for x, t in zip(self.x, self.t, strict=True))


def simuler_goulot(p: ParametresGoulot) -> ResultatGoulot:
    """Simule le banc jusqu'a ce que tous aient quitte le goulot ou jusqu'a `duree`."""
    g = p.geometrie
    sortie_x = g.longueur + g.longueur_goulot
    grille = GrilleReguliere.couvrant(0.0, sortie_x, 0.0, g.largeur, p.pas_guidage)
    noeuds = grille.noeuds().reshape(-1, 2)
    libre = g.admissible(noeuds, p.rayon)
    F = np.where(libre, p.facteur_vitesse * p.sec.vitesse, 0.0)
    champ = ChampEikonal.depuis_tableaux(
        grille,
        F.reshape(grille.forme),
        (libre & (noeuds[:, 0] >= sortie_x - 1e-9)).reshape(grille.forme),
    )

    x, r, rng = tirages_initiaux(p)
    # Angle de fluctuation de chaque agent : processus d'Ornstein-Uhlenbeck d'ecart-type
    # stationnaire `bruit_direction` et de temps de correlation `correlation_bruit`, donc
    # independant du pas de temps (Helbing et al. 2000 : fluctuations individuelles).
    angle = rng.normal(0.0, p.bruit_direction, size=p.n_agents) if p.bruit_direction else None
    memoire = np.exp(-p.dt / p.correlation_bruit)
    actif = np.ones(p.n_agents, dtype=bool)

    def direction(etat: State) -> np.ndarray:
        e = champ(etat)
        # Au bout du goulot, le champ s'annule : on continue tout droit vers la sortie.
        bout = np.all(e == 0.0, axis=1) & (etat.x[:, 0] >= g.longueur)
        e[bout] = [1.0, 0.0]
        if angle is not None:
            a = angle[actif]
            c, s = np.cos(a), np.sin(a)
            e = np.column_stack((c * e[:, 0] - s * e[:, 1], s * e[:, 0] + c * e[:, 1]))
        return e

    def partout(points: np.ndarray) -> np.ndarray:
        return np.full(points.shape[0], Milieu.SEC, dtype=np.int64)

    libre_pas = pas_libre_milieux(
        direction, partout, {Milieu.SEC: p.sec}, facteur_vitesse=p.facteur_vitesse
    )
    projection = ProjectionExclusion(g.projeter, tolerance=p.tolerance, strict=True)

    v = np.zeros_like(x)
    historique_t, historique_x = [0.0], [x.copy()]
    for pas in range(1, int(np.ceil(p.duree / p.dt)) + 1):
        if angle is not None:
            angle = memoire * angle + p.bruit_direction * np.sqrt(1 - memoire**2) * rng.normal(
                size=p.n_agents
            )
        a = np.flatnonzero(actif)
        nouveau = pas_semi_implicite(
            State(x=x[a], v=v[a], r=r[a], t=(pas - 1) * p.dt), p.dt, libre_pas, projection
        )
        x[a], v[a] = nouveau.x, nouveau.v
        # Sortie absorbante au bout du goulot : on ne gene plus personne.
        sortis = actif & (x[:, 0] >= sortie_x)
        actif[sortis] = False
        v[sortis] = 0.0
        historique_t.append(pas * p.dt)
        historique_x.append(x.copy())
        if not actif.any():
            break

    t, trajectoire = np.array(historique_t), np.stack(historique_x)
    ligne = franchissements(t, trajectoire, *g.entree(p.position_mesure))
    passages = np.full(p.n_agents, np.nan)
    for agent, instant, sens in zip(ligne.agent, ligne.instant, ligne.sens, strict=True):
        if sens > 0 and np.isnan(passages[agent]):
            passages[agent] = instant
    return ResultatGoulot(
        t, trajectoire, r, passages, debit_central(passages, g.largeur_goulot), projection, p
    )


def debit_central(passages: np.ndarray, largeur: float, fraction: float = 0.8) -> float:
    """Debit specifique (pers/(m.s)) sur la fenetre centrale des passages.

    Les premiers et derniers passages, avant que la file ne se forme et quand elle se
    vide, ne sont pas stationnaires. On garde les passages entre les quantiles
    (1 - fraction)/2 et (1 + fraction)/2, comme une fenetre stationnaire simple.
    """
    instants = np.sort(passages[np.isfinite(passages)])
    if instants.size < 3:
        return float("nan")
    k0 = int(np.floor((1 - fraction) / 2 * (instants.size - 1)))
    k1 = int(np.ceil((1 + fraction) / 2 * (instants.size - 1)))
    if instants[k1] <= instants[k0]:
        return float("nan")
    return float((k1 - k0) / (instants[k1] - instants[k0]) / largeur)


# Seyfried et al. (2009), tableau 2 : debit specifique J_s, en pers/(m.s), pour N = 60.
SEYFRIED_2009_N60 = {0.8: 1.61, 0.9: 1.86, 1.0: 1.90, 1.1: 1.93, 1.2: 1.97}


def parametres_goulot(config: dict, **changements) -> ParametresGoulot:
    """Parametres du banc depuis une configuration `goulot` lue par `lire_configuration`."""
    if config["scenario"] != "goulot":
        raise ValueError("l'etalonnage attend une configuration du scenario goulot")
    try:
        return ParametresGoulot(**(config["parametres"] | changements), graine=config["graine"])
    except TypeError as erreur:
        raise ValueError(f"parametres du goulot manquants ou inconnus : {erreur}") from erreur


def etalonner(config: dict, largeurs, graines) -> dict[float, np.ndarray]:
    """J_s par largeur de goulot et par graine ; NaN quand la foule ne passe pas en entier.

    Une foule qui ne passe pas en `duree` est comptee a part : moyenner son debit
    partiel avec les autres melangerait deux regimes, l'ecoulement et le bouchage.
    """
    resultats = {}
    for b in largeurs:
        debits = []
        for graine in graines:
            r = simuler_goulot(
                parametres_goulot(config | {"graine": graine}, largeur_goulot=float(b))
            )
            r.projection.verifier_convergence()
            passe = np.all(np.isfinite(r.passages))
            debits.append(r.debit_specifique if passe else np.nan)
        resultats[float(b)] = np.array(debits)
    return resultats
