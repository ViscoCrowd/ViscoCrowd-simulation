"""Image « pose longue » d'une evacuation de piscine : toutes les trajectoires d'un coup.

Comme une photographie a longue exposition, l'image superpose le chemin de chaque
agent sur toute l'archive, colore par sa vitesse. On y lit en une image les
couloirs reellement empruntes, les files, les zones lentes (sortie de l'eau,
carrelage mouille, porte) et la part de la plage que personne n'utilise.

Ce qui est trace : les deplacements d'un agent entre deux instants archives ou il
est ACTIF dans le meme etat (eau ou plage). Les franchissements le teleportent du
point d'attente au bord, puis du bord au point d'arrivee, et la sortie le pose
derriere la porte : ces sauts ne sont pas des chemins et ne sont pas traces.
Aucun calcul physique n'est relance ; seules les positions et vitesses archivees
servent.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

from viscocrowd.scenarios.piscine import EAU, PLAGE


def segments_actifs(
    x: np.ndarray, v: np.ndarray, etats: np.ndarray, pas: int = 1
) -> tuple[np.ndarray, np.ndarray]:
    """Segments de trajectoire (K, 2, 2) et vitesses (K,) des agents actifs.

    Args:
        x, v: positions et vitesses archivees (P, N, 2), en m et m/s.
        etats: (P, N) codes d'etat du scenario piscine.
        pas: un instant archive sur `pas`, pour alleger l'image (au moins 1).

    Returns:
        Les segments entre deux instants retenus consecutifs ou l'agent est dans le
        meme etat actif, et la norme de sa vitesse au debut de chaque segment.
    """
    if type(pas) is not int or pas < 1:
        raise ValueError("pas doit etre un entier strictement positif")
    x, v, etats = x[::pas], v[::pas], etats[::pas]
    debut, fin = etats[:-1], etats[1:]
    garde = (debut == fin) & ((debut == EAU) | (debut == PLAGE))
    instants, agents = np.nonzero(garde)
    segments = np.stack((x[instants, agents], x[instants + 1, agents]), axis=1)
    vitesses = np.hypot(*v[instants, agents].T)
    return segments, vitesses


def figure_pose_longue(donnees, pas: int = 2):
    """Figure matplotlib de la pose longue d'une archive piscine.

    Reprend le fond de la relecture (carte des milieux, murs, porte, sites) et y
    ajoute les trajectoires. Les disques et les compteurs de la relecture sont
    masques : l'image ne represente aucun instant en particulier.
    """
    from matplotlib.collections import LineCollection

    from viscocrowd.ui.relecture_piscine import LecteurPiscine

    lecteur = LecteurPiscine(donnees, interactif=False)
    figure, ax = lecteur.figure, lecteur.ax
    for disque in lecteur.disques:
        disque.set_visible(False)
    for texte in (lecteur.temps, lecteur.compteur, lecteur.effectifs):
        texte.set_text("")
    for legende in list(figure.legends):
        legende.remove()
    figure.texts[1].set_text("ÉVACUATION PISCINE  /  POSE LONGUE")

    segments, vitesses = segments_actifs(donnees.x, donnees.v, donnees.etats, pas)
    traits = LineCollection(
        segments, cmap="plasma", linewidths=1.1, alpha=0.35, zorder=3, capstyle="round"
    )
    traits.set_array(vitesses)
    traits.set_clim(0.0, max(float(np.quantile(vitesses, 0.99)), 1e-9) if vitesses.size else 1)
    ax.add_collection(traits)
    ax.grid(False)
    barre = figure.colorbar(traits, ax=ax, orientation="horizontal", fraction=0.05, pad=0.16)
    barre.set_label("vitesse (m/s)", color="#b7c5d0")
    barre.ax.tick_params(colors="#b7c5d0", labelsize=9)
    barre.solids.set_alpha(1.0)
    duree = donnees.t[-1] - donnees.t[0]
    lecteur.compteur.set_text(f"{donnees.x.shape[1]} trajectoires · {duree:.1f} s")
    return figure


def ajouter_commande(sous) -> None:
    commande = sous.add_parser(
        "pose-longue",
        help="image de toutes les trajectoires d'une archive piscine, colorees par la vitesse",
    )
    commande.add_argument("archive", type=Path, help="archive NPZ d'une simulation piscine")
    commande.add_argument("--image", type=Path, required=True, help="PNG a creer")
    commande.add_argument(
        "--pas", type=int, default=2, help="un instant archive sur PAS (defaut : 2)"
    )
    commande.set_defaults(fonction=commande_pose_longue)


def commande_pose_longue(args) -> int:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    from viscocrowd.io.trajectoires import lire_trajectoire

    figure = None
    try:
        if args.image.exists() or args.image.suffix.lower() != ".png":
            raise ValueError(f"choisir un nouveau fichier .png : {args.image}")
        figure = figure_pose_longue(lire_trajectoire(args.archive), args.pas)
        args.image.parent.mkdir(parents=True, exist_ok=True)
        figure.savefig(args.image, dpi=160)
        print(f"Image : {args.image}")
        return 0
    except (OSError, ValueError) as erreur:
        print(f"Pose longue refusee : {erreur}", file=sys.stderr)
        return 1
    finally:
        if figure is not None:
            plt.close(figure)
