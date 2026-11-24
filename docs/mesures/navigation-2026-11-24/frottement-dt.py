"""Condition 2 de Lenny (#158) : l'effet du mouille tient-il a dt/2 avec la navigation ?

Question, ecrite avant le calcul. Dans le prototype de #201, le frottement que consomme
deja la marche (RCOF = 0,20, Beschorner et al. 2016) donne un effet du mouille detecte
sur la reference (Delta t50 = +0,47 s, 9/10), stable a dt/2 (+0,474 contre +0,469 s).
Avec la navigation, Delta t100 disparaissait (-0,02 s). On mesure les deux modeles de
marche, a dt et a dt/2, sur les memes graines.

Le prototype n'est pas dans le depot. D'apres #201, il retranche RCOF g au plafond
d'acceleration de la marche : 0,34 g - 0,20 g = 1,37 m/s^2 sur le mouille et
0,60 g - 0,20 g = 3,92 m/s^2 sur le sec (#201 donne 1,34 et 3,94 a partir des valeurs
arrondies 3,3 et 5,9 du YAML). On le reproduit ici par la configuration seule :
a_max - RCOF g sur MOUILLE et SEC, l'eau inchangee. La premiere ligne (reference, dt)
doit redonner l'effet du prototype, Delta t50 ~ +0,47 s ; sinon, la reproduction n'est
pas fidele et le reste ne se lit pas.

Cas, graines 1 a 10, chacun avec son temoin sec (`temoin`, meme frottement) :
  - reference : T = 0,35 s, sans navigation ;
  - navigation : navigation a tau = 0,20 s (etalonnee sur E0, #158) ;
chacun a dt et a dt/2.

Critere (`criteres-acceptation.md`, § 3, critere 2), fixe avant le calcul : l'effet
Delta = mouille - sec d'une grandeur (t50, t100) est robuste au pas de temps si, a dt/2,
il garde son signe sur au moins 9 graines sur 10 quand il l'avait a dt, et si l'ecart
apparie (dt/2 - dt) de Delta reste sous son ecart-type entre graines.

Usage, depuis la racine du depot :
    python docs/mesures/navigation-2026-11-24/frottement-dt.py experiments/piscine.yaml
"""

import copy
import json
import sys
import time
from multiprocessing import Pool
from pathlib import Path

import numpy as np

from viscocrowd.io.configuration import lire_configuration
from viscocrowd.scenarios.balayage_piscine import temoin
from viscocrowd.scenarios.campagne import contexte
from viscocrowd.scenarios.piscine import ParametresPiscine, simuler_piscine

RCOF = 0.20  # frottement requis par un pas de marche (Beschorner et al. 2016)
G = 9.81  # m/s^2
GRAINES = range(1, 11)


def avec_frottement(parametres: dict) -> dict:
    """Plafond d'acceleration de la marche diminue de RCOF g sur la plage (prototype #201)."""
    p = copy.deepcopy(parametres)
    for sol in ("MOUILLE", "SEC"):
        p["parametres_milieux"][sol]["acceleration_max"] -= RCOF * G
    return p


BASE = avec_frottement(lire_configuration(Path(sys.argv[1]))["parametres"])
NAV = {"navigation": {"temps_anticipation": 0.2}}
MODELES = {"reference": BASE, "navigation": BASE | NAV}
CAS = {}
for nom, p in MODELES.items():
    for pas, facteur in (("dt", 1.0), ("dt2", 0.5)):
        mouille = p | {"dt": p["dt"] * facteur}
        CAS[(nom, pas, "mouille")] = mouille
        CAS[(nom, pas, "sec")] = temoin(mouille)


def mesurer(tache):
    cle, graine = tache
    debut = time.perf_counter()
    r = simuler_piscine(ParametresPiscine(**CAS[cle], graine=graine))
    return {
        "modele": cle[0],
        "pas": cle[1],
        "sol": cle[2],
        "graine": graine,
        "t50": r.temps_evacuation(0.5),
        "t90": r.temps_evacuation(0.9),
        "t100": r.temps_evacuation(1.0),
        "violation": r.violation_paroi_max(),
        "calcul_s": time.perf_counter() - debut,
    }


def ecarts(resultats, modele, pas, grandeur):
    """Delta = mouille - sec, graine par graine."""
    m = {
        r["graine"]: r[grandeur]
        for r in resultats
        if (r["modele"], r["pas"], r["sol"]) == (modele, pas, "mouille")
    }
    s = {
        r["graine"]: r[grandeur]
        for r in resultats
        if (r["modele"], r["pas"], r["sol"]) == (modele, pas, "sec")
    }
    return np.array([m[g] - s[g] for g in GRAINES])


if __name__ == "__main__":
    debut = time.perf_counter()
    taches = [(cle, g) for cle in CAS for g in GRAINES]
    taches.sort(key=lambda t: (t[0][0] != "navigation", t[0][1] != "dt2"))  # longs d'abord
    with Pool(14) as pool:
        resultats = pool.map(mesurer, taches, chunksize=1)
    sortie = Path(__file__).with_suffix(".json")
    sortie.write_text(
        json.dumps({"contexte": contexte(), "rcof": RCOF, "resultats": resultats}, indent=1),
        encoding="utf-8",
    )
    for modele in MODELES:
        for grandeur in ("t50", "t100"):
            d1, d2 = (
                ecarts(resultats, modele, "dt", grandeur),
                ecarts(resultats, modele, "dt2", grandeur),
            )
            diff = d2 - d1
            print(
                f"{modele:10s} {grandeur:4s} | dt : {d1.mean():+.3f} ± {d1.std(ddof=1):.3f}"
                f" ({(d1 > 0).sum()}/10 > 0) | dt/2 : {d2.mean():+.3f} ± {d2.std(ddof=1):.3f}"
                f" ({(d2 > 0).sum()}/10 > 0)"
                f" | dt/2 - dt : {diff.mean():+.3f} ± {diff.std(ddof=1):.3f}"
            )
    viol = max(r["violation"] for r in resultats)
    print(f"violation max {viol:.1e} ; duree {(time.perf_counter() - debut) / 60:.0f} min")
