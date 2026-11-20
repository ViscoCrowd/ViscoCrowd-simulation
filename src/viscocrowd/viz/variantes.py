"""Commande `comparer-variantes` : 2 a 4 variantes d'une meme piscine, dans un seul GIF.

    viscocrowd comparer-variantes CONFIG --gif X.gif \\
        --variante adherence_mouille=3.3 --variante adherence_mouille=2 \\
        --variante adherence_mouille=1 [--vitesse 4] [--garder DOSSIER]

Chaque `--variante` est une liste de surcharges `NOM=VALEUR` (noms de `balayer-piscine`),
appliquees a la configuration par `appliquer_fixes` : meme graine, memes positions de
depart, seule la surcharge change. Chaque calcul passe par `executer_configuration`
(convergence, parois, provenance), et les vues sont celles de la relecture, horloges
synchronisees (`viz.duel.exporter_comparaison`). Le titre d'une vue est sa surcharge.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import yaml


def ajouter_commande(sous) -> None:
    commande = sous.add_parser(
        "comparer-variantes",
        help="GIF de 2 a 4 variantes d'une piscine (ex. adherence_mouille=3.3, 2 et 1)",
    )
    commande.add_argument("configuration", type=Path, help="configuration YAML de la piscine")
    commande.add_argument("--gif", type=Path, required=True, help="GIF a creer")
    commande.add_argument(
        "--variante",
        action="append",
        nargs="+",
        required=True,
        metavar="NOM=VALEUR",
        help="surcharges d'une vue ; option a repeter, de 2 a 4 fois",
    )
    commande.add_argument("--vitesse", type=float, default=4.0, help="facteur de lecture")
    commande.add_argument("--garder", type=Path, help="repertoire ou conserver les archives")
    commande.set_defaults(fonction=commande_variantes)


def commande_variantes(args) -> int:
    import matplotlib

    matplotlib.use("Agg")

    from viscocrowd.io.configuration import lire_configuration
    from viscocrowd.scenarios.balayage_piscine import appliquer_fixes, lire_fixes
    from viscocrowd.scenarios.experience import executer_configuration
    from viscocrowd.viz.duel import exporter_comparaison

    try:
        if not 2 <= len(args.variante) <= 4:
            raise ValueError("comparer 2 a 4 variantes (--variante a repeter)")
        if args.gif.exists() or args.gif.suffix.lower() != ".gif":
            raise ValueError(f"choisir un nouveau fichier .gif : {args.gif}")
        base = lire_configuration(args.configuration)
        if base["scenario"] != "piscine":
            raise ValueError("comparer-variantes attend une configuration piscine")
        configurations = [
            base | {"parametres": appliquer_fixes(base["parametres"], lire_fixes(variante))}
            for variante in args.variante
        ]
        titres = [" ".join(variante) for variante in args.variante]
        with tempfile.TemporaryDirectory() as dossier:
            dossier = Path(dossier)
            destination = args.garder or dossier
            destination.mkdir(parents=True, exist_ok=True)
            donnees = []
            for k, (configuration, titre) in enumerate(zip(configurations, titres, strict=True)):
                archive = destination / f"variante-{k + 1}.npz"
                if archive.exists():
                    raise ValueError(f"{archive} existe deja")
                yaml_vue = dossier / f"variante-{k + 1}.yaml"
                yaml_vue.write_text(yaml.safe_dump(configuration, allow_unicode=True))
                donnees.append(executer_configuration(yaml_vue, archive))
                print(f"{titre} : t_final = {donnees[-1].t[-1]:.2f} s")
            args.gif.parent.mkdir(parents=True, exist_ok=True)
            images = exporter_comparaison(donnees, titres, args.gif, vitesse=args.vitesse)
        print(f"Animation : {args.gif} ({images} images)")
        return 0
    except (OSError, ValueError) as erreur:
        print(f"Comparaison refusee : {erreur}", file=sys.stderr)
        return 1
