"""Navigation locale (#158) sur l'anneau de M8 (#149) : vitesse selon la densite, contre Weidmann.

Configuration `experiments/anneau.yaml`, sans regulation de Tordeux (temps_espacement:
null), avec la navigation de Moussaid et al. (2011), valeurs de l'article. 40 s de
simulation, vitesse mesuree de 20 a 40 s. Neuf densites, graines 1 a 10.

Le premier bilan (17 novembre, graines 1 a 3) avait ete calcule sur une branche locale,
avant la fusion de #149. Ce script le relance depuis le depot : les graines 1 a 3 doivent
redonner les memes vitesses au bit pres (`tests/test_anneau.py`).

Usage : python docs/mesures/navigation-2026-11-17/anneau.py experiments/anneau.yaml
"""

import json
import sys
import time
from multiprocessing import Pool
from pathlib import Path

import numpy as np

from viscocrowd.io.configuration import lire_configuration
from viscocrowd.observables import weidmann
from viscocrowd.scenarios.anneau import parametres_anneau, simuler_anneau
from viscocrowd.scenarios.campagne import contexte

CONFIG = lire_configuration(Path(sys.argv[1]))
EFFECTIFS = (302, 264, 226, 188, 151, 113, 75, 38, 19)  # les plus longs d'abord
GRAINES = range(1, 11)


def mesurer(tache):
    n, graine = tache
    debut = time.perf_counter()
    p = parametres_anneau(
        CONFIG,
        n_agents=n,
        graine=graine,
        temps_espacement=None,
        navigation={},
        duree=40.0,
        debut_mesure=20.0,
    )
    r = simuler_anneau(p)
    return {
        "n": n,
        "graine": graine,
        "densite": p.densite,
        "vitesse": r.vitesse_moyenne,
        "derive": r.derive,
        "violation": max(r.violation_paroi_max, r.recouvrement_max),
        "weidmann": float(weidmann.vitesse(p.densite)),
        "calcul_s": time.perf_counter() - debut,
    }


if __name__ == "__main__":
    debut = time.perf_counter()
    taches = [(n, g) for n in EFFECTIFS for g in GRAINES]
    with Pool(20) as pool:
        resultats = pool.map(mesurer, taches, chunksize=1)
    sortie = Path(__file__).parent / "anneau.json"
    sortie.write_text(
        json.dumps({"contexte": contexte(), "resultats": resultats}, indent=1), encoding="utf-8"
    )
    for n in sorted(EFFECTIFS):
        lignes = [m for m in resultats if m["n"] == n]
        v = np.array([m["vitesse"] for m in lignes])
        print(
            f"rho={lignes[0]['densite']:.2f} v={v.mean():.3f}±{v.std(ddof=1):.3f}"
            f" Weidmann={lignes[0]['weidmann']:.3f}"
            f" derive_max={max(m['derive'] for m in lignes):.1%}"
            f" viol={max(m['violation'] for m in lignes):.1e}"
            f" calcul={np.mean([m['calcul_s'] for m in lignes]):.0f}s"
        )
    print(f"duree {(time.perf_counter() - debut) / 60:.0f} min")
