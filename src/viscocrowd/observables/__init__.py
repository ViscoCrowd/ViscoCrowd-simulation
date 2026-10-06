"""Observables, calcules hors ligne a partir des trajectoires enregistrees.

Ce paquet ne depend volontairement d'aucun module de simulation : il travaille
sur des tableaux de positions et de vitesses. Il reste donc testable sur des
donnees synthetiques, sans faire tourner le moteur.
"""

from viscocrowd.observables.energie import ecart_entrainement, energie_mecanique

__all__ = ["ecart_entrainement", "energie_mecanique"]
