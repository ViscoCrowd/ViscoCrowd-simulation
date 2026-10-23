"""Archivage moins frequent : meme dynamique, memes evenements, controles a chaque pas."""

import json
import subprocess
from pathlib import Path

import numpy as np
import pytest
import yaml

from viscocrowd.cli import main
from viscocrowd.io.configuration import lire_configuration
from viscocrowd.io.trajectoires import lire_trajectoire
from viscocrowd.scenarios.experience import executer_configuration
from viscocrowd.scenarios.piscine import ParametresPiscine, simuler_piscine


@pytest.fixture
def configuration(tmp_path):
    config = lire_configuration(Path(__file__).parents[1] / "experiments/piscine.yaml")
    config["parametres"].update(n_agents=4, duree=0.055)
    fichier = tmp_path / "piscine.yaml"
    fichier.write_text(yaml.safe_dump(config))
    return fichier


def test_archivage_en_ligne_identique_sur_une_evacuation_complete():
    config = lire_configuration(Path(__file__).parents[1] / "experiments/piscine.yaml")
    p = ParametresPiscine(**(config["parametres"] | {"n_agents": 20}), graine=config["graine"])
    complet = simuler_piscine(p)
    espace = simuler_piscine(p, archiver_tous=37)
    indices = np.unique(np.r_[np.arange(0, len(complet.t), 37), len(complet.t) - 1])
    for nom in ("t", "x", "v", "etats"):
        np.testing.assert_array_equal(getattr(espace, nom), getattr(complet, nom)[indices])
    for nom in ("franchissements", "sorties", "rayons"):
        np.testing.assert_array_equal(getattr(espace, nom), getattr(complet, nom))
    assert espace.temps_evacuation() == complet.temps_evacuation()
    assert espace.projection.n_appels == complet.projection.n_appels
    assert espace.projection.recouvrement_max == complet.projection.recouvrement_max
    assert espace.violation_paroi_max() == complet.violation_paroi_max()
    assert espace.x.nbytes < complet.x.nbytes / 30


def test_archive_garde_dernier_pas_non_multiple_et_dt_physique(configuration, tmp_path):
    archive = tmp_path / "espace.npz"
    assert (
        main(["simuler", str(configuration), "--sortie", str(archive), "--archiver-tous", "4"]) == 0
    )
    donnees = lire_trajectoire(archive)
    np.testing.assert_array_equal(donnees.t, [0.0, 0.04, 0.06])
    assert donnees.metadonnees["archivage"]["dt_simulation_s"] == 0.01
    assert donnees.metadonnees["archivage"]["tous_les_pas"] == 4
    assert donnees.metadonnees["configuration"]["parametres"]["dt"] == 0.01


def test_violation_sur_pas_non_archive_refuse_publication(configuration, tmp_path, monkeypatch):
    from viscocrowd.geometry.piscine import Piscine

    original = Piscine.violation

    def violation(self, x, r, t):
        return 0.25 if t == 0.02 else original(self, x, r, t)

    monkeypatch.setattr(Piscine, "violation", violation)
    with pytest.raises(ValueError, match="violation des parois"):
        executer_configuration(configuration, tmp_path / "invalide.npz", archiver_tous=4)
    assert not (tmp_path / "invalide.npz").exists()


@pytest.mark.parametrize("intervalle", [0, -1, True, 1.5])
def test_intervalle_invalide(configuration, tmp_path, intervalle):
    with pytest.raises(ValueError, match="entier"):
        executer_configuration(configuration, tmp_path / "invalide.npz", archiver_tous=intervalle)


def test_banc_reel_dans_des_processus_neufs(configuration, tmp_path):
    sortie = tmp_path / "mesures.json"
    args = [
        "mesurer-performances",
        str(configuration),
        "--effectifs",
        "2",
        "4",
        "--archiver-tous",
        "1",
        "4",
        "--sortie",
        str(sortie),
    ]
    assert main(args) == 0
    rapport = json.loads(sortie.read_text())
    assert len(rapport["mesures"]) == 4
    for ligne in rapport["mesures"]:
        assert ligne["statut"] == "termine"
        assert ligne["temps_simulation_validation_archive_s"] > 0
        assert ligne["tableaux_conserves_octets"] > 0
        assert ligne["archive_npz_octets"] > 0
        assert ligne["pic_rss_processus_octets"] is None or ligne["pic_rss_processus_octets"] > 0
        assert ligne["instants_archives"] == (7 if ligne["archiver_tous"] == 1 else 3)
    avant = sortie.read_bytes()
    assert main(args) == 1
    assert sortie.read_bytes() == avant


def test_echec_d_un_enfant_est_visible(configuration, tmp_path, monkeypatch):
    from viscocrowd.scenarios import performances

    monkeypatch.setattr(
        performances.subprocess,
        "run",
        lambda *a, **k: subprocess.CompletedProcess(
            a, 1, stdout="", stderr="projection non convergee"
        ),
    )
    sortie = tmp_path / "mesures.json"
    assert (
        main(
            [
                "mesurer-performances",
                str(configuration),
                "--effectifs",
                "2",
                "--sortie",
                str(sortie),
            ]
        )
        == 1
    )
    ligne = json.loads(sortie.read_text())["mesures"][0]
    assert ligne["statut"] == "echec"
    assert ligne["erreur"] == "projection non convergee"
    assert "pic_rss_processus_octets" not in ligne


def test_refus_avant_calcul(configuration, tmp_path):
    from viscocrowd.scenarios.performances import mesurer_performances

    for effectifs in ([0], [4, 4], [100000]):
        with pytest.raises(ValueError):
            mesurer_performances(
                configuration, tmp_path / "a.json", effectifs=effectifs, intervalles=[1]
            )
    assert not (tmp_path / "a.json").exists()
