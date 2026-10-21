"""Modele de foule : tout ce qui donne un sens « pieton » au moteur de particules.

Le moteur (core, geometry) integre des particules sous contraintes sans rien
savoir d'une foule. Les milieux, le guidage et les franchissements vivent ici.
"""

from viscocrowd.model.milieu import (
    Milieu,
    ParametresMilieu,
    acceleration,
    pas_libre_milieux,
    vitesse_libre,
)

__all__ = ["Milieu", "ParametresMilieu", "acceleration", "pas_libre_milieux", "vitesse_libre"]
