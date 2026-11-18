"""Choix du site de sortie dans la piscine (D3, D5) : facultatif, evacuation complete."""

import numpy as np
import pytest

from utilitaires import parametres_reduits
from viscocrowd.scenarios.piscine import simuler_piscine

LOCAL = {"portee": 3.0, "periode": 1.0, "marge": 1.0}


def test_sans_choix_identique_au_bit_pres():
    a = simuler_piscine(parametres_reduits())
    b = simuler_piscine(parametres_reduits(choix_site=None))
    np.testing.assert_array_equal(a.x, b.x)


@pytest.mark.parametrize("mode", ["local", "coordonne"])
def test_evacuation_complete_avec_choix(mode):
    r = simuler_piscine(
        parametres_reduits(n_agents=30, duree=120.0, choix_site=LOCAL | {"mode": mode})
    )
    assert np.all(np.isfinite(r.sorties))
    assert r.violation_paroi_max() <= 1e-14


def test_le_choix_change_l_evacuation():
    sans = simuler_piscine(parametres_reduits(n_agents=30, duree=120.0))
    avec = simuler_piscine(parametres_reduits(n_agents=30, duree=120.0, choix_site=LOCAL))
    assert not np.array_equal(sans.franchissements, avec.franchissements)


@pytest.mark.parametrize(
    "valeur",
    [{"portee": 3.0}, LOCAL | {"marge": -1.0}, LOCAL | {"mode": "magique"}],
)
def test_choix_mal_forme_refuse(valeur):
    with pytest.raises(ValueError, match="choix_site"):
        parametres_reduits(choix_site=valeur)
