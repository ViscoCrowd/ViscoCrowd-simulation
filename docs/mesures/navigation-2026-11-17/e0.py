"""Navigation locale (#158) sur le banc E0 : debit au goulot, compare a Seyfried et al.

Configuration de reference `experiments/goulot.yaml`, sans regulation de Tordeux
(temps_espacement: null), avec la navigation de Moussaid et al. (2011) :

  - article : valeurs de l'article, tau = 0,5 s pour la seconde heuristique ;
  - tau_035 : la meme, temps d'anticipation 0,35 s, la valeur de T etalonnee pour E0.

Graines 1 a 10, N = 20, 40 et 60, largeurs 0,8 a 1,2 m. Regime de chaque simulation
(ecoulement, bouchage...) et debit specifique J_s, estimateur de la publication.

Usage : python docs/mesures/navigation-2026-11-17/e0.py experiments/goulot.yaml
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
VARIANTES = {"article": {}, "tau_035": {"temps_anticipation": 0.35}}
EFFECTIFS = (20, 40, 60)
LARGEURS = (0.8, 0.9, 1.0, 1.1, 1.2)
GRAINES = range(1, 11)


def mesurer(tache):
    variante, n, b, graine = tache
    debut = time.perf_counter()
    p = parametres_goulot(
        CONFIG | {"graine": graine},
        n_agents=n,
        largeur_goulot=b,
        temps_espacement=None,
        navigation=VARIANTES[variante],
    )
    r = simuler_goulot(p)
    return {
        "variante": variante,
        "n": n,
        "b": b,
        "graine": graine,
        "statut": r.statut,
        "debit": r.debit_specifique if r.statut == "ecoulement" else None,
        "violation": r.violation_paroi_max(),
        "calcul_s": time.perf_counter() - debut,
    }


if __name__ == "__main__":
    taches = [(v, n, b, g) for v in VARIANTES for n in EFFECTIFS for b in LARGEURS for g in GRAINES]
    # Les plus longues d'abord : la file de travail se vide plus regulierement.
    taches.sort(key=lambda t: -t[1])
    with Pool(12) as pool:
        resultats = pool.map(mesurer, taches)
    sortie = Path(__file__).parent / "e0.json"
    sortie.write_text(
        json.dumps({"contexte": contexte(), "resultats": resultats}, indent=1), encoding="utf-8"
    )
    for v in VARIANTES:
        print(f"Variante {v}")
        for n in EFFECTIFS:
            for b in LARGEURS:
                lot = [m for m in resultats if (m["variante"], m["n"], m["b"]) == (v, n, b)]
                ok = [m["debit"] for m in lot if m["debit"] is not None]
                j = f"{np.mean(ok):.2f} +- {np.std(ok, ddof=1):.2f}" if len(ok) > 1 else "-"
                print(
                    f"  N={n} b={b:.1f} ecoulements {len(ok)}/{len(lot)} J_s {j}"
                    f" Seyfried {reference_seyfried(n, b):.2f}"
                )
