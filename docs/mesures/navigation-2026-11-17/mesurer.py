"""Navigation locale (#158) : la file indienne disparait-elle, et que change-t-elle ?

Pour chaque graine (1 a 10), quatre evacuations de la piscine de reference :

  - reference : guidage seul (navigation: null) ;
  - navigation : heuristiques de Moussaid et al. (2011), valeurs de l'article ;
  - navigation_dt2 : la meme au pas de temps divise par deux ;
  - navigation_sec : la meme, sol entierement sec (temoin du mouille) ;
  - navigation_fig3 : champ de vision et horizon de la fig. 3 de l'article (45 deg,
    8 m, foules denses) au lieu de ceux de la fig. 2 (75 deg, 10 m).

Mesures : t50, t90, t100 (s), debit a la porte (pers/(m.s), estimateur de E0), part
des positions de plage le long du bassin a moins de 1 cm du plus pres possible,
epaisseur du flux (ecart interquartile lateral par tranche de 1 m, mediane des
tranches, en m), violation des murs et temps de calcul.

Usage : python docs/mesures/navigation-2026-11-17/mesurer.py experiments/piscine.yaml
"""

import json
import sys
import time
from multiprocessing import Pool
from pathlib import Path

import numpy as np

from viscocrowd.io.configuration import lire_configuration
from viscocrowd.scenarios.balayage_piscine import temoin
from viscocrowd.scenarios.campagne import contexte
from viscocrowd.scenarios.goulot import debit_seyfried
from viscocrowd.scenarios.piscine import PLAGE, ParametresPiscine, simuler_piscine

BASE = lire_configuration(Path(sys.argv[1]))["parametres"]
CAS = {
    "reference": BASE,
    "navigation": BASE | {"navigation": {}},
    "navigation_dt2": BASE | {"navigation": {}, "dt": BASE["dt"] / 2},
    "navigation_sec": temoin(BASE) | {"navigation": {}},
    "navigation_fig3": BASE | {"navigation": {"champ_vision": 45.0, "horizon": 8.0}},
}


def mesurer(tache):
    nom, graine = tache
    debut = time.perf_counter()
    r = simuler_piscine(ParametresPiscine(**CAS[nom], graine=graine))
    calcul = time.perf_counter() - debut
    p = r.parametres.piscine
    b, rayon = p.bassin, r.parametres.rayon
    L, W = p.longueur_emprise, p.largeur_emprise
    # Un instant sur 10 (0,1 s, ou 0,05 s a dt/2) : les positions voisines sont correlees.
    pas = 10 if nom != "navigation_dt2" else 20
    xs, es = r.x[::pas], r.etats[::pas]
    ecarts = []
    for x, e in zip(xs, es, strict=True):
        pl = x[(e == PLAGE) & (x[:, 0] > b.x_min) & (x[:, 0] < b.x_max)]
        ecarts += list(np.minimum(np.abs(pl[:, 1] - b.y_max), np.abs(pl[:, 1] - b.y_min)))
    contre_le_bord = float(np.mean(np.array(ecarts) < rayon + 0.01))
    epaisseurs = []
    for x0 in np.arange(b.x_min + 1.0, L - 1.0, 1.0):
        for cote in (1, -1):
            ys = []
            for x, e in zip(xs, es, strict=True):
                sel = (e == PLAGE) & (x[:, 0] >= x0) & (x[:, 0] < x0 + 1.0)
                sel &= cote * (x[:, 1] - W / 2) > 0
                ys += list(x[sel, 1])
            if len(ys) > 20:
                q1, q3 = np.quantile(ys, [0.25, 0.75])
                epaisseurs.append(float(q3 - q1))
    finis = bool(np.all(np.isfinite(r.sorties)))
    return {
        "cas": nom,
        "graine": graine,
        "t50": r.temps_evacuation(0.5),
        "t90": r.temps_evacuation(0.9),
        "t100": r.temps_evacuation(1.0),
        "debit": debit_seyfried(r.sorties, p.largeur_porte) if finis else None,
        "contre_le_bord": contre_le_bord,
        "epaisseur_flux": float(np.median(epaisseurs)),
        "violation": r.violation_paroi_max(),
        "calcul_s": calcul,
    }


if __name__ == "__main__":
    taches = [(nom, g) for nom in CAS for g in range(1, 11)]
    with Pool(12) as pool:
        resultats = pool.map(mesurer, taches)
    sortie = Path(__file__).parent / "resultats.json"
    sortie.write_text(
        json.dumps({"contexte": contexte(), "resultats": resultats}, indent=1), encoding="utf-8"
    )
    for nom in CAS:
        lignes = [m for m in resultats if m["cas"] == nom]
        moy = {
            k: np.mean([m[k] for m in lignes])
            for k in ("t50", "t100", "contre_le_bord", "epaisseur_flux", "calcul_s")
        }
        print(nom, {k: round(float(v), 3) for k, v in moy.items()})
