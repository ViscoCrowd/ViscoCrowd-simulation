"""E0 sur dix graines, pour N = 20, 40 et 60 : le controle de T tient-il au-dela de trois graines ?

Usage, depuis la racine du depot (arbre propre) :
    python docs/mesures/e0-dix-graines-2026-11-14/etalonner.py experiments/goulot.yaml sortie.json

Meme protocole que `viscocrowd etalonner-goulot --agents N --graines 1 ... 10`, mais chaque
mesure est conservee graine par graine, avec le contexte du code (`campagne.contexte`).
Le cas « sans reglage » (N = 60, `temps_espacement: null`) donne la premiere ligne du
tableau `tab:e0` du rapport.
"""

import json
import sys
from multiprocessing import Pool
from pathlib import Path

import numpy as np

from viscocrowd.io.configuration import lire_configuration
from viscocrowd.scenarios.campagne import contexte
from viscocrowd.scenarios.goulot import etalonner, reference_seyfried

LARGEURS = (0.8, 0.9, 1.0, 1.1, 1.2)
GRAINES = tuple(range(1, 11))
EFFECTIFS = (20, 40, 60)
SANS_REGLAGE = "60-sans-reglage"


def mesurer(cas):
    config = lire_configuration(Path(sys.argv[1]))
    if cas == SANS_REGLAGE:
        changements = {"n_agents": 60, "temps_espacement": None}
    else:
        changements = {"n_agents": cas}
    config = config | {"parametres": config["parametres"] | changements}
    resultats = etalonner(config, LARGEURS, GRAINES)
    return cas, {
        str(b): [{"graine": m.graine, "statut": m.statut, "debit": m.debit} for m in mesures]
        for b, mesures in resultats.items()
    }


def ecart_moyen(debits, n_agents):
    """Moyenne sur les largeurs de |J_s simule moyen - J_s Seyfried| / J_s Seyfried."""
    return float(
        np.mean(
            [
                abs(np.mean(debits[str(b)]) - reference_seyfried(n_agents, b))
                / reference_seyfried(n_agents, b)
                for b in LARGEURS
            ]
        )
    )


if __name__ == "__main__":
    sortie = Path(sys.argv[2])
    if sortie.exists():
        raise SystemExit(f"{sortie} existe deja")
    ctx = contexte()
    with Pool(len(EFFECTIFS) + 1) as pool:
        mesures = dict(pool.map(mesurer, [*EFFECTIFS, SANS_REGLAGE]))

    bilan = {"version": 1, "contexte": ctx, "largeurs": LARGEURS, "graines": GRAINES}
    bilan["effectifs"] = {}
    sans = {b: [m["debit"] for m in ms] for b, ms in mesures[SANS_REGLAGE].items()}
    statuts = sorted({m["statut"] for ms in mesures[SANS_REGLAGE].values() for m in ms})
    print(f"N = 60, sans reglage (temps_espacement null), statuts {statuts}")
    for b in LARGEURS:
        d = np.array(sans[str(b)])
        ref = reference_seyfried(60, b)
        print(
            f"  b {b:.1f} m : J_s {np.nanmean(d):.3f} ± {np.nanstd(d, ddof=1):.3f}"
            f" pers/(m.s), {np.nanmean(d) / ref:.2f} fois Seyfried"
        )
    bilan["sans_reglage"] = {"mesures": mesures[SANS_REGLAGE]}
    for n in EFFECTIFS:
        debits = {
            b: [m["debit"] for m in ms if m["statut"] == "ecoulement"]
            for b, ms in mesures[n].items()
        }
        bilan["effectifs"][str(n)] = {"mesures": mesures[n]}
        print(f"N = {n}")
        for b in LARGEURS:
            d = np.array(debits[str(b)])
            print(
                f"  b {b:.1f} m : {d.size} ecoulements, J_s {d.mean():.3f} ± {d.std(ddof=1):.3f}"
                f" pers/(m.s), Seyfried {reference_seyfried(n, b):.2f}"
            )
        trois = {b: v[:3] for b, v in debits.items()}
        print(f"  ecart moyen, graines 1 a 3  : {100 * ecart_moyen(trois, n):.1f} %")
        print(f"  ecart moyen, graines 1 a 10 : {100 * ecart_moyen(debits, n):.1f} %")
        # Variabilite due aux graines : l'ecart moyen de chaque triplet de graines consecutives.
        triplets = [
            100 * ecart_moyen({b: v[k : k + 3] for b, v in debits.items()}, n) for k in range(8)
        ]
        print(
            f"  triplets de graines consecutives : de {min(triplets):.1f} a {max(triplets):.1f} %"
        )
        niveau = np.mean([np.mean(debits[str(b)]) for b in LARGEURS])
        niveau_ref = np.mean([reference_seyfried(n, b) for b in LARGEURS])
        print(
            f"  niveau moyen sur les cinq largeurs : {niveau:.3f} contre {niveau_ref:.3f}"
            f" ({100 * (niveau / niveau_ref - 1):+.1f} %)"
        )
        bilan["effectifs"][str(n)] |= {
            "ecart_moyen_3": ecart_moyen(trois, n),
            "ecart_moyen_10": ecart_moyen(debits, n),
            "ecart_moyen_triplets": [t / 100 for t in triplets],
        }
    sortie.write_text(json.dumps(bilan, indent=1), encoding="utf-8")
    print(f"Bilan : {sortie}")
