"""Observables, calcules hors ligne a partir des trajectoires enregistrees.

Ce paquet ne depend volontairement d'aucun module de simulation : il travaille
sur des tableaux de positions et de vitesses. Il reste donc testable sur des
donnees synthetiques, sans faire tourner le moteur.
"""

from viscocrowd.observables.debit import Franchissements, debit_specifique, franchissements
from viscocrowd.observables.energie import ecart_entrainement, energie_mecanique

# La reference de Weidmann s'importe par son module (observables.weidmann) : elle
# definit elle aussi un debit_specifique, de la densite cette fois.

__all__ = [
    "Franchissements",
    "debit_specifique",
    "ecart_entrainement",
    "energie_mecanique",
    "franchissements",
]
