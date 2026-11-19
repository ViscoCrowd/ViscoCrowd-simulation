"""Reference figee : detecter un changement involontaire de la simulation de reference.

Les options du modele s'accumulent (chutes, deblocage, navigation, egouttage...), chacune
« desactivee par defaut, reference identique au bit pres ». Ce test le verifie a chaque PR :
20 baigneurs de `experiments/piscine.yaml`, instants de sortie compares a ceux enregistres
dans `tests/donnees/reference_piscine.json`, a 1e-6 s pres (marge pour les differences de
plate-forme entre les postes Windows et la CI Linux).

Une PR qui change VOLONTAIREMENT la reference regenere le fichier dans la meme PR, par
`python tests/donnees/regenerer_reference.py`, et l'explique dans sa description.
"""

import json
from pathlib import Path

import numpy as np

from viscocrowd.io.configuration import lire_configuration
from viscocrowd.scenarios.piscine import ParametresPiscine, simuler_piscine

EXEMPLE = Path(__file__).parents[1] / "experiments/piscine.yaml"
FICHIER = Path(__file__).parent / "donnees/reference_piscine.json"
N_AGENTS = 20  # environ 3 s de calcul, comme la fixture `evacuation` du scenario
TOLERANCE_S = 1e-6


def mesurer_reference() -> dict:
    """Sorties (s), t50, t100, deblocages et franchissements de la reference a 20 agents."""
    config = lire_configuration(EXEMPLE)
    p = ParametresPiscine(
        **(config["parametres"] | {"n_agents": N_AGENTS}), graine=config["graine"]
    )
    r = simuler_piscine(p)
    sorties = np.sort(r.sorties[np.isfinite(r.sorties)])
    return {
        "sorties": [float(s) for s in r.sorties],
        "t50": float(sorties[(len(sorties) - 1) // 2]),
        "t100": float(sorties[-1]),
        "deblocages": int(r.deblocages),
        "franchissements": len(r.franchissements),
    }


def test_reference_inchangee():
    attendu = json.loads(FICHIER.read_text(encoding="utf-8"))
    obtenu = mesurer_reference()
    np.testing.assert_allclose(obtenu["sorties"], attendu["sorties"], rtol=0, atol=TOLERANCE_S)
    assert obtenu["deblocages"] == attendu["deblocages"]
    assert obtenu["franchissements"] == attendu["franchissements"]
