"""Banc G1/G5 : foule guidee dans un couloir, avec milieux, exclusion et obstacles."""

from dataclasses import dataclass

import numpy as np

from viscocrowd.core.integrator import trajectoire
from viscocrowd.core.rng import generateur
from viscocrowd.core.state import State
from viscocrowd.geometry.couloir import Couloir
from viscocrowd.geometry.obstacle import ObstacleRectangle
from viscocrowd.geometry.projection import ProjectionExclusion
from viscocrowd.model.carte import CarteBandes
from viscocrowd.model.eikonal import ChampEikonal, GrilleReguliere, vitesse_des_milieux
from viscocrowd.model.guidage import direction_aval
from viscocrowd.model.milieu import Direction, Milieu, ParametresMilieu, pas_libre_milieux

GUIDAGES = ("aval", "eikonal")


@dataclass(frozen=True)
class ParametresCouloir:
    """Tous les choix du banc sont explicites dans le YAML, en unites SI.

    `guidage` vaut "aval" (direction analytique (1, 0) de G1, sans obstacle) ou
    "eikonal" (champ de temps de parcours de G2, calcule sur une grille de pas
    `pas_guidage`). `obstacles` liste des rectangles [x_min, x_max, y_min, y_max].
    """

    longueur: float
    largeur: float
    n_agents: int
    colonnes: int
    rayon: float
    espacement: float
    origine_x: float
    bruit: float
    dt: float
    duree: float
    tolerance: float
    facteur_vitesse: float
    frontieres: tuple[float, ...]
    milieux: tuple[str, ...]
    parametres_milieux: dict[str, ParametresMilieu]
    guidage: str
    pas_guidage: float
    obstacles: tuple[tuple[float, float, float, float], ...]
    graine: int

    def __post_init__(self) -> None:
        for nom in ("n_agents", "colonnes", "graine"):
            valeur = getattr(self, nom)
            if type(valeur) is not int or valeur < (0 if nom == "graine" else 1):
                raise ValueError(f"{nom} doit etre entier, positif (graine nulle admise)")
        for nom in (
            "longueur",
            "largeur",
            "rayon",
            "espacement",
            "origine_x",
            "bruit",
            "dt",
            "duree",
            "tolerance",
            "facteur_vitesse",
            "pas_guidage",
        ):
            valeur = getattr(self, nom)
            if type(valeur) not in (int, float) or not np.isfinite(valeur):
                raise ValueError(f"{nom} doit etre un nombre reel fini")
            if valeur < 0 or (nom not in ("bruit", "duree", "facteur_vitesse") and valeur == 0):
                raise ValueError(f"{nom} hors domaine")
        try:
            parametres = {
                nom: p if isinstance(p, ParametresMilieu) else ParametresMilieu(**p)
                for nom, p in self.parametres_milieux.items()
            }
            carte = CarteBandes(self.frontieres, tuple(Milieu[nom] for nom in self.milieux))
            for nom in parametres:
                Milieu[nom]
            utilises = [parametres[nom] for nom in self.milieux]
        except (KeyError, TypeError, AttributeError) as erreur:
            raise ValueError(
                "milieux et parametres_milieux doivent declarer des milieux valides et complets"
            ) from erreur
        if any(f <= 0 or f >= self.longueur for f in carte.frontieres):
            raise ValueError("frontieres doit rester entre 0 et longueur")
        if any(p.vitesse <= 0 for p in utilises):
            raise ValueError("la vitesse souhaitee des milieux du couloir doit etre positive")
        if self.dt > min(p.relaxation for p in utilises):
            raise ValueError("dt doit etre inferieur ou egal aux temps de relaxation")
        if self.dt * self.facteur_vitesse * max(p.vitesse for p in utilises) > self.rayon / 5:
            raise ValueError("dt trop grand : deplacement souhaite par pas > rayon/5")
        if self.espacement - 2 * self.bruit < 2 * self.rayon:
            raise ValueError("espacement insuffisant pour garantir le non-recouvrement initial")
        object.__setattr__(self, "frontieres", carte.frontieres)
        object.__setattr__(self, "milieux", tuple(self.milieux))
        object.__setattr__(self, "parametres_milieux", parametres)
        # Bornes du placement, bruit inclus : controle avant tout tirage.
        lignes = (self.n_agents + self.colonnes - 1) // self.colonnes
        if (
            self.origine_x - self.bruit < self.rayon
            or self.origine_x
            + (min(self.colonnes, self.n_agents) - 1) * self.espacement
            + self.bruit
            + self.rayon
            >= self.longueur
            or (lignes - 1) * self.espacement / 2 + self.bruit + self.rayon > self.largeur / 2
        ):
            raise ValueError("population initiale trop grande ou hors du couloir avant la sortie")
        self._verifier_guidage_et_obstacles()

    def _verifier_guidage_et_obstacles(self) -> None:
        if self.guidage not in GUIDAGES:
            raise ValueError(f"guidage doit valoir {' ou '.join(GUIDAGES)}, recu {self.guidage!r}")
        # La grille doit resoudre la marge d'un rayon autour des obstacles.
        if self.pas_guidage > self.rayon:
            raise ValueError("pas_guidage doit etre inferieur ou egal au rayon")
        try:
            rectangles = tuple(ObstacleRectangle(*map(float, o)) for o in self.obstacles)
        except (TypeError, ValueError) as erreur:
            raise ValueError(
                "chaque obstacle doit etre [x_min, x_max, y_min, y_max], fini et non vide"
            ) from erreur
        if rectangles and self.guidage != "eikonal":
            raise ValueError("des obstacles exigent le guidage eikonal : l'aval les traverse")
        # Un diametre libre autour de chaque obstacle : la projection reste exacte
        # (cf. Couloir) et un agent peut toujours passer.
        diametre = 2 * self.rayon
        for o in rectangles:
            if (
                o.x_min < diametre
                or o.x_max > self.longueur
                or o.y_min - (-self.largeur / 2) < diametre
                or self.largeur / 2 - o.y_max < diametre
            ):
                raise ValueError(
                    "chaque obstacle doit laisser un diametre d'agent jusqu'aux parois "
                    "et finir avant la section de sortie"
                )
        for k, a in enumerate(rectangles):
            for b in rectangles[k + 1 :]:
                ecart = max(
                    b.x_min - a.x_max, a.x_min - b.x_max, b.y_min - a.y_max, a.y_min - b.y_max
                )
                if ecart < diametre:
                    raise ValueError("deux obstacles doivent etre separes d'au moins un diametre")
        depart = positions_de_depart(self, bruit=False)
        if any(
            np.any(o.distance(depart) < self.rayon + self.bruit * np.sqrt(2)) for o in rectangles
        ):
            raise ValueError("la population initiale chevauche un obstacle")
        object.__setattr__(self, "obstacles", tuple(tuple(map(float, o)) for o in self.obstacles))

    @property
    def rectangles(self) -> tuple[ObstacleRectangle, ...]:
        return tuple(ObstacleRectangle(*o) for o in self.obstacles)


def positions_de_depart(p: ParametresCouloir, *, bruit: bool = True) -> np.ndarray:
    """Grille de depart (N, 2), perturbee par la graine si `bruit`."""
    indices = np.arange(p.n_agents)
    lignes = (p.n_agents + p.colonnes - 1) // p.colonnes
    x = np.column_stack(
        (
            p.origine_x + (indices % p.colonnes) * p.espacement,
            (indices // p.colonnes - (lignes - 1) / 2) * p.espacement,
        )
    )
    if bruit:
        x += generateur(p.graine).uniform(-p.bruit, p.bruit, size=x.shape)
    return x


@dataclass(frozen=True)
class ResultatCouloir:
    t: np.ndarray
    x: np.ndarray
    v: np.ndarray
    rayons: np.ndarray
    domaine: Couloir
    projection: ProjectionExclusion
    parametres: ParametresCouloir

    def violation_paroi_max(self) -> float:
        return max(
            self.domaine.violation(x, self.rayons, t) for x, t in zip(self.x, self.t, strict=True)
        )


def guidage_du_couloir(p: ParametresCouloir, carte: CarteBandes) -> Direction:
    """Direction de guidage du banc : analytique (G1) ou eikonale (G2).

    Le champ eikonal a sa sortie sur la section x = longueur ; au-dela, son
    gradient est nul. Les agents passes en aval y reprennent la direction (1, 0),
    comme avec le guidage analytique, pour continuer entre les parois.
    """
    if p.guidage == "aval":
        return direction_aval
    grille = GrilleReguliere.couvrant(0.0, p.longueur, -p.largeur / 2, p.largeur / 2, p.pas_guidage)
    vitesse = vitesse_des_milieux(
        carte, {Milieu[nom]: v for nom, v in p.parametres_milieux.items()}, p.rectangles, p.rayon
    )
    champ = ChampEikonal(grille, vitesse, lambda points: points[:, 0] >= p.longueur - 1e-9)

    def _direction(etat: State) -> np.ndarray:
        e = champ(etat)
        en_aval = np.all(e == 0.0, axis=1) & (etat.x[:, 0] >= p.longueur - p.pas_guidage)
        e[en_aval] = direction_aval(etat)[en_aval]
        return e

    return _direction


def simuler_couloir(p: ParametresCouloir) -> ResultatCouloir:
    """Assemble les briques existantes ; la projection est stricte a chaque pas."""
    domaine = Couloir(p.longueur, p.largeur, p.rectangles)
    initial = State(
        x=positions_de_depart(p), v=np.zeros((p.n_agents, 2)), r=np.full(p.n_agents, p.rayon)
    )
    carte = CarteBandes(p.frontieres, tuple(Milieu[nom] for nom in p.milieux))
    libre = pas_libre_milieux(
        guidage_du_couloir(p, carte),
        carte,
        {Milieu[nom]: v for nom, v in p.parametres_milieux.items()},
        facteur_vitesse=p.facteur_vitesse,
    )
    projection = ProjectionExclusion(domaine.projeter, tolerance=p.tolerance, strict=True)
    t, x, v = trajectoire(initial, p.dt, p.duree, libre, projection)
    # Controle a posteriori aussi : les corrections de contact peuvent changer v.
    if np.max(np.linalg.norm(v, axis=2)) * p.dt > p.rayon / 5 * (1 + 1e-12):
        raise ValueError("deplacement mesure par pas > rayon/5 ; reduire dt")
    return ResultatCouloir(t, x, v, initial.r, domaine, projection, p)
