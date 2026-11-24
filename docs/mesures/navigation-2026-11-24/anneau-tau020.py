"""Condition 1 de Lenny (#158) : l'anneau avec la navigation a tau = 0,20 s, contre Weidmann.

Question, ecrite avant le calcul. La navigation a tau = 0,20 s est etalonnee sur E0 ; a
tau = 0,5 s, elle etait deja de 23 a 67 % au-dessus de Weidmann au-dela de 1,5 pers/m^2.
Un tau plus court autorise une vitesse plus grande a jeu egal : on s'attend a ce que
l'ecart grandisse. Combien ?

Meme protocole que `docs/mesures/navigation-2026-11-17/anneau.py` (graines 1 a 10, neuf
densites, 40 s, vitesse mesuree de 20 a 40 s), seul `temps_anticipation` change.

Pas de seuil fixe d'avance : Lenny demande un ecart « acceptable » a Weidmann. On rapporte
l'ecart relatif par densite, a cote de celui de tau = 0,5 s et de la reference T.

Usage, depuis la racine du depot :
    python docs/mesures/navigation-2026-11-24/anneau-tau020.py experiments/anneau.yaml
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
TAU = 0.2


def mesurer(tache):
    n, graine = tache
    debut = time.perf_counter()
    p = parametres_anneau(
        CONFIG,
        n_agents=n,
        graine=graine,
        temps_espacement=None,
        navigation={"temps_anticipation": TAU},
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
    with Pool(14) as pool:
        resultats = pool.map(mesurer, taches, chunksize=1)
    sortie = Path(__file__).with_suffix(".json")
    sortie.write_text(
        json.dumps({"contexte": contexte(), "tau": TAU, "resultats": resultats}, indent=1),
        encoding="utf-8",
    )
    for n in sorted(EFFECTIFS):
        lignes = [m for m in resultats if m["n"] == n]
        v = np.array([m["vitesse"] for m in lignes])
        w = lignes[0]["weidmann"]
        print(
            f"rho={lignes[0]['densite']:.2f} v={v.mean():.3f}±{v.std(ddof=1):.3f}"
            f" Weidmann={w:.3f} ecart={v.mean() / w - 1:+.0%}"
            f" derive_max={max(m['derive'] for m in lignes):.1%}"
            f" viol={max(m['violation'] for m in lignes):.1e}"
        )
    print(f"duree {(time.perf_counter() - debut) / 60:.0f} min")
