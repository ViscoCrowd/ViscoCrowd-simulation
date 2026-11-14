"""#130 : le taux de chute par bousculade depend-il de dt dans une vraie evacuation ?"""

import copy
import sys
from multiprocessing import Pool
from pathlib import Path

import viscocrowd.scenarios.piscine as s
from viscocrowd.io.configuration import lire_configuration

BASE = lire_configuration(Path(sys.argv[1]))["parametres"]
CHUTES = {"lambda_chute": 1e-12, "lambda_domino": 1e-12, "lambda_bousculade": 20.0}


def run(a):
    dt, g = a
    par = copy.deepcopy(BASE) | {"dt": dt, "chutes": CHUTES}
    par["geometrie"] = par["geometrie"] | {"largeur_porte": 0.8}
    r = s.simuler_piscine(s.ParametresPiscine(**par, graine=g))
    n = sum(1 for e in r.chutes if e.cause == "bousculade")
    return dt, g, n, r.temps_evacuation(1.0)


if __name__ == "__main__":
    with Pool(8) as pool:
        for dt, g, n, t100 in pool.imap_unordered(
            run, [(dt, g) for dt in (0.01, 0.005) for g in range(1, 11)]
        ):
            print(
                f"dt {dt:.3f} graine {g:2d} : {n:3d} chutes par bousculade, "
                f"t100 {t100:.2f} s, taux {n / t100:.3f} /s",
                flush=True,
            )
