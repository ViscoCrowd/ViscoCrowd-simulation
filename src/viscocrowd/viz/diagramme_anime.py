"""Relecture de la piscine avec son diagramme fondamental qui se trace en direct.

A gauche, la relecture habituelle ; a droite, le plan densite / debit specifique
devant la porte. Le point courant se deplace a mesure que la foule arrive, se
densifie et s'ecoule, avec une trainee des dernieres secondes ; tous les points de
l'evacuation restent en fond, et la relation de Weidmann (1993) sert de repere.
L'animation relie ainsi ce qu'on voit (la file devant la porte) a l'objet central
de la problematique.

Mesure : celle de M8 (#124, `scenarios.diagramme_piscine`) sur l'archive, sans
nouvelle simulation. Densite et vitesse de Voronoi dans la zone devant la porte
(1,8 m sur 2 m, a 0,2 m du mur), cellules bornees par la salle de `recul` m.
Chaque point est un instant d'une evacuation sans phase stationnaire : la courbe
decrit une file qui se forme puis se vide, pas un ecoulement etabli.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

from viscocrowd.observables import weidmann
from viscocrowd.scenarios.diagramme_goulot import serie_voronoi
from viscocrowd.scenarios.diagramme_piscine import salle_porte, zone_porte
from viscocrowd.ui.relecture_piscine import LecteurPiscine

TRAINEE = 2.0  # s de points recents surlignes derriere le point courant
RHO = "\u03c1"  # lettre grecque rho, ecrite en echappement (regle RUF001)


class LecteurDiagramme(LecteurPiscine):
    """Relecture piscine et diagramme fondamental synchronises sur le meme instant."""

    def __init__(
        self,
        donnees,
        *,
        interactif: bool = True,
        vitesse: float = 1.0,
        recul: float = 10.0,
        pas_mesure: int = 10,
    ):
        super().__init__(donnees, interactif=interactif, vitesse=vitesse)
        from matplotlib.patches import Rectangle as Cadre

        g = self.p.piscine
        salle, zone = salle_porte(g, recul), zone_porte(g)
        self.serie = serie_voronoi(donnees.t, donnees.x, salle, zone, pas_mesure=pas_mesure)
        self.ax.grid(False)
        self.figure.texts[1].set_text("ÉVACUATION PISCINE  /  DIAGRAMME FONDAMENTAL")
        self.ax.set_position((0.05, 0.29, 0.56, 0.46))
        self.ax.add_patch(
            Cadre(
                (zone.x_min, zone.y_min),
                zone.x_max - zone.x_min,
                zone.y_max - zone.y_min,
                fill=False,
                edgecolor="#ffd166",
                lw=1.2,
                linestyle="--",
                zorder=5,
            )
        )
        couleur = "#b7c5d0"
        self.ax_fd = self.figure.add_axes((0.68, 0.30, 0.28, 0.44), facecolor="#172431")
        ax = self.ax_fd
        rho_max = max(4.0, float(np.max(self.serie.densite, initial=0.0)) * 1.1)
        rho = np.linspace(1e-3, rho_max, 300)
        ax.plot(rho, weidmann.debit_specifique(rho), color="#8193a6", ls="--", lw=1)
        ax.text(rho_max * 0.97, 0.15, "Weidmann (1993)", color="#8193a6", fontsize=8, ha="right")
        ax.scatter(self.serie.densite, self.serie.debit, s=6, color="#4daeb9", alpha=0.18, lw=0)
        (self.trainee,) = ax.plot([], [], color="#ffd166", lw=1.4, alpha=0.8)
        (self.point,) = ax.plot([], [], "o", color="#ffd166", markersize=9, mec="#101923")
        j_max = max(2.0, float(np.max(self.serie.debit, initial=0.0)) * 1.1)
        ax.set(xlim=(0, rho_max), ylim=(0, j_max))
        ax.set_xlabel(f"densité {RHO} (pers/m²)", color=couleur)
        ax.set_ylabel(f"débit spécifique J = {RHO}v (pers/(m·s))", color=couleur)
        ax.set_title("Zone devant la porte (cadre jaune)", color=couleur, fontsize=10)
        ax.tick_params(colors=couleur, labelsize=9)
        for spine in ax.spines.values():
            spine.set_color("#3a4b5c")
        self.mesure = ax.text(0.03, 0.95, "", transform=ax.transAxes, color="white", va="top")
        self.afficher(self.index)

    def afficher(self, index: int) -> None:
        super().afficher(index)
        if not hasattr(self, "point"):
            return  # premier affichage du parent, avant la construction du diagramme
        t = self.donnees.t[self.index]
        s = self.serie
        recents = (s.t <= t) & (s.t > t - TRAINEE)
        self.trainee.set_data(s.densite[recents], s.debit[recents])
        dernier = np.searchsorted(s.t, t, side="right") - 1
        # Pas de point si la zone n'a rien mesure depuis plus d'une trainee : vide.
        if dernier >= 0 and s.t[dernier] > t - TRAINEE:
            self.point.set_data([s.densite[dernier]], [s.debit[dernier]])
            self.mesure.set_text(
                f"{RHO} = {s.densite[dernier]:.2f} pers/m²\nv = {s.vitesse[dernier]:.2f} m/s"
            )
        else:
            self.point.set_data([], [])
            self.mesure.set_text("zone vide")
        self.figure.canvas.draw_idle()


def ajouter_commande(sous) -> None:
    commande = sous.add_parser(
        "diagramme-anime",
        help="relecture piscine avec le diagramme fondamental devant la porte, en direct",
    )
    commande.add_argument("archive", type=Path, help="archive NPZ d'une simulation piscine")
    commande.add_argument("--gif", type=Path, help="export GIF hors ecran")
    commande.add_argument("--image", type=Path, help="export PNG hors ecran")
    commande.add_argument("--instant", type=float, default=0.0, help="instant du PNG, en s")
    commande.add_argument("--vitesse", type=float, default=4.0, help="facteur de lecture")
    commande.set_defaults(fonction=commande_diagramme_anime)


def commande_diagramme_anime(args) -> int:
    import matplotlib

    if args.gif or args.image:
        matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.backends import backend_registry

    from viscocrowd.io.trajectoires import lire_trajectoire

    lecteur = None
    try:
        for chemin, extension in ((args.gif, ".gif"), (args.image, ".png")):
            if chemin and (chemin.exists() or chemin.suffix.lower() != extension):
                raise ValueError(f"choisir un nouveau fichier {extension} : {chemin}")
        lecteur = LecteurDiagramme(
            lire_trajectoire(args.archive),
            interactif=not (args.gif or args.image),
            vitesse=args.vitesse,
        )
        lecteur.aller_au_temps(args.instant)
        if args.image:
            args.image.parent.mkdir(parents=True, exist_ok=True)
            lecteur.figure.savefig(args.image, dpi=140)
            print(f"Image : {args.image}")
        if args.gif:
            args.gif.parent.mkdir(parents=True, exist_ok=True)
            lecteur.exporter_gif(args.gif)
            print(f"Animation : {args.gif}")
        if not (args.gif or args.image):
            if backend_registry.resolve_backend(plt.get_backend())[1] is None:
                raise ValueError("affichage local requis ; utiliser --gif ou --image hors ecran")
            lecteur.basculer()
            plt.show(block=True)
        return 0
    except (OSError, ValueError) as erreur:
        print(f"Diagramme anime refuse : {erreur}", file=sys.stderr)
        return 1
    finally:
        if lecteur is not None:
            plt.close(lecteur.figure)
