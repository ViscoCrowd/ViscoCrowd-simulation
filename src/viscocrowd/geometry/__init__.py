"""Geometrie : domaines, parois, projections sur l'ensemble admissible."""

from viscocrowd.geometry.boite import BoiteTournante
from viscocrowd.geometry.grille import paires_candidates, recouvrement_max
from viscocrowd.geometry.projection import ProjectionExclusion

__all__ = ["BoiteTournante", "ProjectionExclusion", "paires_candidates", "recouvrement_max"]
