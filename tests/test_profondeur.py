"""Profondeur variable du bassin : vitesse des nageurs selon la profondeur (option)."""

import numpy as np
import pytest

from viscocrowd.geometry.obstacle import ObstacleRectangle
from viscocrowd.model.profondeur import (
    PROFONDEUR_MAX,
    PROFONDEUR_MIN,
    PROFONDEUR_REFERENCE,
    facteur_profondeur,
    profondeur,
)


def test_bornes_et_reference():
    assert (PROFONDEUR_MIN, PROFONDEUR_REFERENCE, PROFONDEUR_MAX) == (0.2, 0.7, 1.0)


def test_facteur_a_la_reference():
    assert facteur_profondeur(np.array([0.7]))[0] == 1.0


def test_facteur_suit_la_loi_de_puissance():
    # V = 0,53 (d^2/2)^-0,19, donc V(d)/V(0,7) = (d/0,7)^-0,38
    np.testing.assert_allclose(facteur_profondeur(np.array([1.0])), [0.8733], atol=1e-4)
    np.testing.assert_allclose(facteur_profondeur(np.array([0.35])), [1.3013], atol=1e-4)


def test_profondeur_lineaire_et_bornee():
    bassin = ObstacleRectangle(3.0, 28.0, 4.0, 16.5)
    x = np.array([[3.0, 8.0], [15.5, 8.0], [28.0, 8.0], [40.0, 8.0], [0.0, 8.0]])
    np.testing.assert_allclose(profondeur(x, bassin, 1.0, 0.7), [1.0, 0.85, 0.7, 0.7, 1.0])


@pytest.mark.parametrize("d", [0.1, 1.2, np.nan])
def test_facteur_hors_domaine_refuse(d):
    with pytest.raises(ValueError):
        facteur_profondeur(np.array([d]))
