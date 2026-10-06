"""Generation aleatoire reproductible.

Les consignes du module exigent une graine fixee, afin que les executions
soient reproductibles. Tout tirage aleatoire du projet passe par ici : on
n'appelle jamais numpy.random directement, ce qui garantit qu'aucune source
d'alea ne peut echapper a la graine declaree dans la configuration.
"""

from __future__ import annotations

import numpy as np

GRAINE_PAR_DEFAUT = 20262027


def generateur(graine: int | None = None) -> np.random.Generator:
    """Generateur aleatoire initialise par une graine explicite.

    Args:
        graine: graine entiere. Si None, la graine par defaut du projet est
            utilisee, de sorte qu'un oubli ne produise jamais une execution
            non reproductible.
    """
    return np.random.default_rng(GRAINE_PAR_DEFAUT if graine is None else graine)
