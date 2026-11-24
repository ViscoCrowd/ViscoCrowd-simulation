"""Choix du site de sortie selon la file (D3) et coordination par un maitre-nageur (D5)."""

import numpy as np
import pytest

from viscocrowd.model.choix_site import (
    attribuer_coordonne,
    choisir,
    couts_sites,
    files_devant,
)

ATTENTES = np.array([[4.0, 0.2], [6.0, 0.2]])
DUREES = np.array([2.0, 2.0])


def test_files_devant_ne_compte_que_les_plus_proches():
    """#202 : trois nageurs visent le site 0, a 1, 2 et 3 m ; un quatrieme vise le site 1."""
    x = np.array([[4.0, 1.2], [4.0, 2.2], [4.0, 3.2], [6.0, 1.2]])
    files = files_devant(x, ATTENTES, np.array([0, 0, 0, 1]))
    np.testing.assert_array_equal(files[:, 0], [0, 1, 2, 2])
    np.testing.assert_array_equal(files[:, 1], [1, 1, 1, 0])


def test_le_premier_de_la_file_ne_compte_pas_ceux_de_derriere():
    """Revues de #188 : le plus proche d'un site y passerait le premier, il y reste."""
    x = np.array([[4.0, 0.7], [4.0, 1.5], [4.0, 2.0], [4.0, 2.5]])
    vises = np.array([-1, 0, 0, 0])
    couts = couts_sites(x, ATTENTES, 1.0, DUREES, np.zeros(2), files_devant(x, ATTENTES, vises))
    assert choisir(couts, vises, 0.0, np.ones((4, 2), dtype=bool))[0] == 0


def test_couts_additionnent_trajet_file_franchissement_et_suite():
    couts = couts_sites(
        np.array([[5.0, 1.0]]), ATTENTES, 1.0, DUREES, np.array([3.0, 0.0]), np.array([1, 0])
    )
    trajet = np.hypot(1.0, 0.8)
    np.testing.assert_allclose(couts, [[trajet + 2.0 + 2.0 + 3.0, trajet + 0.0 + 2.0 + 0.0]])


def test_la_file_detourne_vers_le_site_libre():
    couts = couts_sites(
        np.array([[5.0, 1.0]]), ATTENTES, 1.0, DUREES, np.zeros(2), np.array([3, 0])
    )
    assert choisir(couts, np.array([-1]), 1.0, np.ones((1, 2), dtype=bool))[0] == 1


def test_la_marge_evite_l_hesitation():
    couts = np.array([[10.0, 9.5]])
    assert choisir(couts, np.array([0]), 1.0, np.ones((1, 2), dtype=bool))[0] == 0
    assert choisir(couts, np.array([0]), 0.2, np.ones((1, 2), dtype=bool))[0] == 1


def test_aucun_site_a_portee():
    assert choisir(np.array([[1.0, 2.0]]), np.array([-1]), 1.0, np.zeros((1, 2), bool))[0] == -1


def test_site_actuel_hors_de_portee_est_abandonne():
    portee = np.array([[False, True]])
    assert choisir(np.array([[1.0, 5.0]]), np.array([0]), 1.0, portee)[0] == 1


def test_coordonne_equilibre_deux_sites_identiques():
    couts = np.zeros((6, 2))
    sites = attribuer_coordonne(couts, DUREES, np.arange(6))
    np.testing.assert_array_equal(np.bincount(sites, minlength=2), [3, 3])


def test_coordonne_envoie_moins_de_monde_au_site_lent():
    sites = attribuer_coordonne(np.zeros((6, 2)), np.array([2.0, 4.0]), np.arange(6))
    compte = np.bincount(sites, minlength=2)
    assert compte[1] < compte[0]


def test_coordonne_refuse_un_ordre_incomplet():
    with pytest.raises(ValueError):
        attribuer_coordonne(np.zeros((3, 2)), DUREES, np.array([0, 1]))
