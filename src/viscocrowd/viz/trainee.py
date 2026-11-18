"""Relecture de la piscine avec la trainee d'eau que laissent les baigneurs.

Le film d'eau depose sur la plage (`model.egouttage`) est superpose a la
relecture : bleu de plus en plus franc a mesure qu'il s'epaissit, et contour
blanc la ou il depasse le seuil, c'est-a-dire la ou le carrelage est devenu
MOUILLE. On voit les traces de chaque baigneur, trop minces seules, et leur
accumulation la ou les trajets se superposent. Le film affiche est la derniere
image gardee par la simulation (toutes les `PERIODE_EAU` s), sans interpolation.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

from viscocrowd.ui.relecture_piscine import LecteurPiscine


class LecteurTrainee(LecteurPiscine):
    """Relecture piscine avec le film d'eau de l'egouttage."""

    def __init__(self, donnees, eau_sol, t_eau, pas, seuil, *, interactif=True, vitesse=1.0):
        eau_sol, t_eau = np.asarray(eau_sol, dtype=float), np.asarray(t_eau, dtype=float)
        if eau_sol.ndim != 3 or t_eau.shape != (eau_sol.shape[0],):
            raise ValueError("eau_sol doit etre (K, nx, ny) avec un instant par image")
        if not np.all(np.isfinite(eau_sol)) or np.any(eau_sol < 0):
            raise ValueError("eau_sol doit etre fini et positif ou nul")
        self.eau_sol, self.t_eau, self.seuil = eau_sol, t_eau, float(seuil)
        super().__init__(donnees, interactif=interactif, vitesse=vitesse)
        from matplotlib.colors import LinearSegmentedColormap

        nx, ny = eau_sol.shape[1:]
        self.ax.grid(False)
        self.sous_titre.set_text("ÉVACUATION PISCINE  /  TRAÎNÉE D'EAU")
        cmap = LinearSegmentedColormap.from_list(
            "eau", [(0.38, 0.78, 0.93, 0.0), (0.38, 0.78, 0.93, 0.95)]
        )
        self.film = self.ax.imshow(
            eau_sol[0].T,
            origin="lower",
            extent=(0, nx * pas, 0, ny * pas),
            cmap=cmap,
            vmin=0.0,
            vmax=2 * self.seuil,
            interpolation="nearest",
            zorder=1,
        )
        self.contour = None
        self._pas = pas
        # Meme definition que la simulation : part de la plage SECHE devenue mouillee.
        from viscocrowd.model.carte import CartePiscine
        from viscocrowd.model.milieu import Milieu

        xs, ys = (np.arange(nx) + 0.5) * pas, (np.arange(ny) + 0.5) * pas
        centres = np.stack(np.meshgrid(xs, ys, indexing="ij"), axis=-1).reshape(-1, 2)
        self._sec = CartePiscine(self.p.piscine)(centres).reshape(nx, ny) == int(Milieu.SEC)
        self.afficher(self.index)

    def afficher(self, index: int) -> None:
        super().afficher(index)
        if not hasattr(self, "film"):
            return  # premier affichage du parent
        k = max(0, np.searchsorted(self.t_eau, self.donnees.t[self.index], side="right") - 1)
        eau = self.eau_sol[k]
        self.film.set_data(eau.T)
        if self.contour is not None:
            self.contour.remove()
            self.contour = None
        if np.any(eau >= self.seuil):
            nx, ny = eau.shape
            xs, ys = (np.arange(nx) + 0.5) * self._pas, (np.arange(ny) + 0.5) * self._pas
            self.contour = self.ax.contour(
                xs, ys, eau.T, levels=[self.seuil], colors="white", linewidths=0.7, zorder=2
            )
        mouille = np.sum(self._sec & (eau >= self.seuil)) / max(int(self._sec.sum()), 1)
        texte = self.compteur.get_text().split("  ·")[0]
        self.compteur.set_text(f"{texte}  ·  sol mouillé par la traînée : {100 * mouille:.1f} %")
        self.figure.canvas.draw_idle()


def ajouter_commande(sous) -> None:
    commande = sous.add_parser(
        "trainee",
        help="simule la piscine avec egouttage et montre la trainee d'eau sur la plage",
    )
    commande.add_argument(
        "configuration", type=Path, help="configuration YAML de la piscine, avec egouttage"
    )
    commande.add_argument("--gif", type=Path, help="export GIF hors ecran")
    commande.add_argument("--image", type=Path, help="export PNG hors ecran")
    commande.add_argument("--instant", type=float, default=0.0, help="instant du PNG, en s")
    commande.add_argument("--vitesse", type=float, default=4.0, help="facteur de lecture")
    commande.set_defaults(fonction=commande_trainee)


def commande_trainee(args) -> int:
    import matplotlib

    if args.gif or args.image:
        matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.backends import backend_registry

    from viscocrowd.io.configuration import lire_configuration
    from viscocrowd.io.trajectoires import Trajectoire
    from viscocrowd.scenarios.experience import _configuration_effective, _evenements_piscine
    from viscocrowd.scenarios.piscine import NOMS_ETATS, ParametresPiscine, simuler_piscine

    lecteur = None
    try:
        for chemin, extension in ((args.gif, ".gif"), (args.image, ".png")):
            if chemin and (chemin.exists() or chemin.suffix.lower() != extension):
                raise ValueError(f"choisir un nouveau fichier {extension} : {chemin}")
        configuration = lire_configuration(args.configuration)
        if configuration["scenario"] != "piscine":
            raise ValueError("la trainee attend une configuration piscine")
        p = ParametresPiscine(**configuration["parametres"], graine=configuration["graine"])
        if p.egouttage is None:
            raise ValueError("la configuration doit activer egouttage (volume, duree, seuil, pas)")
        r = simuler_piscine(p)
        r.projection.verifier_convergence()
        donnees = Trajectoire(
            r.t,
            r.x,
            r.v,
            r.rayons,
            {
                "configuration": _configuration_effective(configuration, p),
                "etats": list(NOMS_ETATS),
                "evenements": _evenements_piscine(r),
            },
            etats=r.etats,
        )
        lecteur = LecteurTrainee(
            donnees,
            r.eau_sol,
            r.t_eau,
            p.egouttage["pas"],
            p.egouttage["seuil"],
            interactif=not (args.gif or args.image),
            vitesse=args.vitesse,
        )
        print(
            f"t100 = {r.temps_evacuation(1.0):.2f} s ; plage mouillée par la traînée en fin "
            f"d'évacuation : {100 * r.fraction_mouillee[-1]:.1f} %"
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
        print(f"Trainee refusee : {erreur}", file=sys.stderr)
        return 1
    finally:
        if lecteur is not None:
            plt.close(lecteur.figure)
