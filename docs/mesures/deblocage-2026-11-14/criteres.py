"""Criteres de #127 : 160 simulations, une ligne par simulation terminee."""

import copy
import time
from collections import defaultdict
from multiprocessing import Pool
from pathlib import Path

import numpy as np

import viscocrowd.scenarios.piscine as s
from viscocrowd.io.configuration import lire_configuration
from viscocrowd.scenarios.balayage_piscine import temoin

BASE = lire_configuration(Path("experiments/piscine.yaml"))["parametres"]
DEB = {"delai": 2.0, "portee": 0.65, "vitesse": 0.001}


def run(args):
    nom, chg, sol, g, deb = args
    par = copy.deepcopy(BASE)
    if "a_eau" in chg:
        par["parametres_milieux"]["EAU"]["acceleration_max"] = chg["a_eau"]
    par |= {k: v for k, v in chg.items() if k != "a_eau"}
    par["deblocage"] = DEB if deb else None
    if sol == "sec":
        par = temoin(par)
    r = s.simuler_piscine(s.ParametresPiscine(**par, graine=g))
    return nom, sol, g, deb, int(np.sum(r.etats[-1] != s.SORTI)), r.deblocages, r.sorties.tobytes()


if __name__ == "__main__":
    taches = []
    for a in (1.6, 1.67):
        for g in range(1, 11):
            for sol in ("mouille", "sec"):
                chg = {"temps_espacement": None, "n_agents": 200, "a_eau": a}
                taches.append((f"sans-reg-200-a{a}", chg, sol, g, True))
    regules = (
        ("ref", {}),
        ("reg-200", {"n_agents": 200}),
        ("reg-porte-0.8", {"geometrie": BASE["geometrie"] | {"largeur_porte": 0.8}}),
    )
    for nom, chg in regules:
        for g in range(1, 11):
            for sol in ("mouille", "sec"):
                for deb in (False, True):
                    taches.append((nom, chg, sol, g, deb))

    t0 = time.perf_counter()
    res = []
    with Pool(10) as pool:
        for k, out in enumerate(pool.imap_unordered(run, taches), 1):
            res.append(out)
            nom, sol, g, deb, restes, nd, _ = out
            print(
                f"[{k:3d}/{len(taches)}] {nom:18s} {sol:7s} graine {g:2d} "
                f"deblocage={'oui' if deb else 'non'} : restes {restes:2d}, deblocages {nd}",
                flush=True,
            )
    print(f"{len(taches)} simulations en {time.perf_counter() - t0:.0f} s")

    agg = defaultdict(lambda: [0, 0, 0])
    for nom, sol, g, deb, restes, nd, _ in res:
        a = agg[(nom, deb)]
        a[0] += restes > 0
        a[1] += restes
        a[2] += nd
    for k, (inc, restes, nd) in sorted(agg.items()):
        print(k, "incompletes", inc, "restes", restes, "deblocages", nd)
    d = {(n, so, g, deb): b for n, so, g, deb, _, _, b in res}
    for nom, _ in regules:
        same = all(
            d[(nom, so, g, False)] == d[(nom, so, g, True)]
            for g in range(1, 11)
            for so in ("mouille", "sec")
        )
        print(nom, "sorties identiques au bit pres avec/sans deblocage :", same)
