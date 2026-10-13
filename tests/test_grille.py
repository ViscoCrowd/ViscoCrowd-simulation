"""Tests de la recherche de voisins : la grille doit donner EXACTEMENT la force brute."""

import numpy as np
import pytest

from viscocrowd.core.rng import generateur
from viscocrowd.geometry.grille import paires_candidates, recouvrement_max


def paires_force_brute(x, r, marge=0.0):
    """Reference lente et evidente : on teste les N(N-1)/2 paires."""
    n = x.shape[0]
    return np.array(
        [
            (i, j)
            for i in range(n)
            for j in range(i + 1, n)
            if np.linalg.norm(x[i] - x[j]) < r[i] + r[j] + marge
        ],
        dtype=np.int64,
    ).reshape(-1, 2)


@pytest.mark.parametrize("graine", range(8))
@pytest.mark.parametrize("marge", [0.0, 0.03])
def test_identique_a_la_force_brute(graine, marge):
    rng = generateur(graine)
    n = 150
    x = rng.uniform(-1.0, 1.0, size=(n, 2))
    r = rng.uniform(0.02, 0.08, size=n)  # rayons heterogenes

    np.testing.assert_array_equal(paires_candidates(x, r, marge), paires_force_brute(x, r, marge))


def test_coordonnees_negatives_et_loin_de_l_origine():
    """La grille est ancree sur le minimum des positions, pas sur l'origine."""
    rng = generateur(3)
    x = rng.uniform(-500.0, -499.0, size=(80, 2))
    r = np.full(80, 0.05)
    np.testing.assert_array_equal(paires_candidates(x, r), paires_force_brute(x, r))


def test_cas_triviaux():
    r = np.array([0.1, 0.1])
    assert paires_candidates(np.empty((0, 2)), np.empty(0)).shape == (0, 2)
    assert paires_candidates(np.zeros((1, 2)), np.array([0.1])).shape == (0, 2)
    # Deux disques tangents ne se recouvrent pas : inegalite stricte.
    assert paires_candidates(np.array([[0.0, 0.0], [0.2, 0.0]]), r).shape == (0, 2)
    np.testing.assert_array_equal(
        paires_candidates(np.array([[0.0, 0.0], [0.19, 0.0]]), r), [[0, 1]]
    )


def test_disques_confondus():
    x = np.zeros((3, 2))
    r = np.full(3, 0.1)
    np.testing.assert_array_equal(paires_candidates(x, r), [[0, 1], [0, 2], [1, 2]])


def test_marge_negative_refusee():
    with pytest.raises(ValueError, match="marge"):
        paires_candidates(np.zeros((2, 2)), np.full(2, 0.1), marge=-1.0)


def test_recouvrement_max():
    r = np.array([0.1, 0.1, 0.1])
    x = np.array([[0.0, 0.0], [0.15, 0.0], [5.0, 5.0]])
    assert recouvrement_max(x, r) == pytest.approx(0.05)
    assert recouvrement_max(np.array([[0.0, 0.0], [1.0, 0.0]]), r[:2]) == 0.0


@pytest.mark.parametrize("valeur", [np.nan, np.inf, -np.inf])
def test_position_non_finie_rejetee(valeur):
    """Un NaN rend toutes les comparaisons fausses : sans ce refus, recouvrement_max
    annoncait 0 pour une configuration corrompue (issue #16)."""
    x = np.array([[0.0, 0.0], [valeur, 0.0]])
    r = np.full(2, 0.1)
    with pytest.raises(ValueError, match="non finies"):
        paires_candidates(x, r)
    with pytest.raises(ValueError, match="non finies"):
        recouvrement_max(x, r)


def test_rayon_non_fini_rejete():
    with pytest.raises(ValueError, match="non finies"):
        paires_candidates(np.array([[0.0, 0.0], [1.0, 0.0]]), np.array([0.1, np.nan]))
