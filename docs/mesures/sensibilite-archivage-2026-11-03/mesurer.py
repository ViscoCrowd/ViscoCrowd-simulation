"""Sensibilite des observables a l'espacement K des archives de la piscine (#73).

Rejoue des evacuations completes, puis ne garde qu'une image sur K, comme le ferait
`--archiver-tous K`. Reference : les memes mesures sur toutes les images (K = 1).

Depuis la racine du depot, sur une copie sans modification locale :

    python docs/mesures/sensibilite-archivage-2026-11-03/mesurer.py experiments/piscine.yaml \\
        docs/mesures/sensibilite-archivage-2026-11-03/resultats.json
"""

import json
import sys
from pathlib import Path

import numpy as np

from viscocrowd.io.configuration import lire_configuration
from viscocrowd.io.provenance import provenance_code
from viscocrowd.observables.debit import debit_specifique, franchissements
from viscocrowd.observables.densite import Rectangle, densite_comptage
from viscocrowd.observables.sortie import sorties_definitives
from viscocrowd.scenarios.piscine import PLAGE, ParametresPiscine, simuler_piscine

GRAINES, ESPACEMENTS = range(1, 11), (1, 2, 5, 10, 25, 50, 100)
source = Path(sys.argv[1])
c = lire_configuration(source)["parametres"]
code = provenance_code()  # lu avant le calcul, comme pour les archives
lignes = []
for g in GRAINES:
    r = simuler_piscine(ParametresPiscine(**c, graine=g))
    pi = r.parametres.piscine
    a, b = pi.porte
    xl = pi.longueur_emprise - 10.0
    A, B = np.array([xl, 0.0]), np.array([xl, pi.largeur_emprise])
    zone = Rectangle(pi.longueur_emprise - 3.0, pi.longueur_emprise, a[1] - 1.0, b[1] + 1.0)
    exact = r.sorties
    for K in ESPACEMENTS:
        i = np.unique(np.r_[np.arange(0, r.t.size, K), r.t.size - 1])
        t, x, e = r.t[i], r.x[i], r.etats[i]
        s = sorties_definitives(t, x, a, b)
        f = franchissements(t, x, A, B)
        duree = r.t[-1] + 1.0
        dens = np.array(
            [
                densite_comptage(x[k][e[k] == PLAGE], zone) if np.any(e[k] == PLAGE) else 0.0
                for k in range(i.size)
            ]
        )
        d = (x[1:] - x[:-1]) / np.diff(t)[:, None, None]
        plage = (e[1:] == PLAGE) & (e[:-1] == PLAGE)
        lignes.append(
            {
                "graine": g,
                "K": K,
                "sortis": int(s.sortis.sum()),
                "erreur_sortie_max_s": float(np.max(np.abs(s.instant[s.sortis] - exact[s.sortis]))),
                "t50": s.temps_evacuation(0.5),
                "t90": s.temps_evacuation(0.9),
                "t100": s.temps_evacuation(1.0),
                "passages_ligne": int(f.agent.size),
                "debit_ligne": debit_specifique(f, pi.largeur_emprise, 0.0, duree),
                "densite_pic": float(dens.max()),
                "vitesse_max_plage": float(np.linalg.norm(d, axis=-1)[plage].max()),
            }
        )
    print(g, flush=True)
Path(sys.argv[2]).write_text(
    json.dumps(
        {
            "configuration": source.as_posix(),
            "parametres": c,
            "code": code,
            "graines": list(GRAINES),
            "lignes": lignes,
        },
        indent=1,
    )
    + "\n",
    encoding="utf-8",
)
