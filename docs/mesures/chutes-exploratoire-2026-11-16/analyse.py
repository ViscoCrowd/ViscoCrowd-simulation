"""Campagne exploratoire des chutes (#130) : chutes par cause et test du pas de temps.

Relit les bilans de `viscocrowd balayer-piscine` de ce dossier, sans rien simuler :

    python docs/mesures/chutes-exploratoire-2026-11-16/analyse.py
"""

import itertools
import json
import math
import statistics as st
from pathlib import Path

DOSSIER = Path(__file__).parent
BALAYAGES = ("lambda_chute", "lambda_domino", "lambda_bousculade", "facteur_rayon_terre", "dt")
CAUSES = ("glissade", "domino", "bousculade")


def p_permutation(ecarts: list[float]) -> float:
    """Valeur p bilaterale exacte du test de permutation des signes (apparie)."""
    observe = abs(sum(ecarts))
    signes = itertools.product((1, -1), repeat=len(ecarts))
    extremes = [
        abs(sum(s * e for s, e in zip(t, ecarts, strict=True))) >= observe - 1e-9 for t in signes
    ]
    return sum(extremes) / len(extremes)


for nom in BALAYAGES:
    bilan = json.loads((DOSSIER / f"{nom}.json").read_text(encoding="utf-8"))
    colonnes = [bilan["mesures"].index(f"chutes_{c}") for c in CAUSES]
    print(f"== {nom} (commit {bilan['contexte']['code']['commit']})")
    for point in bilan["points"]:
        mouille = [st.mean(ligne[k] for ligne in point["mouille"]) for k in colonnes]
        temoin = [st.mean(ligne[k] for ligne in point["temoin"]) for k in colonnes]
        cellules = ", ".join(
            f"{c} {m:.1f}/{t:.1f}" for c, m, t in zip(CAUSES, mouille, temoin, strict=True)
        )
        print(f"  {point['valeur']:g} : chutes par evacuation, mouille/temoin : {cellules}")

    if nom == "dt":
        fin, gros = bilan["points"][1], bilan["points"][0]
        for libelle, retenues in (
            ("total", colonnes),
            ("glissade", colonnes[:1]),
            ("domino", colonnes[1:2]),
        ):
            avant = [sum(ligne[c] for c in retenues) for ligne in gros["mouille"]]
            apres = [sum(ligne[c] for c in retenues) for ligne in fin["mouille"]]
            ecarts = [b - a for a, b in zip(avant, apres, strict=True)]
            moyenne, ecart_type = st.mean(ecarts), st.stdev(ecarts)
            demi = 2.262 * ecart_type / math.sqrt(len(ecarts))  # t de Student, 9 ddl
            print(
                f"  dt/2 - dt, {libelle} : {moyenne:+.1f} ± {ecart_type:.1f} "
                f"(IC 95 % {moyenne - demi:+.1f} a {moyenne + demi:+.1f}), "
                f"{100 * moyenne / st.mean(avant):+.1f} %, p = {p_permutation(ecarts):.3f}"
            )
