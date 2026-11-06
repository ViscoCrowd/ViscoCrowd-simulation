"""Relation vitesse-espacement : on ralentit derriere celui qu'on suit (proposition E0).

Sans elle, un agent marche a sa vitesse souhaitee jusqu'au contact, que seule la
projection arrete : dans un goulot, la foule avance presque jointive et son debit
vaut environ le double de la mesure de Seyfried et al. (2009). Les pietons reels
gardent un ecart avec celui qui les precede.

On reprend la fonction de vitesse optimale du modele de Tordeux, Chraibi et
Seyfried (2016) :

    V(s) = min(v0, max(0, s / T))

ou s est le JEU (m) entre le disque de l'agent et celui de son meneur, et T (s)
le temps d'espacement. La vitesse souhaitee de l'agent devient V(s) dans la
direction de son guidage ; sa direction n'est pas modifiee.

Meneur
------

Le meneur de i est le plus proche des agents j qui verifient :

    e_i . (x_j - x_i) > 0                  j est devant i ;
    |e_i^perp . (x_j - x_i)| < r_i + r_j   j est dans le couloir de DEMI-largeur
                                           r_i + r_j autour de la direction de i ;
    avance_j < avance_i                    j est plus avance vers la sortie.

Les deux premieres conditions sont celles de Tordeux et al., avec l = r_i + r_j
pour demi-largeur. La troisieme est la notre. `avance` est le temps de parcours
restant jusqu'a la sortie (le champ eikonal) : un ordre strict entre agents. La
relation « suivre » ne peut donc former AUCUN cycle, de quelque longueur que ce
soit, et l'agent le plus avance d'un groupe n'a jamais de meneur : rien ne peut
immobiliser tout le groupe par attente mutuelle. Le premier prototype, sans cette
condition, bouchait le goulot E0 sur toutes les largeurs : deux agents qui
convergent s'attendaient l'un l'autre. Exclure seulement les paires mutuelles
laissait possibles les cycles de trois agents ou plus (revue de #58).

Limite : le meneur est cherche en ligne droite, sans tenir compte des murs. Pres
des angles d'un goulot, un agent peut ralentir derriere un agent deja engage de
l'autre cote de l'angle ; l'etalonnage de T inclut cet effet.

Seuls les meneurs a moins de T * v0 comptent (au-dela, V = v0) : la recherche se
limite aux paires proches (`geometry.grille.paires_candidates`), a cout lineaire.
"""

from __future__ import annotations

import numpy as np

from viscocrowd.core.verifications import exiger_fini, exiger_scalaire_fini
from viscocrowd.geometry.grille import paires_candidates


def jeu_au_meneur(
    x: np.ndarray, r: np.ndarray, e: np.ndarray, avance: np.ndarray, portee: float
) -> np.ndarray:
    """Jeu (N,) en m entre chaque disque et celui de son meneur ; inf sans meneur a portee.

    Args:
        x, r, e: positions (N, 2), rayons (N,) et directions de guidage (N, 2).
        avance: temps restant jusqu'a la sortie (N,), en s ; plus petit = plus avance.
        portee: jeu (m) au-dela duquel un meneur est ignore, positif ou nul.

    Un agent sans direction (e nul) n'a pas de meneur. Le jeu est negatif si les
    deux disques se recouvrent, ce que la projection tolere jusqu'a sa tolerance.
    """
    x, r, e = (np.asarray(a, dtype=float) for a in (x, r, e))
    avance = np.asarray(avance, dtype=float)
    n = x.shape[0]
    if x.shape != (n, 2) or e.shape != (n, 2) or r.shape != (n,) or avance.shape != (n,):
        raise ValueError("x, e, r et avance doivent etre de formes (N, 2), (N, 2), (N,), (N,)")
    exiger_fini(x=x, r=r, e=e)
    if np.any(np.isnan(avance)):
        raise ValueError("avance ne doit pas contenir de NaN (+inf : sortie inatteignable)")
    exiger_scalaire_fini("portee", portee)
    if not portee >= 0.0:
        raise ValueError("portee doit etre positive ou nulle")
    jeux = np.full(n, np.inf)
    paires = paires_candidates(x, r, marge=portee)
    if paires.size == 0:
        return jeux
    # Chaque paire proche est examinee dans les deux sens : i suit-il j, j suit-il i ?
    suiveur = np.concatenate((paires[:, 0], paires[:, 1]))
    meneur = np.concatenate((paires[:, 1], paires[:, 0]))
    d = x[meneur] - x[suiveur]
    es = e[suiveur]
    devant = d[:, 0] * es[:, 0] + d[:, 1] * es[:, 1]
    lateral = np.abs(d[:, 1] * es[:, 0] - d[:, 0] * es[:, 1])
    contact = r[suiveur] + r[meneur]
    suit = (devant > 0.0) & (lateral < contact) & (avance[meneur] < avance[suiveur])
    np.minimum.at(jeux, suiveur[suit], np.hypot(d[suit, 0], d[suit, 1]) - contact[suit])
    return jeux


def facteur_espacement(
    x: np.ndarray,
    r: np.ndarray,
    e: np.ndarray,
    avance: np.ndarray,
    vitesse: np.ndarray,
    temps: float,
) -> np.ndarray:
    """V(s) / v0 dans [0, 1], par agent : la part de sa vitesse souhaitee qu'il garde.

    Args:
        x, r, e: positions (N, 2), rayons (N,) et directions de guidage (N, 2).
        avance: temps restant jusqu'a la sortie (N,), en s, qui ordonne les agents.
        vitesse: vitesse souhaitee v0 de chaque agent (N,), en m/s, positive ou nulle.
        temps: temps d'espacement T, en s, strictement positif.
    """
    exiger_scalaire_fini("temps", temps, strictement_positif=True)
    vitesse = np.broadcast_to(np.asarray(vitesse, dtype=float), (np.shape(x)[0],))
    exiger_fini(vitesse=vitesse)
    if np.any(vitesse < 0.0):
        raise ValueError("la vitesse souhaitee doit etre positive ou nulle")
    portee = temps * float(np.max(vitesse, initial=0.0))
    jeu = jeu_au_meneur(x, r, e, avance, portee)
    # Un agent a l'arret (v0 = 0) n'a rien a moduler : facteur 1, sans division par zero.
    rapport = np.divide(jeu, temps * vitesse, out=np.ones_like(vitesse), where=vitesse > 0.0)
    return np.clip(rapport, 0.0, 1.0)
