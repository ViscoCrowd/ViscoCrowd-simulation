"""Invariants du modele de foule sur la piscine de reference (E1 sec et E2 mouille).

Pour chaque evacuation (graines 1 a 10, deux sols) : plus fort recouvrement entre deux
agents actifs a tous les instants, plus forte violation des murs et du bord du bassin,
projections non convergees, agents sortis, franchissements par agent, et conservation
eau + bord + plage + sortis = N a chaque instant.

Usage : python docs/mesures/invariants-piscine-2026-11-16/mesurer.py experiments/piscine.yaml
"""

import sys
from multiprocessing import Pool
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree

from viscocrowd.io.configuration import lire_configuration
from viscocrowd.scenarios.balayage_piscine import temoin
from viscocrowd.scenarios.campagne import contexte
from viscocrowd.scenarios.piscine import EAU, PLAGE, ParametresPiscine, simuler_piscine

BASE = lire_configuration(Path(sys.argv[1]))["parametres"]


def mesurer(cas):
    sol, g = cas
    par = BASE if sol == "mouille" else temoin(BASE)
    r = simuler_piscine(ParametresPiscine(**par, graine=g))
    n, diametre = r.parametres.n_agents, 2 * r.parametres.rayon
    recouvrement = 0.0
    for x, e in zip(r.x, r.etats, strict=True):
        actifs = np.flatnonzero((e == EAU) | (e == PLAGE))
        if actifs.size > 1:
            paires = cKDTree(x[actifs]).query_pairs(diametre, output_type="ndarray")
            if paires.size:
                d = np.hypot(*(x[actifs][paires[:, 0]] - x[actifs][paires[:, 1]]).T)
                recouvrement = max(recouvrement, float(diametre - d.min()))
    effectifs = np.stack([np.sum(r.etats == k, axis=1) for k in range(4)], axis=1)
    agents = r.franchissements[:, 0].astype(int)
    return (
        sol,
        g,
        recouvrement,
        r.violation_paroi_max(),
        r.projection.non_convergences,
        int(np.isfinite(r.sorties).sum()),
        bool(np.array_equal(np.sort(agents), np.arange(n))),
        bool(np.all(effectifs.sum(axis=1) == n)),
        r.t.size,
    )


if __name__ == "__main__":
    print("# contexte :", contexte()["code"], contexte()["sources_sha256"][:16])
    print(
        "# sol graine recouvrement_max_m violation_murs_m non_convergees sortis "
        "un_franchissement_par_agent conservation instants"
    )
    with Pool(8) as pool:
        for ligne in pool.imap(mesurer, [(s, g) for s in ("sec", "mouille") for g in range(1, 11)]):
            sol, g, rec, viol, nc, sortis, un, cons, k = ligne
            print(f"{sol:7s} {g:2d} {rec:.3e} {viol:.3e} {nc} {sortis} {un} {cons} {k}", flush=True)
