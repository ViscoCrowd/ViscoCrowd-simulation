"""Observables, calcules hors ligne a partir des trajectoires enregistrees.

Ce paquet ne depend volontairement d'aucun module de simulation : il travaille
sur des tableaux de positions et de vitesses. Il reste donc testable sur des
donnees synthetiques, sans faire tourner le moteur.
"""

from viscocrowd.io.trajectoires import charger_et_valider_complete
from viscocrowd.observables.debit import (
    Franchissements,
    debit_specifique,
    debit_specifique_trajectoire,
    franchissements,
    franchissements_trajectoire,
)
from viscocrowd.observables.densite import (
    Rectangle,
    densite_comptage,
    densite_comptage_trajectoire,
    densite_voronoi,
    densite_voronoi_trajectoire,
    mesures_voronoi,
    mesures_voronoi_trajectoire,
    serie_densite_comptage_trajectoire,
    vitesse_voronoi,
    vitesse_voronoi_trajectoire,
)
from viscocrowd.observables.energie import (
    ecart_entrainement,
    energie_mecanique,
    energie_mecanique_trajectoire,
)
from viscocrowd.observables.sortie import (
    Sorties,
    sorties_definitives,
    sorties_definitives_trajectoire,
)

# La reference de Weidmann s'importe par son module (observables.weidmann) : elle
# definit elle aussi un debit_specifique, de la densite cette fois.

__all__ = [
    "Franchissements",
    "Rectangle",
    "Sorties",
    "charger_et_valider_complete",
    "debit_specifique",
    "debit_specifique_trajectoire",
    "densite_comptage",
    "densite_comptage_trajectoire",
    "densite_voronoi",
    "densite_voronoi_trajectoire",
    "ecart_entrainement",
    "energie_mecanique",
    "energie_mecanique_trajectoire",
    "franchissements",
    "franchissements_trajectoire",
    "mesures_voronoi",
    "mesures_voronoi_trajectoire",
    "serie_densite_comptage_trajectoire",
    "sorties_definitives",
    "sorties_definitives_trajectoire",
    "vitesse_voronoi",
    "vitesse_voronoi_trajectoire",
]
