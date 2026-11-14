import copy, numpy as np
from multiprocessing import Pool
from pathlib import Path
import viscocrowd.scenarios.piscine as s
from viscocrowd.io.configuration import lire_configuration
from viscocrowd.scenarios.balayage_piscine import temoin

BASE = lire_configuration(Path("experiments/piscine.yaml"))["parametres"]
DEB = {"delai": 2.0, "portee": 0.65, "vitesse": 0.001}


def run(a):
    sol, g, deb = a
    par = copy.deepcopy(BASE) | {"n_agents": 200, "deblocage": DEB if deb else None}
    if sol == "sec":
        par = temoin(par)
    r = s.simuler_piscine(s.ParametresPiscine(**par, graine=g))
    return (
        a,
        r.temps_evacuation(0.5),
        r.temps_evacuation(0.9),
        r.temps_evacuation(1.0),
        r.deblocages,
    )


if __name__ == "__main__":
    cas = [("mouille", 1), ("sec", 4), ("mouille", 4), ("mouille", 6), ("mouille", 8)]
    with Pool(10) as pool:
        res = {
            a: rest
            for a, *rest in pool.map(run, [(so, g, d) for so, g in cas for d in (False, True)])
        }
    for so, g in cas:
        sans, avec = res[(so, g, False)], res[(so, g, True)]
        print(
            f"{so:7s} graine {g:2d}: t50 {sans[0]:.2f}->{avec[0]:.2f}  t90 {sans[1]:.2f}->{avec[1]:.2f}  t100 {sans[2]:.2f}->{avec[2]:.2f}  (deblocages {avec[3]})"
        )
