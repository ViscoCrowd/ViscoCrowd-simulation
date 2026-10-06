"""ViscoCrowd — simulation particulaire d'une evacuation de piscine en panique.

Le moteur suit le cadre du module R5.12 : un pas libre, puis une projection sur
l'ensemble des configurations admissibles. La vitesse n'est jamais transportee
d'un pas a l'autre, elle est recalculee a partir du deplacement effectivement
realise : c'est la que le choc se produit.
"""

__version__ = "0.1.0"

__all__ = ["__version__"]
