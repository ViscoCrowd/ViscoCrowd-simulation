"""Intervalles entre sorties successives : la signature des bouchons (Zuriguel et al., 2014)."""

import numpy as np
import pytest

from viscocrowd.observables.bouchage import intervalles_sorties, resumer, survie


def test_intervalles_ignorent_les_non_sortis_et_trient():
    sorties = np.array([5.0, 0.0, np.nan, 1.0, 2.0])
    np.testing.assert_array_equal(intervalles_sorties(sorties), [1.0, 1.0, 3.0])


@pytest.mark.parametrize("sorties", [np.array([]), np.array([3.0]), np.array([np.nan, 2.0])])
def test_moins_de_deux_sorties(sorties):
    assert intervalles_sorties(sorties).size == 0


def test_survie_stricte():
    intervalles = np.array([1.0, 1.0, 3.0])
    np.testing.assert_allclose(
        survie(intervalles, np.array([0.5, 1.0, 2.0, 3.0])), [1.0, 1 / 3, 1 / 3, 0.0]
    )


def test_survie_sans_intervalle():
    assert np.all(np.isnan(survie(np.array([]), np.array([1.0, 2.0]))))


def test_resumer_signale_une_evacuation_incomplete():
    r = resumer(np.array([0.0, 1.0, np.nan]), seuil_bouchon=0.5)
    assert r["incomplete"] == 1 and r["n_sortis"] == 2
    assert r["p_bouchon"] == 1.0 and r["mediane"] == 1.0 and r["max"] == 1.0


def test_resumer_evacuation_complete():
    r = resumer(np.array([0.0, 0.2, 0.4, 2.4]), seuil_bouchon=1.0)
    assert r["incomplete"] == 0 and r["n_sortis"] == 4
    assert r["p_bouchon"] == pytest.approx(1 / 3) and r["max"] == pytest.approx(2.0)


def test_commande_bouchons(tmp_path, capsys):
    from utilitaires import simuler_archive_reduite
    from viscocrowd.cli import main

    for dossier in ("complete", "courte"):
        (tmp_path / dossier).mkdir()
    complete = simuler_archive_reduite(tmp_path / "complete" / "a.npz", duree=60.0)
    courte = simuler_archive_reduite(tmp_path / "courte" / "b.npz", duree=2.0)
    image = tmp_path / "bouchons.png"
    commande = ["bouchons", str(complete), str(courte), "--etiquettes", "complète", "courte"]
    assert main([*commande, "--image", str(image)]) == 0
    assert image.stat().st_size > 0
    sortie = capsys.readouterr().out
    assert "complète" in sortie and "courte" in sortie
    assert "1 évacuation(s) incomplète(s)" in sortie


def test_commande_bouchons_refuse_des_etiquettes_mal_comptees(tmp_path, capsys):
    from viscocrowd.cli import main

    image = tmp_path / "b.png"
    assert main(["bouchons", "a.npz", "b.npz", "--etiquettes", "x", "--image", str(image)]) == 1
    assert "etiquette" in capsys.readouterr().err
