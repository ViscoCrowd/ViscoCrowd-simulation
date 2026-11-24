"""#202 : le choix du site compte-t-il la bonne file ?

Question, ecrite avant le calcul. Dans #188, `files_par_site` compte tous les nageurs qui
visent un site, y compris ceux plus loin de son point d'attente que le nageur qui choisit.
Le plus proche d'une echelle surestime donc son attente et part vers un rebord alors qu'il
passerait le premier (revues de Shaleena et de Lenny). Ne compter que les nageurs plus pres
du point d'attente (« la file devant moi ») devrait rendre des sorties aux echelles (6,0 %
avec l'ancienne regle, 23,7 % sans choix du site). Effet sur t100 : aucune attente
particuliere.

Protocole : reference `experiments/piscine.yaml` (mouille), graines 1 a 10, sans choix du
site et choix local {portee: 3, periode: 1, marge: 1}, comme le journal du 18 novembre. Le
script tourne deux fois, sur deux commits propres : `avant` (ancienne regle) et `apres`
(file devant soi). Il ecrit t100 et la part des franchissements par les echelles, graine par
graine.

Critere, fixe avant le calcul (`criteres-acceptation.md`, § 3) : la nouvelle regle change
l'evacuation si l'ecart apparie de t100 (apres - avant, choix local) a le meme signe sur au
moins 9 graines sur 10. La part des echelles est rapportee sans seuil.

Usage, depuis la racine du depot (arbre propre) :
    python docs/mesures/choix-site-file-devant-2026-11-20/mesurer.py experiments/piscine.yaml \
        avant docs/mesures/choix-site-file-devant-2026-11-20/avant.json
"""

import json
import sys
from multiprocessing import Pool
from pathlib import Path

import numpy as np

from viscocrowd.io.configuration import lire_configuration
from viscocrowd.scenarios.campagne import contexte
from viscocrowd.scenarios.piscine import ParametresPiscine, simuler_piscine

GRAINES = tuple(range(1, 11))
LOCAL = {"portee": 3.0, "periode": 1.0, "marge": 1.0, "mode": "local"}
VARIANTES = {"sans": None, "local": LOCAL}


def simuler(cas):
    variante, graine = cas
    config = lire_configuration(Path(sys.argv[1]))
    parametres = config["parametres"] | {"choix_site": VARIANTES[variante]}
    r = simuler_piscine(ParametresPiscine(**parametres, graine=graine))
    sites = r.franchissements[:, 1].astype(int)
    echelles = sum(r.natures[k] == "echelle" for k in sites)
    return (
        variante,
        graine,
        {
            "t100": r.temps_evacuation(1.0),
            "franchissements": int(sites.size),
            "par_echelles": int(echelles),
        },
    )


if __name__ == "__main__":
    etiquette, sortie = sys.argv[2], Path(sys.argv[3])
    if sortie.exists():
        raise SystemExit(f"{sortie} existe deja")
    ctx = contexte()
    cas = [(v, g) for v in VARIANTES for g in GRAINES]
    with Pool(len(cas)) as pool:
        resultats = pool.map(simuler, cas)
    mesures = {v: {g: m for vv, g, m in resultats if vv == v} for v in VARIANTES}
    print(f"Regle : {etiquette}")
    for v in VARIANTES:
        t100 = np.array([mesures[v][g]["t100"] for g in GRAINES])
        part = sum(mesures[v][g]["par_echelles"] for g in GRAINES) / sum(
            mesures[v][g]["franchissements"] for g in GRAINES
        )
        print(f"  {v:5s} : t100 {t100.mean():.2f} ± {t100.std(ddof=1):.2f} s, echelles {part:.1%}")
    bilan = {
        "version": 1,
        "regle": etiquette,
        "contexte": ctx,
        "graines": GRAINES,
        "local": LOCAL,
        "mesures": {v: {str(g): mesures[v][g] for g in GRAINES} for v in VARIANTES},
    }
    sortie.parent.mkdir(parents=True, exist_ok=True)
    sortie.write_text(json.dumps(bilan, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Bilan : {sortie}")
