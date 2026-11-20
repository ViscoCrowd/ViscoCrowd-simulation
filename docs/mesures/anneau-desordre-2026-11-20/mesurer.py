"""#167 : sur l'anneau, la marche a v0 jusqu'a 2 pers/m^2 vient-elle du banc ou du modele ?

Question, ecrite avant le calcul. Sur l'anneau de #149, le modele marche a 1,340 m/s
jusqu'a 2 pers/m^2, sans dispersion sur 10 graines, alors que Weidmann (1993) perd 21 % de
vitesse a 1 pers/m^2. Les relectures de #149 l'attribuent au depart : quatre voies
concentriques espacees de 0,44 m, au-dessus du seuil de meneur, et des vitesses identiques,
si bien que personne ne rattrape personne. On casse cette symetrie de deux facons, puis des
deux a la fois.

Protocole : `experiments/anneau.yaml` (T = 0,35 s, v0 = 1,34 m/s), N = 38, 75, 113, 151 et
188 (0,5 a 2,5 pers/m^2), graines 1 a 10, fenetre [30 ; 60] s. Quatre variantes :
  - voies : le depart actuel (reference de #149) ;
  - desordonne : `depart: desordonne` ;
  - dispersee : depart en voies, `dispersion_vitesse: 0.26` (Weidmann 1993, p. 53) ;
  - desordonne_dispersee : les deux.

Criteres, fixes avant le calcul, a 1,0 et 1,5 pers/m^2 (N = 75 et 113) et pour chaque
variante :
  - « reste a v0 » si la vitesse moyenne vaut au moins 1,33 m/s (1 % sous v0) ;
  - « baisse » si elle est sous 1,30 m/s (3 % sous v0) sur au moins 9 graines sur 10.
Lecture (issue #167) : si le depart desordonne reste a v0, le modele n'anticipe pas, et
c'est une limite a ecrire ; s'il baisse, l'ecart de #149 venait du banc, et la conclusion
de `docs/diagramme-fondamental.md` est a corriger. La vitesse dispersee se lit de la meme
facon. Les variantes avec dispersion ont une vitesse moyenne souhaitee legerement differente
de 1,34 m/s (loi bornee, tirage fini) : on la donne a cote.

Le script trace aussi v(rho) et J(rho) avec Weidmann, et l'histogramme des distances au
centre au regime etabli a N = 113 (les voies se reforment-elles ?).

Usage, depuis la racine du depot (arbre propre) :
    python docs/mesures/anneau-desordre-2026-11-20/mesurer.py experiments/anneau.yaml \
        docs/mesures/anneau-desordre-2026-11-20
"""

import json
import sys
from multiprocessing import Pool
from pathlib import Path

import numpy as np

from viscocrowd.io.configuration import lire_configuration
from viscocrowd.observables import weidmann
from viscocrowd.scenarios.anneau import parametres_anneau, simuler_anneau, vitesses_individuelles
from viscocrowd.scenarios.campagne import contexte

EFFECTIFS = (38, 75, 113, 151, 188)
GRAINES = tuple(range(1, 11))
VARIANTES = {
    "voies": {},
    "desordonne": {"depart": "desordonne"},
    "dispersee": {"dispersion_vitesse": 0.26},
    "desordonne_dispersee": {"depart": "desordonne", "dispersion_vitesse": 0.26},
}
EFFECTIF_HISTOGRAMME = 113


def simuler(cas):
    variante, n, graine = cas
    p = parametres_anneau(
        lire_configuration(Path(sys.argv[1])), n_agents=n, graine=graine, **VARIANTES[variante]
    )
    r = simuler_anneau(p)
    return (
        variante,
        n,
        graine,
        {
            "vitesse": r.vitesse_moyenne,
            "vitesse_souhaitee_moyenne": float(vitesses_individuelles(p).mean()),
            "derive": r.derive,
            "violation": max(r.violation_paroi_max, r.recouvrement_max),
            "distances_centre": (
                np.round(r.distances_centre, 4).ravel().tolist()
                if n == EFFECTIF_HISTOGRAMME
                else None
            ),
        },
    )


def figures(bilan: dict, dossier: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    rho_w = np.linspace(0.3, 2.7, 100)
    fig, (ax_v, ax_j) = plt.subplots(1, 2, figsize=(11, 4.2))
    ax_v.plot(rho_w, weidmann.vitesse(rho_w), "k--", label="Weidmann (1993)")
    ax_j.plot(rho_w, weidmann.debit_specifique(rho_w), "k--", label="Weidmann (1993)")
    for variante, points in bilan["points"].items():
        rho = np.array([pt["densite"] for pt in points])
        v = np.array([pt["vitesse_moyenne"] for pt in points])
        ev = np.array([pt["vitesse_ecart_type"] for pt in points])
        ax_v.errorbar(rho, v, yerr=ev, marker="o", capsize=3, label=variante)
        ax_j.errorbar(rho, rho * v, yerr=rho * ev, marker="o", capsize=3, label=variante)
    ax_v.set_xlabel("densité (pers/m²)")
    ax_v.set_ylabel("vitesse v (m/s)")
    ax_j.set_xlabel("densité (pers/m²)")
    ax_j.set_ylabel("débit spécifique J (pers/(m·s))")
    ax_v.legend(fontsize=8)
    fig.suptitle("Anneau, graines 1 à 10 : départ et dispersion des vitesses (#167)")
    fig.tight_layout()
    fig.savefig(dossier / "diagramme.png", dpi=130)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(7, 4))
    bornes = np.linspace(5.0, 7.0, 81)
    for variante, distances in bilan["histogramme"].items():
        ax.hist(distances, bins=bornes, histtype="step", density=True, label=variante)
    ax.set_xlabel("distance au centre (m)")
    ax.set_ylabel("densité de probabilité (1/m)")
    ax.set_title(f"N = {EFFECTIF_HISTOGRAMME}, régime établi (une fois par seconde, 10 graines)")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(dossier / "voies.png", dpi=130)
    plt.close(fig)


if __name__ == "__main__":
    dossier = Path(sys.argv[2])
    sortie = dossier / "anneau-desordre.json"
    if sortie.exists():
        raise SystemExit(f"{sortie} existe deja")
    ctx = contexte()
    cas = [(v, n, g) for v in VARIANTES for n in EFFECTIFS for g in GRAINES]
    with Pool(32) as pool:
        resultats = pool.map(simuler, cas)
    mesures = {(v, n, g): m for v, n, g, m in resultats}
    aire = parametres_anneau(lire_configuration(Path(sys.argv[1]))).anneau.aire

    bilan = {"version": 1, "contexte": ctx, "graines": GRAINES, "points": {}, "histogramme": {}}
    print("variante | N | rho | v (m/s) | v0 moyen | v < 1,30 | derive max | violation")
    for v in VARIANTES:
        bilan["points"][v] = []
        for n in EFFECTIFS:
            serie = [mesures[(v, n, g)] for g in GRAINES]
            vit = np.array([m["vitesse"] for m in serie])
            v0 = np.mean([m["vitesse_souhaitee_moyenne"] for m in serie])
            sous = int(np.sum(vit < 1.30))
            point = {
                "n_agents": n,
                "densite": n / aire,
                "vitesses": vit.tolist(),
                "vitesse_moyenne": float(vit.mean()),
                "vitesse_ecart_type": float(vit.std(ddof=1)),
                "vitesse_souhaitee_moyenne": float(v0),
                "graines_sous_1_30": sous,
                "derive_max": max(m["derive"] for m in serie),
                "violation_max": max(m["violation"] for m in serie),
                "vitesse_weidmann": float(weidmann.vitesse(n / aire)),
            }
            bilan["points"][v].append(point)
            print(
                f"  {v:20s} | {n:3d} | {n / aire:.2f} | {vit.mean():.3f} ± {vit.std(ddof=1):.3f}"
                f" | {v0:.3f} | {sous}/10 | {point['derive_max']:.1%}"
                f" | {point['violation_max']:.1e}"
            )
        bilan["histogramme"][v] = [
            d for g in GRAINES for d in mesures[(v, EFFECTIF_HISTOGRAMME, g)]["distances_centre"]
        ]

    print("Criteres a 1,0 et 1,5 pers/m^2 (N = 75 et 113) :")
    verdicts = {}
    for v in VARIANTES:
        for pt in bilan["points"][v]:
            if pt["n_agents"] in (75, 113):
                if pt["vitesse_moyenne"] >= 1.33:
                    verdict = "reste a v0"
                elif pt["graines_sous_1_30"] >= 9:
                    verdict = "baisse"
                else:
                    verdict = "entre les deux"
                verdicts[f"{v}/{pt['n_agents']}"] = verdict
                print(f"  {v:20s} N = {pt['n_agents']} : {verdict}")
    bilan["verdicts"] = verdicts
    sortie.write_text(json.dumps(bilan, ensure_ascii=False) + "\n", encoding="utf-8")
    figures(bilan, dossier)
    print(f"Bilan : {sortie} ; figures : diagramme.png, voies.png")
