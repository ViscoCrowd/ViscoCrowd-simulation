"""Figure « faster-is-slower » : temps d'evacuation selon le niveau de panique.

Lit un ou plusieurs bilans JSON de `viscocrowd balayer-piscine --parametre
facteur_vitesse` et trace t100 (moyenne et ecart-type sur les graines) contre le
facteur de panique, pour la piscine mouillee (trait plein) et son temoin sec
(tirets). L'effet *faster-is-slower* serait une courbe qui remonte : au-dela d'une
certaine panique, aller plus vite ferait sortir plus tard. Aucune simulation n'est
relancee : la figure ne fait que relire les mesures archivees.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np


def series_t100(
    bilan: dict,
) -> tuple[np.ndarray, dict[str, tuple[np.ndarray, np.ndarray, np.ndarray]]]:
    """Facteurs (V,) et, par sol : moyenne et ecart-type de t100 (V,) en s, bouches (V,).

    Une evacuation bouchee n'a pas de t100 (null dans le bilan) : la moyenne ne porte
    que sur les evacuations TERMINEES, et le nombre de graines bouchees est rendu a
    part, pour etre affiche a cote du point. NaN si aucune n'est terminee.

    Raises:
        ValueError: si le bilan ne balaie pas facteur_vitesse ou s'il manque t100.
    """
    if bilan.get("parametre") != "facteur_vitesse":
        raise ValueError("le bilan doit balayer facteur_vitesse")
    try:
        k = bilan["mesures"].index("t100")
        points = bilan["points"]
    except (KeyError, ValueError) as erreur:
        raise ValueError("bilan sans mesure t100") from erreur
    facteurs = np.array([p["valeur"] for p in points], dtype=float)
    resultat = {}
    for sol in ("mouille", "temoin"):
        t100 = np.array(
            [[np.nan if ligne[k] is None else ligne[k] for ligne in p[sol]] for p in points],
            dtype=float,
        )
        finis = np.isfinite(t100)
        n = finis.sum(axis=1)
        somme = np.where(finis, t100, 0.0).sum(axis=1)
        moyenne = np.where(n > 0, somme / np.maximum(n, 1), np.nan)
        ecart = np.sqrt(
            np.where(finis, (t100 - moyenne[:, None]) ** 2, 0.0).sum(axis=1) / np.maximum(n, 1)
        )
        resultat[sol] = (moyenne, np.where(n > 0, ecart, np.nan), (~finis).sum(axis=1))
    ordre = np.argsort(facteurs)
    return facteurs[ordre], {s: tuple(v[ordre] for v in t) for s, t in resultat.items()}


def fusionner(bilans: list[dict]) -> dict:
    """Un seul bilan a partir de bilans d'une meme campagne, decoupee par valeur.

    Les points sont concatenes ; graines, mesures, parametre et parametres fixes
    doivent etre identiques, et une valeur ne peut pas apparaitre deux fois.
    """
    premier = bilans[0]
    for b in bilans[1:]:
        for cle in ("parametre", "mesures", "graines", "fixes"):
            if b.get(cle) != premier.get(cle):
                raise ValueError(f"bilans incompatibles : {cle} differe")
    points = [p for b in bilans for p in b["points"]]
    valeurs = [p["valeur"] for p in points]
    if len(set(valeurs)) != len(valeurs):
        raise ValueError("une valeur du parametre apparait dans deux bilans")
    return premier | {"points": points}


def figure_panique(bilans: list[dict], etiquettes: list[str], chemin: Path) -> Path:
    """Trace t100 contre le facteur de panique pour chaque bilan ; rend le chemin.

    Les bilans qui portent la meme etiquette sont fusionnes en une courbe.
    """
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    import viscocrowd.viz.figures  # noqa: F401 - style commun des figures du rapport

    if len(bilans) != len(etiquettes) or not bilans:
        raise ValueError("une etiquette par bilan")
    groupes: dict[str, list[dict]] = {}
    for bilan, etiquette in zip(bilans, etiquettes, strict=True):
        groupes.setdefault(etiquette, []).append(bilan)
    etiquettes = list(groupes)
    bilans = [fusionner(groupe) for groupe in groupes.values()]
    fig, ax = plt.subplots(figsize=(7, 4))
    couleurs = ("#1f6f8b", "#d1495b", "#2e933c", "#7b4b94")
    for bilan, etiquette, couleur in zip(bilans, etiquettes, couleurs, strict=False):
        facteurs, series = series_t100(bilan)
        for sol, style, nom in (("mouille", "-", "mouillé"), ("temoin", "--", "témoin sec")):
            moyenne, ecart, bouches = series[sol]
            ax.errorbar(
                facteurs,
                moyenne,
                yerr=ecart,
                fmt="o" + style,
                color=couleur,
                capsize=3,
                markersize=4,
                alpha=1.0 if sol == "mouille" else 0.6,
                label=f"{etiquette}, {nom}",
            )
            # Les graines bouchees n'entrent pas dans la moyenne : on le dit sur le point.
            haut = np.nanmax(moyenne) if np.any(np.isfinite(moyenne)) else 0.0
            for f, m, b in zip(facteurs, moyenne, bouches, strict=True):
                if b:
                    ax.annotate(
                        f"{b} bouchée{'s' if b > 1 else ''}",
                        (f, m if np.isfinite(m) else haut),
                        textcoords="offset points",
                        xytext=(4, 6 if sol == "mouille" else -12),
                        fontsize=7,
                        color=couleur,
                    )
    fixes = bilans[0].get("fixes", {})
    precision = ", ".join(f"{k} = {v:g}" for k, v in fixes.items() if k != "dt")
    ax.set_xlabel("facteur de panique (multiplie les vitesses souhaitées)")
    ax.set_ylabel("t100 : sortie du dernier baigneur (s)")
    ax.set_title(
        f"Temps d'évacuation selon la panique ({precision} ; "
        f"{len(bilans[0]['graines'])} graines ; moyenne ± écart-type des évacuations terminées)",
        fontsize=9,
    )
    ax.legend(fontsize=8)
    chemin.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(chemin)
    plt.close(fig)
    return chemin


def ajouter_commande(sous) -> None:
    commande = sous.add_parser(
        "figure-panique", help="t100 selon la panique, depuis des bilans de balayer-piscine"
    )
    commande.add_argument("bilans", type=Path, nargs="+", help="bilans JSON (facteur_vitesse)")
    commande.add_argument(
        "--etiquettes", nargs="+", help="une etiquette par bilan ; meme etiquette : fusion"
    )
    commande.add_argument("--image", type=Path, required=True, help="PNG a creer")
    commande.set_defaults(fonction=commande_figure_panique)


def commande_figure_panique(args) -> int:
    try:
        if args.image.exists() or args.image.suffix.lower() != ".png":
            raise ValueError(f"choisir un nouveau fichier .png : {args.image}")
        bilans = [json.loads(chemin.read_text()) for chemin in args.bilans]
        etiquettes = args.etiquettes or [chemin.stem for chemin in args.bilans]
        print(f"Figure : {figure_panique(bilans, etiquettes, args.image)}")
        return 0
    except (OSError, ValueError) as erreur:
        print(f"Figure refusee : {erreur}", file=sys.stderr)
        return 1
