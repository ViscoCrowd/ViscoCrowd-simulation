"""Choix du site de sortie selon la file d'attente (D3), et maitre-nageur (D5). Facultatif.

Le champ eikonal de l'eau (`model.guidage_piscine`) est statique : il « ignore l'attente
devant un site occupe ». Un vrai nageur, pres du bord, voit la file devant l'echelle et va
au rebord libre d'a cote. Ce module estime, pour chaque nageur proche du bord et chaque site
a sa portee, le temps total jusqu'a la porte par ce site :

    cout_k = |x - attente_k| / v_eau  +  attente_k  +  T_k  +  phi_plage(arrivee_k)

ou attente_k = (temps restant du franchissement en cours) + (nageurs devant lui) T_k. Les
nageurs « devant lui » sont ceux qui visent deja k et sont plus pres que lui de son point
d'attente (`files_devant`) : celui qui passerait le premier ne compte pas les autres
(revues de #188, #202).
Le nageur garde son site tant qu'un autre ne lui fait pas gagner plus de `marge` secondes :
sans cette hysteresis, deux sites de cout voisin le feraient osciller.

Mode coordonne (D5, maitre-nageur) : une seule personne voit tout le bassin et repartit les
nageurs un par un, du plus avance au moins avance, chacun vers le site de cout minimal en
tenant compte des nageurs deja envoyes. Aucune source ne decrit ce comportement : c'est un
scenario illustratif.

Toutes les durees sont en secondes, les distances en metres.
"""

from __future__ import annotations

import numpy as np


def files_devant(x: np.ndarray, attentes: np.ndarray, vises: np.ndarray) -> np.ndarray:
    """File (N, K) devant chaque nageur, pour chaque site, en nombre de nageurs.

    Pour le nageur i et le site k : les nageurs j qui visent deja k et sont strictement plus
    pres que i du point d'attente de k. Un nageur ne se compte pas lui-meme, ni ceux qui sont
    derriere lui.

    Args:
        x: (N, 2) positions des nageurs.
        attentes: (K, 2) points d'attente des sites.
        vises: (N,) site vise par chaque nageur ; -1 = aucun.
    """
    distances = np.hypot(x[:, None, 0] - attentes[None, :, 0], x[:, None, 1] - attentes[None, :, 1])
    vises = np.asarray(vises, dtype=np.int64)
    vise_k = vises[:, None] == np.arange(attentes.shape[0])[None, :]  # (N, K) : j vise k
    # devant[i, k] = somme sur j de [j vise k et d(j, k) < d(i, k)]
    plus_pres = distances[None, :, :] < distances[:, None, :]  # (i, j, k)
    return np.sum(plus_pres & vise_k[None, :, :], axis=1)


def couts_sites(
    x: np.ndarray,
    attentes: np.ndarray,
    v_eau: float,
    durees: np.ndarray,
    temps_apres: np.ndarray,
    files: np.ndarray,
    restes: np.ndarray | None = None,
) -> np.ndarray:
    """Temps total (N, K) jusqu'a la porte par chaque site, en s.

    Args:
        x: (N, 2) positions des nageurs.
        attentes: (K, 2) points d'attente des sites.
        v_eau: vitesse souhaitee dans l'eau, en m/s.
        durees: (K,) duree de franchissement de chaque site.
        temps_apres: (K,) temps de la plage depuis l'arrivee du site jusqu'a la porte.
        files: (K,) nageurs qui visent deja chaque site, ou (N, K) la file devant chaque
            nageur (`files_devant`).
        restes: (K,) temps restant du franchissement en cours sur chaque site (0 si libre).
    """
    trajet = (
        np.hypot(x[:, None, 0] - attentes[None, :, 0], x[:, None, 1] - attentes[None, :, 1]) / v_eau
    )
    attente = files * durees + (0.0 if restes is None else restes)
    return trajet + attente + (durees + temps_apres)[None, :]


def choisir(
    couts: np.ndarray, actuels: np.ndarray, marge: float, portee_ok: np.ndarray
) -> np.ndarray:
    """Site (N,) choisi par chaque nageur parmi ceux a portee ; -1 si aucun.

    Un nageur qui vise deja un site a portee n'en change que si le gain depasse `marge` (s).
    """
    couts = np.where(portee_ok, couts, np.inf)
    meilleur = np.argmin(couts, axis=1)
    rang = np.arange(couts.shape[0])
    choix = np.where(np.isfinite(couts[rang, meilleur]), meilleur, -1)
    actuels = np.asarray(actuels, dtype=np.int64)
    garde = actuels >= 0
    if np.any(garde):
        cout_actuel = np.full(couts.shape[0], np.inf)
        cout_actuel[garde] = couts[rang[garde], actuels[garde]]
        a_portee = np.isfinite(cout_actuel)  # site actuel encore a portee : meilleur fini aussi
        gain = np.full(couts.shape[0], np.inf)
        gain[a_portee] = cout_actuel[a_portee] - couts[rang[a_portee], meilleur[a_portee]]
        choix = np.where(a_portee & (gain <= marge), actuels, choix)
    return choix


def attribuer_coordonne(
    couts_sans_file: np.ndarray, durees: np.ndarray, ordre: np.ndarray
) -> np.ndarray:
    """Repartition (N,) des nageurs par un maitre-nageur qui voit tout (D5).

    Les nageurs sont servis dans `ordre` (le plus avance d'abord) ; chacun va au site de cout
    minimal, ou chaque nageur deja envoye a un site y ajoute sa duree de franchissement.
    """
    n, k = couts_sans_file.shape
    ordre = np.asarray(ordre, dtype=np.int64)
    if sorted(ordre.tolist()) != list(range(n)):
        raise ValueError("ordre doit etre une permutation de tous les nageurs")
    files = np.zeros(k)
    sites = np.full(n, -1, dtype=np.int64)
    for i in ordre:
        cout = couts_sans_file[i] + files * durees
        sites[i] = int(np.argmin(cout))
        files[sites[i]] += 1
    return sites
