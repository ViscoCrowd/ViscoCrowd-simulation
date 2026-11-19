"""Pourquoi la navigation va-t-elle trop vite sur l'anneau au-dela de 1,5 pers/m2 ?

Deux pistes, chacune changee seule par rapport au bilan de anneau.py (r = 0,2 m,
tau = 0,5 s, graines 1 a 3 identiques) :

  - rayon_023 : disques de 0,23 m, le rayon dont l'empilement compact donne la densite
    d'arret de Weidmann (5,4 pers/m2) au lieu de 7,2 ;
  - tau_07 : temps d'anticipation de la seconde heuristique porte a 0,7 s.

Usage, depuis la racine du depot :

    python docs/mesures/navigation-2026-11-17/diagnostic-weidmann.py \
        experiments/anneau.yaml docs/mesures/navigation-2026-11-17/diagnostic-weidmann.json

Mesure du 19 novembre lancee depuis le commit 5aa0ed1, avec ce meme script, alors hors
du depot (seules cette notice et la mise en forme ruff ont change) ; la sortie console est
dans diagnostic-weidmann.txt.
"""

import json
import sys
import time
from multiprocessing import Pool
from pathlib import Path

from viscocrowd.io.configuration import lire_configuration
from viscocrowd.observables import weidmann
from viscocrowd.scenarios.anneau import parametres_anneau, simuler_anneau
from viscocrowd.scenarios.campagne import contexte

CONFIG = lire_configuration(Path(sys.argv[1]))
VARIANTES = {
    "rayon_023": {"rayon": 0.23, "navigation": {}},
    "tau_07": {"navigation": {"temps_anticipation": 0.7}},
}
EFFECTIFS = (264, 226, 188, 151, 113)  # 3,5 a 1,5 pers/m2, les plus longs d'abord
GRAINES = (1, 2, 3)


def mesurer(tache):
    variante, n, graine = tache
    debut = time.perf_counter()
    p = parametres_anneau(
        CONFIG,
        n_agents=n,
        graine=graine,
        temps_espacement=None,
        duree=40.0,
        debut_mesure=20.0,
        **VARIANTES[variante],
    )
    r = simuler_anneau(p)
    return {
        "variante": variante,
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
    taches = [(va, n, g) for n in EFFECTIFS for va in VARIANTES for g in GRAINES]
    with Pool(20) as pool:
        resultats = pool.map(mesurer, taches, chunksize=1)
    Path(sys.argv[2]).write_text(
        json.dumps({"contexte": contexte(), "resultats": resultats}, indent=1), encoding="utf-8"
    )
    for m in sorted(resultats, key=lambda m: (m["variante"], m["n"], m["graine"])):
        print(
            m["variante"],
            m["n"],
            m["graine"],
            f"v={m['vitesse']:.3f}",
            f"derive={m['derive']:.1%}",
            f"viol={m['violation']:.1e}",
        )
    print(f"duree {(time.perf_counter() - debut) / 60:.0f} min")
