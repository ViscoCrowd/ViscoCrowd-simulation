"""Recherche des paires voisines par grille de hachage spatial.

Tester toutes les paires coute N^2. Or deux disques ne peuvent se recouvrir que
s'ils sont proches : on decoupe donc le plan en cases carrees de cote egal au
plus grand diametre, de sorte que deux disques en contact sont toujours dans la
MEME case ou dans deux cases ADJACENTES. Il suffit alors de comparer chaque case
a elle-meme et a ses voisines, soit un cout proportionnel a N a densite fixe.

Pour ne compter chaque paire de cases qu'une fois, on ne regarde que la moitie
des huit voisines :

        . . .          (0,0) est la case courante ; les quatre decalages
        . X +          marques + sont parcourus, les autres le sont deja
        + + +          depuis la case voisine, dans l'autre sens.
"""

from __future__ import annotations

import numpy as np

# Decalages (colonne, ligne) de la demi-voisinage : la case elle-meme et quatre voisines.
_DECALAGES = ((0, 0), (1, 0), (-1, 1), (0, 1), (1, 1))


def paires_candidates(x: np.ndarray, r: np.ndarray, marge: float = 0.0) -> np.ndarray:
    """Paires (i, j), i < j, dont la distance est inferieure a r_i + r_j + marge.

    Avec marge = 0 ce sont exactement les paires en recouvrement strict. Une
    marge positive rend aussi les paires presque en contact : utile pour reutiliser
    la liste pendant plusieurs iterations de projection, ou les disques bougent un peu.

    Args:
        x: positions, de forme (N, 2), en metres.
        r: rayons, de forme (N,), en metres.
        marge: distance supplementaire de detection, en metres, positive ou nulle.

    Returns:
        Tableau d'entiers de forme (M, 2), trie par i puis j. Vide si M = 0.
    """
    if marge < 0.0:
        raise ValueError(f"la marge doit etre positive ou nulle, recu {marge}")
    # Toute comparaison avec un NaN est fausse : aucune paire ne serait detectee, et
    # `recouvrement_max` annoncerait 0 recouvrement pour une configuration corrompue,
    # resultat indiscernable d'une configuration valide. On refuse donc l'entree.
    if not (np.all(np.isfinite(x)) and np.all(np.isfinite(r))):
        raise ValueError("positions et rayons doivent etre finis (ni NaN ni infini)")

    n = x.shape[0]
    vide = np.empty((0, 2), dtype=np.int64)
    if n < 2:
        return vide

    # Cote de case : deux disques separes de moins de r_i + r_j + marge sont a
    # distance au plus 2 r_max + marge, donc dans la meme case ou dans deux voisines.
    cote = 2.0 * float(r.max()) + marge
    cases = np.floor((x - x.min(axis=0)) / cote).astype(np.int64)  # (N, 2)

    # Cle unique par case. Une case vide de bordure de chaque cote empeche qu'un
    # decalage de colonne « deborde » sur la ligne suivante.
    largeur = int(cases[:, 0].max()) + 3
    cles = (cases[:, 0] + 1) + (cases[:, 1] + 1) * largeur  # (N,)

    ordre = np.argsort(cles, kind="stable")
    cles_uniques, debuts, effectifs = np.unique(cles[ordre], return_index=True, return_counts=True)

    morceaux = []
    for dc, dl in _DECALAGES:
        voisines = cles_uniques + (dc + dl * largeur)
        position = np.minimum(np.searchsorted(cles_uniques, voisines), cles_uniques.size - 1)
        existe = cles_uniques[position] == voisines
        a = np.flatnonzero(existe)  # cases courantes ayant cette voisine occupee
        b = position[existe]  # indices des cases voisines correspondantes

        # Toutes les combinaisons (agent de la case a, agent de la case b), sans boucle Python.
        n_a, n_b = effectifs[a], effectifs[b]
        total = n_a * n_b
        quel_couple = np.repeat(np.arange(a.size), total)
        rang = np.arange(total.sum()) - np.repeat(np.cumsum(total) - total, total)
        i = ordre[debuts[a][quel_couple] + rang // n_b[quel_couple]]
        j = ordre[debuts[b][quel_couple] + rang % n_b[quel_couple]]

        if (dc, dl) == (0, 0):
            garder = i < j  # meme case : chaque paire apparait deux fois, on n'en garde qu'une
            i, j = i[garder], j[garder]
        morceaux.append(np.stack([i, j], axis=1))

    candidates = np.concatenate(morceaux)
    if candidates.size == 0:
        return vide

    i, j = candidates[:, 0], candidates[:, 1]
    distance2 = np.sum((x[i] - x[j]) ** 2, axis=1)
    proches = candidates[distance2 < (r[i] + r[j] + marge) ** 2]
    if proches.size == 0:
        return vide

    # Deux cases voisines ne donnent pas toujours i < j : on oriente puis on trie.
    orientees = np.sort(proches, axis=1)
    return orientees[np.lexsort((orientees[:, 1], orientees[:, 0]))]


def recouvrement_max(x: np.ndarray, r: np.ndarray) -> float:
    """Plus grand recouvrement entre deux disques, en metres. Zero s'il n'y en a pas.

    Pour la paire (i, j), le recouvrement vaut r_i + r_j - |x_i - x_j| quand il est
    positif. C'est l'indicateur de validation n_1 de la non-interpenetration :
    une grandeur mesuree et publiee, jamais supposee.
    """
    paires = paires_candidates(x, r)
    if paires.shape[0] == 0:
        return 0.0
    i, j = paires[:, 0], paires[:, 1]
    distance = np.linalg.norm(x[i] - x[j], axis=1)
    return float(np.max(r[i] + r[j] - distance))
