"""Navigation (#158) sur E0 : un temps d'anticipation tau permet-il d'atteindre Seyfried ?

Meme protocole que docs/mesures/navigation-2026-11-17/e0.py (goulot.yaml, sans regulation
T, navigation avec les valeurs de l'article), tau de la seconde heuristique balaye. Comme
pour T : on choisit tau sur N = 60, et le critere des criteres d'acceptation (§ 4, ecart
moyen absolu de J_s <= 10 % sur 10 graines) se juge sur N = 40 et N = 20.

Usage, depuis la racine du depot (arguments : configuration, puis bilan JSON) :

    python docs/mesures/navigation-2026-11-19/e0-tau.py experiments/goulot.yaml
        docs/mesures/navigation-2026-11-19/e0-tau.json

Lance le 19 novembre depuis le commit 275fc3d, alors hors du depot ; seules cette notice
et la mise en forme ruff ont change depuis.
"""

import json
import sys
import time
from multiprocessing import Pool
from pathlib import Path

import numpy as np

from viscocrowd.io.configuration import lire_configuration
from viscocrowd.scenarios.campagne import contexte
from viscocrowd.scenarios.goulot import parametres_goulot, reference_seyfried, simuler_goulot

CONFIG = lire_configuration(Path(sys.argv[1]))
TAUS = (0.15, 0.20, 0.25, 0.30)
EFFECTIFS = (60, 40, 20)
LARGEURS = (0.8, 0.9, 1.0, 1.1, 1.2)
GRAINES = range(1, 11)


def mesurer(tache):
    tau, n, b, graine = tache
    debut = time.perf_counter()
    p = parametres_goulot(
        CONFIG | {"graine": graine},
        n_agents=n,
        largeur_goulot=b,
        temps_espacement=None,
        navigation={"temps_anticipation": tau},
    )
    r = simuler_goulot(p)
    return {
        "tau": tau,
        "n": n,
        "b": b,
        "graine": graine,
        "statut": r.statut,
        "debit": r.debit_specifique if r.statut == "ecoulement" else None,
        "violation": r.violation_paroi_max(),
        "calcul_s": time.perf_counter() - debut,
    }


if __name__ == "__main__":
    debut = time.perf_counter()
    taches = [(t, n, b, g) for t in TAUS for n in EFFECTIFS for b in LARGEURS for g in GRAINES]
    with Pool(20) as pool:
        resultats = pool.map(mesurer, taches, chunksize=1)
    Path(sys.argv[2]).write_text(
        json.dumps({"contexte": contexte(), "resultats": resultats}, indent=1), encoding="utf-8"
    )
    for t in TAUS:
        print(f"tau = {t} s")
        for n in EFFECTIFS:
            ecarts, bouches = [], 0
            for b in LARGEURS:
                lot = [m for m in resultats if (m["tau"], m["n"], m["b"]) == (t, n, b)]
                ok = [m["debit"] for m in lot if m["debit"] is not None]
                bouches += len(lot) - len(ok)
                if ok:
                    ecarts.append(np.mean(ok) / reference_seyfried(n, b) - 1)
            print(
                f"  N={n}: ecart moyen absolu {np.mean(np.abs(ecarts)):.1%},"
                f" ecarts {', '.join(f'{e:+.0%}' for e in ecarts)}, non-ecoulements {bouches}/50"
            )
    print(f"duree {(time.perf_counter() - debut) / 60:.0f} min")
