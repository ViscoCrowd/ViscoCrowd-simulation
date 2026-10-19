"""Modele de foule : tout ce qui donne un sens « pieton » au moteur de particules.

Le moteur (core, geometry) integre des particules sous contraintes sans rien
savoir d'une foule. Les milieux, le guidage et les franchissements vivent ici.
"""

from viscocrowd.model.milieu import acceleration, vitesse_libre

__all__ = ["acceleration", "vitesse_libre"]
