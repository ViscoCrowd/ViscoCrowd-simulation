"""Duel : deux evacuations de piscine rejouees l'une au-dessus de l'autre, en un GIF.

Le cas d'usage est la problematique en une animation : la meme foule, partie des
memes positions (meme graine), evacue la piscine mouillee en haut et le temoin
tout sec en bas. Les deux horloges avancent ensemble ; quand une evacuation est
finie, sa vue reste figee sur son dernier instant, compteur a N / N.

Le temoin est celui des balayages (`balayage_piscine.temoin`) : bande mouillee de
largeur nulle et carrelage mouille aux valeurs du sec, chutes eventuelles
inchangees. `--contre` remplace le temoin par n'importe quelle autre
configuration piscine.

Les deux simulations passent par `executer_configuration`, avec ses controles
(convergence, parois, provenance), dans un repertoire temporaire ; `--garder`
conserve les deux archives. Chaque vue est une `LecteurPiscine`, sans changement :
le GIF montre exactement ce que montre la relecture.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import numpy as np
import yaml


def instants_communs(fin_a: float, fin_b: float, fps: int, vitesse: float) -> np.ndarray:
    """Instants simules de chaque image, de 0 a la plus longue des deux evacuations."""
    if type(fps) is not int or fps < 1 or not np.isfinite(vitesse) or vitesse <= 0:
        raise ValueError("fps et vitesse doivent etre strictement positifs")
    fin = max(fin_a, fin_b)
    return np.append(np.arange(0.0, fin, vitesse / fps), fin)


def exporter_duel(donnees, titres, chemin: Path, *, fps: int = 15, vitesse: float = 4.0, dpi=60):
    """Ecrit le GIF des deux archives piscine `donnees`, empilees, avec leurs `titres`.

    Returns:
        Le nombre d'images du GIF.
    """
    import matplotlib.pyplot as plt
    from PIL import Image

    from viscocrowd.ui.relecture_piscine import LecteurPiscine

    if len(donnees) != 2 or len(titres) != 2:
        raise ValueError("un duel compare exactement deux archives")
    lecteurs = [LecteurPiscine(d, interactif=False) for d in donnees]
    try:
        for lecteur, titre in zip(lecteurs, titres, strict=True):
            lecteur.figure.set_dpi(dpi)
            lecteur.figure.texts[1].set_text(titre.upper())
            # Le style global peut avoir ete change par un module de figures importe
            # entre-temps (grille) : la vue doit rester celle de la relecture.
            lecteur.ax.grid(False)
        instants = instants_communs(
            donnees[0].t[-1] - donnees[0].t[0], donnees[1].t[-1] - donnees[1].t[0], fps, vitesse
        )

        def image(t: float) -> Image.Image:
            vues = []
            for lecteur in lecteurs:
                debut, fin = lecteur.donnees.t[0], lecteur.donnees.t[-1]
                lecteur.aller_au_temps(min(debut + t, fin))
                lecteur.figure.canvas.draw()
                vue = np.asarray(lecteur.figure.canvas.buffer_rgba())[..., :3]
                # Le bas de la figure (sous la legende, 12 %) est vide hors lecture interactive.
                vues.append(vue[: round(0.88 * vue.shape[0])])
            return Image.fromarray(np.concatenate(vues, axis=0)).quantize(colors=128)

        # Generateur : seule l'image en cours est en memoire, pas les centaines du film.
        premiere = image(instants[0])
        premiere.save(
            chemin,
            save_all=True,
            append_images=(image(t) for t in instants[1:]),
            duration=round(1000 / fps),
            loop=0,
            optimize=False,
        )
        return len(instants)
    finally:
        for lecteur in lecteurs:
            plt.close(lecteur.figure)


def configuration_temoin(configuration: dict) -> dict:
    """La meme configuration piscine, sol entierement sec (temoin des balayages)."""
    from viscocrowd.scenarios.balayage_piscine import temoin

    if configuration.get("scenario") != "piscine":
        raise ValueError("le duel attend une configuration piscine")
    return configuration | {"parametres": temoin(configuration["parametres"])}


def ajouter_commande(sous) -> None:
    commande = sous.add_parser(
        "duel",
        help="GIF de deux evacuations de piscine empilees (defaut : mouillee contre temoin sec)",
    )
    commande.add_argument("configuration", type=Path, help="configuration YAML de la piscine")
    commande.add_argument("--gif", type=Path, required=True, help="GIF a creer")
    commande.add_argument(
        "--contre", type=Path, help="seconde configuration piscine (defaut : temoin tout sec)"
    )
    commande.add_argument("--titres", nargs=2, metavar=("HAUT", "BAS"), help="titre de chaque vue")
    commande.add_argument(
        "--vitesse", type=float, default=4.0, help="facteur de lecture (defaut : 4)"
    )
    commande.add_argument("--garder", type=Path, help="repertoire ou conserver les deux archives")
    commande.set_defaults(fonction=commande_duel)


def commande_duel(args) -> int:
    import matplotlib

    matplotlib.use("Agg")

    from viscocrowd.io.configuration import lire_configuration
    from viscocrowd.scenarios.experience import executer_configuration

    try:
        if args.gif.exists() or args.gif.suffix.lower() != ".gif":
            raise ValueError(f"choisir un nouveau fichier .gif : {args.gif}")
        haut = lire_configuration(args.configuration)
        if haut["scenario"] != "piscine":
            raise ValueError("le duel attend une configuration piscine")
        if args.contre is not None:
            bas = lire_configuration(args.contre)
            if bas["scenario"] != "piscine":
                raise ValueError("le duel attend une configuration piscine")
            titres = args.titres or [args.configuration.stem, args.contre.stem]
        else:
            bas = configuration_temoin(haut)
            titres = args.titres or ["Carrelage mouillé", "Témoin : tout sec"]
        if args.garder is not None:
            for nom in ("haut.npz", "bas.npz"):
                if (args.garder / nom).exists():
                    raise ValueError(f"{args.garder / nom} existe deja")
        with tempfile.TemporaryDirectory() as dossier:
            dossier = Path(dossier)
            destination = args.garder or dossier
            destination.mkdir(parents=True, exist_ok=True)
            donnees = []
            for nom, configuration in (("haut", haut), ("bas", bas)):
                yaml_vue = dossier / f"{nom}.yaml"
                yaml_vue.write_text(yaml.safe_dump(configuration, allow_unicode=True))
                donnees.append(executer_configuration(yaml_vue, destination / f"{nom}.npz"))
                print(f"{titres[len(donnees) - 1]} : t_final = {donnees[-1].t[-1]:.2f} s")
            args.gif.parent.mkdir(parents=True, exist_ok=True)
            images = exporter_duel(donnees, titres, args.gif, vitesse=args.vitesse)
        print(f"Animation : {args.gif} ({images} images)")
        return 0
    except (OSError, ValueError) as erreur:
        print(f"Duel refuse : {erreur}", file=sys.stderr)
        return 1
