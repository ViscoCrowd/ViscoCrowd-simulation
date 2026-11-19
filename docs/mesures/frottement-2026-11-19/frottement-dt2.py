"""Controle a dt/2 du prototype frottement.py (meme code, pas de temps divise par deux).

Prototype : la marche consomme du frottement. Effet sur l'evacuation, et glissades attendues.

Hypotheses sourcees :
  - adherence pieds nus de piscine : mouille 0,34, sec 0,60 (Kendzior 2023, deja dans
    piscine.yaml sous la forme a_max = mu g) ;
  - frottement requis par la marche normale RCOF ~ 0,20 (Beschorner et al. 2016 : 0,207 ±
    0,027) ; 0,25 approche une marche rapide (hypothese, la valeur a 2 m/s manque) ;
  - probabilite de glisser a un pas : logistique de Beschorner et al. (2016),
    logit P = -11,9 + 54,1 RCOF a ACOF moyen 0,165, soit logit P = -2,97 - 54,1 m avec la
    marge m = ACOF - frottement demande.

Hypothese de modelisation (la notre) : sur la plage, l'acceleration disponible pour
manoeuvrer est (mu - RCOF) g, et le frottement demande a un pas vaut RCOF + |a_voulue| / g.
La marge vaut donc m = (a_max reduit - |a_voulue|) / g. Cadence : 2 pas/s (rapport NIOSH de
Cham, 120 pas/min). Les glissades sont COMPTEES (esperance), pas simulees : personne ne
tombe, faute de source sur la part des glissades qui finissent au sol.

Usage, depuis la racine du depot (arguments : configuration, puis bilan JSON) :

    python docs/mesures/frottement-2026-11-19/frottement-dt2.py experiments/piscine.yaml
        docs/mesures/frottement-2026-11-19/frottement-dt2.json

Lance le 19 novembre depuis le commit 6626819, alors hors du depot ; seules cette notice et
la mise en forme (ruff, une chaine coupee en deux) ont change depuis.
"""

import json
import math
import sys
import time
from multiprocessing import Pool
from pathlib import Path

import numpy as np

import viscocrowd.model.milieu as milieu
from viscocrowd.io.configuration import lire_configuration
from viscocrowd.scenarios.balayage_piscine import temoin
from viscocrowd.scenarios.campagne import contexte
from viscocrowd.scenarios.piscine import ParametresPiscine, simuler_piscine

G = 9.81
CADENCE = 2.0  # pas/s
B0_MARGE, B1 = -2.97, 54.1
BASE = lire_configuration(Path(sys.argv[1]))["parametres"]
MU = {s: BASE["parametres_milieux"][s]["acceleration_max"] / G for s in ("MOUILLE", "SEC")}
MODELES = {"reference": {}, "navigation": {"navigation": {"temps_anticipation": 0.2}}}
RCOFS = (0.20, 0.25)


def configuration(modele, rcof, sol):
    p = json.loads(json.dumps(BASE))
    for s in ("MOUILLE", "SEC"):
        p["parametres_milieux"][s]["acceleration_max"] = (MU[s] - rcof) * G
    p = p | MODELES[modele] | {"dt": BASE["dt"] / 2}  # controle : pas de temps divise par deux
    return temoin(p) if sol == "sec" else p


RELEVE = {}
_ORIGINAL = milieu.vitesse_libre


def _releve(v, u, relaxation, acceleration_max, dt):
    tau = np.broadcast_to(np.asarray(relaxation, dtype=float), (v.shape[0],))
    a_max = np.broadcast_to(np.asarray(acceleration_max, dtype=float), (v.shape[0],))
    voulue = np.linalg.norm((np.asarray(u) - np.asarray(v)) / tau[:, None], axis=1)
    for nom, valeur in RELEVE["sols"].items():
        sel = np.isclose(a_max, valeur)
        if not sel.any():
            continue
        m = (a_max[sel] - voulue[sel]) / G
        p_pas = 1.0 / (1.0 + np.exp(-(B0_MARGE - B1 * m)))
        r = RELEVE[nom]
        r["pas_agents"] += int(sel.sum())
        r["glissades"] += float(np.sum(p_pas) * CADENCE * dt)
        r["marge_negative"] += int(np.sum(m < 0))
    return _ORIGINAL(v, u, relaxation, acceleration_max, dt)


milieu.vitesse_libre = _releve


def mesurer(tache):
    modele, rcof, sol, graine = tache
    p = configuration(modele, rcof, sol)
    RELEVE.clear()
    RELEVE["sols"] = {s: p["parametres_milieux"][s]["acceleration_max"] for s in ("MOUILLE", "SEC")}
    if sol == "sec":  # temoin : les deux sols ont la valeur du sec, on ne releve qu'une fois
        RELEVE["sols"] = {"SEC": RELEVE["sols"]["SEC"]}
    for s in RELEVE["sols"]:
        RELEVE[s] = {"pas_agents": 0, "glissades": 0.0, "marge_negative": 0}
    debut = time.perf_counter()
    r = simuler_piscine(ParametresPiscine(**p, graine=graine))
    return {
        "modele": modele,
        "rcof": rcof,
        "sol": sol,
        "graine": graine,
        "t50": r.temps_evacuation(0.5),
        "t100": r.temps_evacuation(1.0),
        "releve": {s: dict(RELEVE[s]) for s in RELEVE["sols"]},
        "calcul_s": time.perf_counter() - debut,
    }


def p_signe(e):
    e = e[np.abs(e) >= 1e-9]
    n, k = e.size, int(np.sum(e > 0))
    if n == 0:
        return 1.0
    q = min(k, n - k)
    return min(1.0, 2 * sum(math.comb(n, i) for i in range(q + 1)) / 2**n)


if __name__ == "__main__":
    debut = time.perf_counter()
    taches = [
        (m, c, s, g)
        for m in ("navigation", "reference")
        for c in RCOFS
        for s in ("mouille", "sec")
        for g in range(1, 11)
    ]
    with Pool(20) as pool:
        resultats = pool.map(mesurer, taches, chunksize=1)
    Path(sys.argv[2]).write_text(
        json.dumps({"contexte": contexte(), "mu": MU, "resultats": resultats}, indent=1),
        encoding="utf-8",
    )
    for m in MODELES:
        for c in RCOFS:
            lot = {
                s: sorted(
                    [x for x in resultats if (x["modele"], x["rcof"], x["sol"]) == (m, c, s)],
                    key=lambda x: x["graine"],
                )
                for s in ("mouille", "sec")
            }
            print(f"{m} RCOF={c}")
            for k in ("t50", "t100"):
                e = np.array([a[k] - b[k] for a, b in zip(lot["mouille"], lot["sec"], strict=True)])
                print(
                    f"  mouille - sec {k}: {e.mean():+.3f} ± {e.std(ddof=1):.3f} s"
                    f" ({int(np.sum(e > 0))}/10 positifs, p_signe={p_signe(e):.3f})"
                    f"  [{k} mouille {np.mean([x[k] for x in lot['mouille']]):.2f}]"
                )
            gm = [x["releve"]["MOUILLE"]["glissades"] for x in lot["mouille"]]
            gs = [x["releve"]["SEC"]["glissades"] for x in lot["mouille"]]
            gt = [x["releve"]["SEC"]["glissades"] for x in lot["sec"]]
            neg = [
                x["releve"]["MOUILLE"]["marge_negative"]
                / max(1, x["releve"]["MOUILLE"]["pas_agents"])
                for x in lot["mouille"]
            ]
            print(
                f"  glissades attendues par evacuation : bande mouillee {np.mean(gm):.3f}"
                f" (min {min(gm):.3f}, max {max(gm):.3f}), plage seche {np.mean(gs):.2e},"
                f" temoin tout sec {np.mean(gt):.2e} ;"
                f" marge negative sur le mouille {np.mean(neg):.2%}"
            )
    print(f"duree {(time.perf_counter() - debut) / 60:.0f} min")
