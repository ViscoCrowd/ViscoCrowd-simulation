"""Carte des temps d'arret : ou la foule a attendu pendant une evacuation de piscine.

La pose longue (`viz.pose_longue`) montre ou les baigneurs sont passes ; cette carte
montre ou ils sont restes plantes. Chaque case de la grille cumule le temps passe par des
agents actifs (eau ou plage) dont la vitesse est sous un seuil : une case a 30 pers·s a vu,
par exemple, trois baigneurs y attendre 10 s chacun. On y lit les files devant les echelles,
le bouchon devant la porte, et les zones ou l'adherence fait pietiner.

Calcul sur l'archive seule, sans simulation : a l'instant archive k (sauf le dernier),
chaque agent actif et lent ajoute t[k+1] - t[k] a la case de sa position. L'ecart reel entre
instants est utilise, si bien qu'une archive espacee (`--archiver-tous`) donne le meme total
qu'une archive complete, a la resolution temporelle pres. Le total ne depend pas de la
taille des cases : la grille ne fait que le repartir.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

from viscocrowd.core.verifications import exiger_scalaire_fini
from viscocrowd.scenarios.piscine import EAU, PLAGE


def temps_arret(
    t: np.ndarray,
    x: np.ndarray,
    v: np.ndarray,
    actifs: np.ndarray,
    *,
    seuil: float,
    pas: float,
    emprise: tuple[float, float],
) -> np.ndarray:
    """Temps d'arret cumule par case (nx, ny), en s (soit pers·s pour la foule).

    Args:
        t: (P,) instants archives, en s.
        x, v: (P, N, 2) positions (m) et vitesses (m/s).
        actifs: (P, N) vrai pour un agent dans l'eau ou sur la plage.
        seuil: vitesse (m/s) sous laquelle un agent est tenu pour arrete.
        pas: cote d'une case, en m.
        emprise: (longueur, largeur) couvertes par la grille depuis l'origine, en m.
    """
    exiger_scalaire_fini("pas", pas, strictement_positif=True)
    exiger_scalaire_fini("seuil", seuil)
    if seuil < 0:
        raise ValueError("seuil doit etre positif ou nul")
    longueur, largeur = emprise
    nx, ny = int(np.ceil(longueur / pas)), int(np.ceil(largeur / pas))
    carte = np.zeros((nx, ny))
    if len(t) < 2:
        return carte
    ecarts = np.diff(np.asarray(t, dtype=float))
    lents = np.asarray(actifs[:-1], dtype=bool) & (np.hypot(v[:-1, :, 0], v[:-1, :, 1]) < seuil)
    instants, agents = np.nonzero(lents)
    if instants.size:
        positions = x[instants, agents]
        i = np.clip(np.floor(positions[:, 0] / pas).astype(np.int64), 0, nx - 1)
        j = np.clip(np.floor(positions[:, 1] / pas).astype(np.int64), 0, ny - 1)
        np.add.at(carte, (i, j), ecarts[instants])
    return carte


def figure_attente(donnees, seuil: float = 0.1, pas: float = 0.25):
    """Figure matplotlib de la carte des temps d'arret, sur le fond de la relecture."""
    from matplotlib.colors import LogNorm

    from viscocrowd.ui.relecture_piscine import LecteurPiscine

    lecteur = LecteurPiscine(donnees, interactif=False)
    figure, ax = lecteur.figure, lecteur.ax
    for disque in lecteur.disques:
        disque.set_visible(False)
    for texte in (lecteur.temps, lecteur.compteur, lecteur.effectifs):
        texte.set_text("")
    for legende in list(figure.legends):
        legende.remove()
    lecteur.sous_titre.set_text("ÉVACUATION PISCINE  /  TEMPS D'ARRÊT")

    piscine = lecteur.p.piscine
    emprise = (piscine.longueur_emprise + piscine.profondeur_porte, piscine.largeur_emprise)
    actifs = (donnees.etats == EAU) | (donnees.etats == PLAGE)
    carte = temps_arret(
        donnees.t, donnees.x, donnees.v, actifs, seuil=seuil, pas=pas, emprise=emprise
    )
    affichee = np.ma.masked_less_equal(carte, 0.0)
    image = ax.imshow(
        affichee.T,
        origin="lower",
        extent=(0.0, carte.shape[0] * pas, 0.0, carte.shape[1] * pas),
        cmap="inferno",
        norm=LogNorm(vmin=max(affichee.min(), 1e-2), vmax=max(affichee.max(), 1e-1))
        if affichee.count()
        else None,
        alpha=0.85,
        zorder=3,
        interpolation="nearest",
    )
    ax.grid(False)
    barre = figure.colorbar(image, ax=ax, orientation="horizontal", fraction=0.05, pad=0.16)
    barre.set_label(f"temps d'arrêt par case de {pas:g} m (pers·s)", color="#b7c5d0")
    barre.ax.tick_params(colors="#b7c5d0", labelsize=9)
    total = float(carte.sum())
    lecteur.compteur.set_text(f"arrêt total : {total:.0f} pers·s · seuil {seuil:g} m/s")
    return figure, carte


def ajouter_commande(sous) -> None:
    commande = sous.add_parser(
        "attente", help="carte des temps d'arret d'une archive piscine (files et bouchons)"
    )
    commande.add_argument("archive", type=Path, help="archive NPZ d'une simulation piscine")
    commande.add_argument("--image", type=Path, required=True, help="PNG a creer")
    commande.add_argument(
        "--seuil", type=float, default=0.1, help="vitesse d'arret, en m/s (defaut : 0,1)"
    )
    commande.add_argument("--pas", type=float, default=0.25, help="cote d'une case, en m")
    commande.set_defaults(fonction=commande_attente)


def commande_attente(args) -> int:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    from viscocrowd.io.trajectoires import lire_trajectoire

    figure = None
    try:
        if args.image.exists() or args.image.suffix.lower() != ".png":
            raise ValueError(f"choisir un nouveau fichier .png : {args.image}")
        figure, carte = figure_attente(lire_trajectoire(args.archive), args.seuil, args.pas)
        args.image.parent.mkdir(parents=True, exist_ok=True)
        figure.savefig(args.image, dpi=160)
        i, j = np.unravel_index(int(np.argmax(carte)), carte.shape)
        print(
            f"Arrêt total : {carte.sum():.1f} pers·s ; case la plus chargée "
            f"({(i + 0.5) * args.pas:.2f} m, {(j + 0.5) * args.pas:.2f} m) : "
            f"{carte.max():.1f} pers·s"
        )
        print(f"Image : {args.image}")
        return 0
    except (OSError, ValueError) as erreur:
        print(f"Carte des temps d'arret refusee : {erreur}", file=sys.stderr)
        return 1
    finally:
        if figure is not None:
            plt.close(figure)
