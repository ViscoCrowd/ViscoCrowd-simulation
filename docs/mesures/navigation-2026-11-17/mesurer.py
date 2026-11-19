"""Navigation locale (#158) : la file indienne disparait-elle, et que change-t-elle ?

Pour chaque graine (1 a 10), six evacuations de la piscine de reference :

  - reference : guidage seul (navigation: null) ;
  - navigation : heuristiques de Moussaid et al. (2011), valeurs de l'article ;
  - navigation_dt2 : la meme au pas de temps divise par deux ;
  - navigation_sec : la meme, sol entierement sec (temoin du mouille) ;
  - navigation_fig3 : champ de vision et horizon de la fig. 3 de l'article (45 deg,
    8 m, foules denses) au lieu de ceux de la fig. 2 (75 deg, 10 m) ;
  - navigation_sans_dispersion : la meme sans dispersion des vitesses souhaitees
    (dispersion_vitesse: 0). Le facteur individuel s'applique aussi aux nageurs : cette
    variante separe l'effet des heuristiques de celui de la dispersion (revue de #163).

Mesures : t50, t90, t100 (s), debit a la porte (pers/(m.s), estimateur de E0), part
des positions de plage le long du bassin a moins de 1 cm du plus pres possible,
epaisseur du flux (ecart interquartile lateral par tranche de 1 m, mediane des
tranches, en m), violation des murs et temps de calcul. Puis les ecarts apparies graine
par graine, avec deux valeurs p : permutation exacte des signes sur la moyenne, et test de
signe exact de docs/criteres-acceptation.md (§ 3), qui seul decide d'une detection.

Usage : python docs/mesures/navigation-2026-11-17/mesurer.py experiments/piscine.yaml
"""

import itertools
import json
import math
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
    "navigation_sans_dispersion": BASE | {"navigation": {"dispersion_vitesse": 0.0}},
}
# Ecarts apparies a publier : (cas, moins ce cas).
ECARTS = (
    ("navigation", "reference"),
    ("navigation_sans_dispersion", "reference"),
    ("navigation", "navigation_sans_dispersion"),
    ("navigation_dt2", "navigation"),
    ("navigation", "navigation_sec"),
    ("navigation_fig3", "navigation"),
)


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


def p_permutation(ecarts: np.ndarray) -> float:
    """Valeur p bilaterale exacte de la moyenne, par permutation des signes (2^n tirages)."""
    observe = abs(ecarts.mean())
    signes = np.array(list(itertools.product((1.0, -1.0), repeat=ecarts.size)))
    return float(np.mean(np.abs(signes @ ecarts / ecarts.size) >= observe - 1e-12))


def p_signe(ecarts: np.ndarray) -> tuple[float, int, int]:
    """Test de signe exact bilateral, egalites (|d| < 1e-9 s) ecartees (criteres, § 3)."""
    utiles = ecarts[np.abs(ecarts) >= 1e-9]
    n, positifs = utiles.size, int(np.sum(utiles > 0))
    if n == 0:
        return 1.0, 0, 0
    k = min(positifs, n - positifs)
    queue = sum(math.comb(n, i) for i in range(k + 1)) / 2**n
    return min(1.0, 2 * queue), positifs, n


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
    print("Ecarts apparies : moyenne ± ecart-type, p permutation, p signe (positifs/n)")
    for a, b in ECARTS:
        for k in ("t50", "t90", "t100", "debit"):
            par_graine = {m["graine"]: m[k] for m in resultats if m["cas"] == a}
            ecarts = np.array([par_graine[m["graine"]] - m[k] for m in resultats if m["cas"] == b])
            ps, positifs, n = p_signe(ecarts)
            print(
                f"  {a} - {b} {k}: {ecarts.mean():+.3f} ± {ecarts.std(ddof=1):.3f}"
                f" p_perm={p_permutation(ecarts):.3f} p_signe={ps:.3f} ({positifs}/{n})"
            )
