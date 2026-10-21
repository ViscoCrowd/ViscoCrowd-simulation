"""Banc G1/G5 : foule guidee dans un couloir, avec milieux et exclusion."""

from dataclasses import dataclass

import numpy as np

from viscocrowd.core.integrator import trajectoire
from viscocrowd.core.rng import generateur
from viscocrowd.core.state import State
from viscocrowd.geometry.couloir import Couloir
from viscocrowd.geometry.projection import ProjectionExclusion
from viscocrowd.model.carte import CarteBandes
from viscocrowd.model.guidage import direction_aval
from viscocrowd.model.milieu import Milieu, ParametresMilieu, pas_libre_milieux


@dataclass(frozen=True)
class ParametresCouloir:
    """Tous les choix du banc sont explicites dans le YAML, en unites SI."""

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


def simuler_couloir(p: ParametresCouloir) -> ResultatCouloir:
    """Assemble les briques existantes ; la projection est stricte a chaque pas."""
    domaine = Couloir(p.longueur, p.largeur)
    indices = np.arange(p.n_agents)
    lignes = (p.n_agents + p.colonnes - 1) // p.colonnes
    x = np.column_stack(
        (
            p.origine_x + (indices % p.colonnes) * p.espacement,
            (indices // p.colonnes - (lignes - 1) / 2) * p.espacement,
        )
    )
    x += generateur(p.graine).uniform(-p.bruit, p.bruit, size=x.shape)
    initial = State(x=x, v=np.zeros_like(x), r=np.full(p.n_agents, p.rayon))
    carte = CarteBandes(p.frontieres, tuple(Milieu[nom] for nom in p.milieux))
    libre = pas_libre_milieux(
        direction_aval,
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
