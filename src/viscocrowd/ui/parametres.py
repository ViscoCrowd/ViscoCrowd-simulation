"""Dimensions provisoires du plan et donnees facultatives du panneau."""

from __future__ import annotations

import math
from dataclasses import dataclass, field, fields


@dataclass(frozen=True)
class DimensionsPlan:
    """Dimensions en metres, communes a tous les elements du dessin.

    Ce jeu de travail sert a comparer les proportions ; il ne calibre pas le
    futur scenario physique. Les plages determinent l'emprise autour du bassin.
    """

    longueur_bassin: float = 25.0
    largeur_bassin: float = 12.5
    plage_gauche: float = 3.0
    plage_verticale: float = 4.0
    plage_sortie: float = 20.0  # distance entre le bord droit du bassin et le mur de sortie
    largeur_echelle: float = 0.5
    longueur_echelle: float = 1.0
    largeur_sortie: float = 1.2
    rayon_reference: float = 0.2

    def __post_init__(self) -> None:
        for attribut in fields(self):
            valeur = getattr(self, attribut.name)
            if not math.isfinite(valeur) or valeur <= 0:
                raise ValueError(f"{attribut.name} doit etre fini et strictement positif")
        # L'echelle est centree a 90 % du bord superieur du bassin.
        if self.largeur_echelle > 0.2 * self.longueur_bassin:
            raise ValueError("l'echelle doit tenir sur le bord du bassin")
        if self.longueur_echelle / 2 > min(self.largeur_bassin, self.plage_verticale):
            raise ValueError("l'echelle doit tenir entre le bassin et la plage")
        if self.largeur_sortie >= self.largeur_totale:
            raise ValueError("la sortie doit tenir sur le mur de droite")
        if self.largeur_sortie / 2 >= self.plage_sortie:
            raise ValueError("le symbole de sortie doit tenir sur la plage")

    @property
    def longueur_totale(self) -> float:
        return self.plage_gauche + self.longueur_bassin + self.plage_sortie

    @property
    def largeur_totale(self) -> float:
        return self.largeur_bassin + 2 * self.plage_verticale


@dataclass(frozen=True)
class ParametresMilieu:
    """Grandeurs affichees pour un milieu ; None signifie non renseigne."""

    vitesse: float | None = None  # m/s
    relaxation: float | None = None  # s
    acceleration_max: float | None = None  # m/s^2


@dataclass(frozen=True)
class ParametresAffichage:
    """Valeurs presentees dans l'interface, independantes du moteur.

    Ces informations ne declenchent aucune simulation. Le rayon de reference,
    le nombre d'echelles et la largeur de sortie affiches sont deduits du plan
    effectivement dessine. Les autres champs restent de simples annotations.
    """

    nombre_agents: int | None = None
    rayon_agents: float | None = None  # m
    niveau_panique: float | None = None
    nombre_echelles: int | None = None
    largeur_sortie: float | None = None  # m
    longueur_zone_mouillee: float | None = None  # m
    temps_rebord: float | None = None  # s
    temps_echelle: float | None = None  # s
    dt: float | None = None  # s
    graine: int | None = None
    eau: ParametresMilieu = field(default_factory=ParametresMilieu)
    mouille: ParametresMilieu = field(default_factory=ParametresMilieu)
    sec: ParametresMilieu = field(default_factory=ParametresMilieu)
