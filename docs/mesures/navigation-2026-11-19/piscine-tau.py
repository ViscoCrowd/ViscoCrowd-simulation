"""Piscine avec la navigation etalonnee sur E0 (tau = 0,20 s).

File indienne, t50, t100, et mouille - sec.

Reprend les mesures de docs/mesures/navigation-2026-11-17/mesurer.py (fonction `mesurer`),
pour trois cas : reference, navigation tau = 0,20 s, et son temoin sec. Graines 1 a 10.

Usage, depuis la racine du depot (arguments : configuration, puis bilan JSON) :

    python docs/mesures/navigation-2026-11-19/piscine-tau.py experiments/piscine.yaml
        docs/mesures/navigation-2026-11-19/piscine-tau.json

Lance le 19 novembre depuis le commit 275fc3d, alors hors du depot ; seules cette notice
et la mise en forme ruff ont change depuis.
"""

import importlib.util
import json
import sys
from multiprocessing import Pool
from pathlib import Path

import numpy as np

CHEMIN = Path("docs/mesures/navigation-2026-11-17/mesurer.py")
spec = importlib.util.spec_from_file_location("mesurer_nav", CHEMIN)
mesurer_nav = importlib.util.module_from_spec(spec)
sys.modules["mesurer_nav"] = mesurer_nav
spec.loader.exec_module(mesurer_nav)
from viscocrowd.scenarios.balayage_piscine import temoin  # noqa: E402
from viscocrowd.scenarios.campagne import contexte  # noqa: E402

BASE = mesurer_nav.BASE
NAV = {"navigation": {"temps_anticipation": 0.2}}
mesurer_nav.CAS.clear()
mesurer_nav.CAS.update(
    {
        "reference": BASE,
        "navigation_tau020": BASE | NAV,
        "navigation_tau020_sec": temoin(BASE) | NAV,
    }
)

if __name__ == "__main__":
    taches = [(nom, g) for nom in mesurer_nav.CAS for g in range(1, 11)]
    with Pool(20) as pool:
        resultats = pool.map(mesurer_nav.mesurer, taches, chunksize=1)
    Path(sys.argv[2]).write_text(
        json.dumps({"contexte": contexte(), "resultats": resultats}, indent=1), encoding="utf-8"
    )
    for nom in mesurer_nav.CAS:
        lignes = [m for m in resultats if m["cas"] == nom]
        print(
            nom,
            {
                k: round(float(np.mean([m[k] for m in lignes])), 3)
                for k in ("contre_le_bord", "epaisseur_flux", "t50", "t90", "t100", "debit")
            },
        )
    for a, b in (
        ("navigation_tau020", "reference"),
        ("navigation_tau020", "navigation_tau020_sec"),
    ):
        for k in ("t50", "t90", "t100", "debit"):
            par = {m["graine"]: m[k] for m in resultats if m["cas"] == b}
            e = np.array([m[k] - par[m["graine"]] for m in resultats if m["cas"] == a])
            ps, pos, n = mesurer_nav.p_signe(e)
            print(
                f"  {a} - {b} {k}: {e.mean():+.3f} ± {e.std(ddof=1):.3f}"
                f" p_signe={ps:.3f} ({pos}/{n})"
            )
