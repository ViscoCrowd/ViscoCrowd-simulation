"""Le plafond d'adherence du mouille sert-il ? Reference (file indienne) contre navigation.

A chaque appel de `model.milieu.vitesse_libre`, on releve pour chaque agent l'acceleration
voulue |u - v| / tau et le plafond a_max de son sol. Le sol se lit sur a_max (reference :
eau 1,67, mouille 3,3, sec 5,9 m/s^2). Sur la bande mouillee, le plafond freine l'agent
quand l'acceleration voulue depasse 3,3 m/s^2 ; l'acceleration perdue par rapport au sec
vaut min(|a|, 5,9) - min(|a|, 3,3).

Usage, depuis la racine du depot (arguments : configuration, puis bilan JSON) :

    python docs/mesures/navigation-2026-11-19/adherence.py experiments/piscine.yaml
        docs/mesures/navigation-2026-11-19/adherence.json

Lance le 19 novembre depuis le commit 275fc3d, alors hors du depot ; seules cette notice
et la mise en forme ruff ont change depuis.
"""

import json
import sys
import time
from multiprocessing import Pool
from pathlib import Path

import numpy as np

import viscocrowd.model.milieu as milieu
from viscocrowd.io.configuration import lire_configuration
from viscocrowd.scenarios.campagne import contexte
from viscocrowd.scenarios.piscine import ParametresPiscine, simuler_piscine

BASE = lire_configuration(Path(sys.argv[1]))["parametres"]
SOLS = {k: v["acceleration_max"] for k, v in BASE["parametres_milieux"].items()}
CAS = {"reference": BASE, "navigation": BASE | {"navigation": {}}}
RELEVE = {}
_ORIGINAL = milieu.vitesse_libre


def _vitesse_libre_relevee(v, u, relaxation, acceleration_max, dt):
    tau = np.broadcast_to(np.asarray(relaxation, dtype=float), (v.shape[0],))
    a_max = np.broadcast_to(np.asarray(acceleration_max, dtype=float), (v.shape[0],))
    voulue = np.linalg.norm((np.asarray(u) - np.asarray(v)) / tau[:, None], axis=1)
    for nom in ("MOUILLE", "SEC"):
        sel = a_max == SOLS[nom]
        r = RELEVE[nom]
        r["pas_agents"] += int(sel.sum())
        r["au_dessus_mouille"] += int(np.sum(voulue[sel] > SOLS["MOUILLE"]))
        r["au_dessus_sec"] += int(np.sum(voulue[sel] > SOLS["SEC"]))
        r["perte"] += float(
            np.sum(np.minimum(voulue[sel], SOLS["SEC"]) - np.minimum(voulue[sel], SOLS["MOUILLE"]))
        )
    return _ORIGINAL(v, u, relaxation, acceleration_max, dt)


milieu.vitesse_libre = _vitesse_libre_relevee


def mesurer(tache):
    nom, graine = tache
    RELEVE.clear()
    for sol in ("MOUILLE", "SEC"):
        RELEVE[sol] = {"pas_agents": 0, "au_dessus_mouille": 0, "au_dessus_sec": 0, "perte": 0.0}
    debut = time.perf_counter()
    r = simuler_piscine(ParametresPiscine(**CAS[nom], graine=graine))
    return {
        "cas": nom,
        "graine": graine,
        "t50": r.temps_evacuation(0.5),
        "t100": r.temps_evacuation(1.0),
        "releve": {k: dict(v) for k, v in RELEVE.items()},
        "calcul_s": time.perf_counter() - debut,
    }


if __name__ == "__main__":
    taches = [(nom, g) for nom in CAS for g in range(1, 11)]
    with Pool(20) as pool:
        resultats = pool.map(mesurer, taches, chunksize=1)
    Path(sys.argv[2]).write_text(
        json.dumps({"contexte": contexte(), "a_max": SOLS, "resultats": resultats}, indent=1),
        encoding="utf-8",
    )
    for nom in CAS:
        lignes = [m for m in resultats if m["cas"] == nom]
        for sol in ("MOUILLE", "SEC"):
            pas = np.array([m["releve"][sol]["pas_agents"] for m in lignes], float)
            frein = np.array([m["releve"][sol]["au_dessus_mouille"] for m in lignes]) / pas
            sec = np.array([m["releve"][sol]["au_dessus_sec"] for m in lignes]) / pas
            perte = np.array([m["releve"][sol]["perte"] for m in lignes]) / pas
            print(
                f"{nom:10s} {sol:7s} pas-agents/eval {pas.mean():9.0f}"
                f"  |a|>3,3 : {frein.mean():6.2%} ± {frein.std(ddof=1):.2%}"
                f"  |a|>5,9 : {sec.mean():6.2%}  perte moyenne {perte.mean():.4f} m/s2"
            )
        t50 = np.mean([m["t50"] for m in lignes])
        print(f"{nom:10s} t50 moyen {t50:.2f} s")
