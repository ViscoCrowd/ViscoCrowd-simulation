"""Production des figures et des animations.

`COMMANDES` : modules de ce paquet qui ajoutent une commande a la CLI (`ajouter_commande`),
un par ligne, dans l'ordre alphabetique. Une nouvelle commande de visualisation ajoute
sa ligne ici, a sa place : deux PR ne touchent plus la meme ligne de `cli.py`, et un
test verifie que la liste correspond aux modules du paquet.
"""

from viscocrowd.viz.figures import produire_toutes

COMMANDES = (
    "attente",
    "bouchage",
    "diagramme_anime",
    "duel",
    "panique",
    "pose_longue",
    "pression",
    "trainee",
    "variantes",
)

__all__ = ["COMMANDES", "produire_toutes"]
