"""Diagramme fondamental : vitesse et debit en fonction de la densite (spec § 3, M8).

Un point du diagramme est un couple (densite, vitesse) mesure dans une zone a un
instant, par exemple avec `mesures_voronoi`. Le debit specifique de ce point vaut
J = rho * v, en pers/(m.s) (Steffen et Seyfried 2010). Le diagramme agrege ces points
par classes de densite, comme le prevoit la spec § 3 : pour chaque classe, la
moyenne de la densite, de la vitesse et du debit, et leur ecart-type.

Ce que l'ecart-type n'est pas
-----------------------------

Les points d'une meme simulation se suivent a quelques dixiemes de seconde : ils
sont correles. L'ecart-type d'une classe decrit la DISPERSION des etats observes a
cette densite, pas l'incertitude sur sa moyenne. Pour une incertitude, il faut
comparer des graines independantes, classe par classe.

Ce module ne depend d'aucun simulateur : il travaille sur des tableaux.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from viscocrowd.core.verifications import exiger_fini


@dataclass(frozen=True)
class ClassesDensite:
    """Diagramme fondamental agrege par classes de densite.

    Attributes:
        bornes: (K + 1,) bornes croissantes des classes, en pers/m^2. La classe k
            contient les densites de [bornes[k], bornes[k + 1][.
        effectifs: (K,) nombre de points par classe.
        densite, vitesse, debit: (K,) moyennes par classe, en pers/m^2, m/s et
            pers/(m.s). NaN pour une classe vide.
        ecart_vitesse, ecart_debit: (K,) ecarts-types par classe (ddof = 1) ; NaN
            pour une classe de moins de deux points.
    """

    bornes: np.ndarray
    effectifs: np.ndarray
    densite: np.ndarray
    vitesse: np.ndarray
    debit: np.ndarray
    ecart_vitesse: np.ndarray
    ecart_debit: np.ndarray


def classer(densites: np.ndarray, vitesses: np.ndarray, bornes: np.ndarray) -> ClassesDensite:
    """Agrege des points (densite, vitesse) par classes de densite.

    Les points hors de [bornes[0], bornes[-1][ ne sont dans aucune classe : ils ne
    sont pas comptes. C'est voulu : choisir les bornes, c'est choisir le domaine
    du diagramme.

    Args:
        densites: (P,) densites des points, en pers/m^2, positives ou nulles.
        vitesses: (P,) vitesses des points, en m/s, positives ou nulles.
        bornes: (K + 1,) bornes strictement croissantes, en pers/m^2, K >= 1.

    Raises:
        ValueError: si une entree est non finie, de mauvaise forme ou de signe faux.
    """
    densites = np.asarray(densites, dtype=float)
    vitesses = np.asarray(vitesses, dtype=float)
    bornes = np.asarray(bornes, dtype=float)
    exiger_fini(densites=densites, vitesses=vitesses, bornes=bornes)
    if densites.ndim != 1 or vitesses.shape != densites.shape:
        raise ValueError("densites et vitesses doivent etre deux tableaux (P,) de meme taille")
    if bornes.ndim != 1 or bornes.size < 2 or np.any(np.diff(bornes) <= 0.0):
        raise ValueError("il faut au moins deux bornes, strictement croissantes")
    if np.any(densites < 0.0) or np.any(vitesses < 0.0):
        raise ValueError("densites et vitesses doivent etre positives ou nulles")

    k = bornes.size - 1
    classe = np.searchsorted(bornes, densites, side="right") - 1
    dedans = (classe >= 0) & (classe < k)
    debits = densites * vitesses

    effectifs = np.zeros(k, dtype=np.int64)
    moyennes = np.full((3, k), np.nan)
    ecarts = np.full((2, k), np.nan)
    for c in range(k):
        masque = dedans & (classe == c)
        effectifs[c] = int(np.count_nonzero(masque))
        if effectifs[c] == 0:
            continue
        moyennes[:, c] = densites[masque].mean(), vitesses[masque].mean(), debits[masque].mean()
        if effectifs[c] > 1:
            ecarts[:, c] = vitesses[masque].std(ddof=1), debits[masque].std(ddof=1)
    return ClassesDensite(bornes, effectifs, *moyennes, *ecarts)
