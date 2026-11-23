"""Commande `bouchons` : distribution des intervalles entre sorties, par etiquette.

    viscocrowd bouchons A.npz B.npz ... --etiquettes E1 E2 ... --image X.png [--seuil 1]

Les archives d'une meme etiquette (des graines differentes) sont regroupees : leurs
intervalles forment une seule distribution. La figure trace P(Delta > tau) en echelle
log-log, une courbe par etiquette ; la console donne, par etiquette, le nombre
d'intervalles, leur mediane, P(Delta > seuil), le plus long, et le nombre d'evacuations
incompletes (jamais retirees en silence : voir `observables.bouchage`).
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

from viscocrowd.observables.bouchage import intervalles_sorties, resumer, survie


def sorties_archivees(chemin: Path) -> np.ndarray:
    """Instants de sortie (s) d'une archive piscine ; NaN pour un agent jamais sorti."""
    from viscocrowd.io.trajectoires import lire_trajectoire

    evenements = lire_trajectoire(chemin).metadonnees.get("evenements")
    if not evenements or "sorties" not in evenements:
        raise ValueError(f"{chemin} : archive sans instants de sortie (scenario piscine attendu)")
    return np.array([np.nan if s is None else s for s in evenements["sorties"]], dtype=float)


def points_survie(intervalles: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Points (tau, P(Delta > tau)) a tracer en echelle log : ceux ou P > 0.

    Au plus long intervalle, P vaut 0 et n'a pas de place sur un axe logarithmique :
    on s'arrete donc a l'avant-dernier intervalle distinct, et la legende le dit.
    """
    taus = np.sort(np.asarray(intervalles, dtype=float))
    p = survie(taus, taus)
    garder = p > 0
    return taus[garder], p[garder]


def ajouter_commande(sous) -> None:
    commande = sous.add_parser(
        "bouchons", help="distribution des intervalles entre sorties (duree des bouchons)"
    )
    commande.add_argument("archives", nargs="+", type=Path, help="archives .npz de la piscine")
    commande.add_argument(
        "--etiquettes", nargs="+", required=True, help="une etiquette par archive (regroupe)"
    )
    commande.add_argument("--image", type=Path, required=True, help="figure PNG a creer")
    commande.add_argument(
        "--seuil", type=float, default=1.0, help="intervalle compte comme bouchon, en s"
    )
    commande.set_defaults(fonction=commande_bouchons)


def commande_bouchons(args) -> int:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    try:
        if len(args.etiquettes) != len(args.archives):
            raise ValueError("il faut exactement une etiquette par archive")
        if args.image.exists() or args.image.suffix.lower() != ".png":
            raise ValueError(f"choisir un nouveau fichier .png : {args.image}")
        groupes: dict[str, list[np.ndarray]] = {}
        for chemin, etiquette in zip(args.archives, args.etiquettes, strict=True):
            groupes.setdefault(etiquette, []).append(sorties_archivees(chemin))

        figure, ax = plt.subplots(figsize=(7, 5))
        for etiquette, liste in groupes.items():
            intervalles = np.concatenate([intervalles_sorties(s) for s in liste])
            bilans = [resumer(s, args.seuil) for s in liste]
            incompletes = sum(b["incomplete"] for b in bilans)
            if intervalles.size:
                seuil = survie(intervalles, np.array([args.seuil]))[0]
                print(
                    f"{etiquette} : {intervalles.size} intervalles, mediane "
                    f"{np.median(intervalles):.3f} s, P(Delta > {args.seuil:g} s) = {seuil:.3f}, "
                    f"plus long {intervalles.max():.2f} s ; "
                    f"{incompletes} évacuation(s) incomplète(s) sur {len(liste)}"
                )
                taus, p = points_survie(intervalles)
                ax.step(taus, p, where="post", label=etiquette)
            else:
                print(
                    f"{etiquette} : aucun intervalle ; "
                    f"{incompletes} évacuation(s) incomplète(s) sur {len(liste)}"
                )
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.axvline(args.seuil, color="0.6", lw=1, ls="--")
        ax.set_xlabel("intervalle entre deux sorties τ (s)")
        ax.set_ylabel("P(Δ > τ)")
        ax.set_title("Intervalles entre sorties successives")
        figure.subplots_adjust(bottom=0.16)  # place pour la note sous l'axe
        figure.text(
            0.01,
            0.015,
            "Le plus long intervalle (P = 0) n'a pas de place en échelle log : non tracé.",
            fontsize=8,
            color="0.4",
        )
        if ax.get_legend_handles_labels()[0]:
            ax.legend()
        args.image.parent.mkdir(parents=True, exist_ok=True)
        figure.savefig(args.image, dpi=140)
        plt.close(figure)
        print(f"Figure : {args.image}")
        return 0
    except (OSError, ValueError) as erreur:
        print(f"Bouchons refuses : {erreur}", file=sys.stderr)
        return 1
