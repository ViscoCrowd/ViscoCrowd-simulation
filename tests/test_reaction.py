"""Instants de reaction a l'alarme : loi log-normale, flux de tirage propre."""

import numpy as np
import pytest

from viscocrowd.model.reaction import FLUX_REACTION, instants_reaction


def test_dispersion_nulle():
    np.testing.assert_array_equal(instants_reaction(5, 3.0, 0.0, 1), np.full(5, 3.0))


def test_mediane_retrouvee():
    assert np.median(instants_reaction(20_000, 5.0, 0.5, 1)) == pytest.approx(5.0, rel=0.02)


def test_reproductible_et_propre_a_la_graine():
    a = instants_reaction(10, 5.0, 0.5, 7)
    np.testing.assert_array_equal(a, instants_reaction(10, 5.0, 0.5, 7))
    assert not np.array_equal(a, instants_reaction(10, 5.0, 0.5, 8))
    assert np.all(a > 0)


def test_flux_distinct_des_autres_tirages():
    assert FLUX_REACTION not in (0, 1, 2)  # positions initiales, chutes, navigation (#163)


@pytest.mark.parametrize(
    "mediane, dispersion", [(0.0, 0.5), (-1.0, 0.5), (5.0, -0.1), (np.nan, 0.5), (5.0, np.inf)]
)
def test_refus(mediane, dispersion):
    with pytest.raises(ValueError):
        instants_reaction(3, mediane, dispersion, 1)
