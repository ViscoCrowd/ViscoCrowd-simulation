"""Donnees facultatives du panneau, sans valeurs physiques imposees."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ParametresMilieu:
    """Grandeurs affichees pour un milieu ; None signifie non renseigne."""

    vitesse: float | None = None  # m/s
    relaxation: float | None = None  # s
    acceleration_max: float | None = None  # m/s^2


@dataclass(frozen=True)
class ParametresAffichage:
    """Valeurs presentees dans l'interface, independantes du moteur.

    Ces informations annotent le schema indicatif : elles ne recalculent pas
    sa geometrie et ne declenchent aucune simulation.
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
