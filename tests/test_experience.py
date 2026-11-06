"""C7 : configurations reproductibles, publication seulement apres validation."""

from pathlib import Path

import numpy as np
import pytest
import yaml

from viscocrowd.cli import main
from viscocrowd.geometry.projection import ProjectionExclusion, ProjectionNonConvergee
from viscocrowd.io.configuration import lire_configuration
from viscocrowd.io.trajectoires import lire_trajectoire
from viscocrowd.observables.energie import energie_mecanique
from viscocrowd.scenarios.experience import executer_configuration


def configurer(tmp_path, scenario="tassement", graine=7, **parametres):
    config = {
        "version": 1,
        "scenario": scenario,
        "graine": graine if scenario == "tassement" else None,
        "parametres": {"dt": 0.002, "duree": 0.02, **parametres},
    }
    if scenario == "tassement":
        config["parametres"].setdefault("n_agents", 4)
    chemin = tmp_path / "config.yaml"
    chemin.write_text(yaml.safe_dump(config), encoding="utf-8")
    return chemin


@pytest.mark.parametrize("scenario", ["bille_boite", "tassement"])
def test_execution_et_relecture_exactes_a_configuration_fixee(tmp_path, scenario):
    config = configurer(tmp_path, scenario)
    a = executer_configuration(config, tmp_path / "a.npz")
    b = executer_configuration(config, tmp_path / "b.npz")
    relue = lire_trajectoire(tmp_path / "a.npz")
    for nom in ("t", "x", "v", "rayons"):
        np.testing.assert_array_equal(getattr(a, nom), getattr(b, nom))
        np.testing.assert_array_equal(getattr(a, nom), getattr(relue, nom))
    assert a.metadonnees == relue.metadonnees
    effectifs = relue.metadonnees["configuration"]
    assert effectifs["parametres"]["gravite"] == [0.0, -9.81]
    assert effectifs["graine"] == (7 if scenario == "tassement" else None)
    assert relue.metadonnees["versions"]["numpy"] == np.__version__
    assert relue.metadonnees["unites"]["x"] == "m"
    # Les valeurs effectives doivent aussi permettre de reconstruire la configuration.
    config.write_text(yaml.safe_dump(effectifs), encoding="utf-8")
    rejouee = executer_configuration(config, tmp_path / "rejouee.npz")
    np.testing.assert_array_equal(rejouee.x, a.x)
    np.testing.assert_array_equal(rejouee.v, a.v)


def test_graine_change_positions_initiales(tmp_path):
    a = executer_configuration(configurer(tmp_path, graine=7), tmp_path / "a.npz")
    b = executer_configuration(configurer(tmp_path, graine=8), tmp_path / "b.npz")
    assert not np.array_equal(a.x[0], b.x[0])


def test_observable_hors_ligne_identique_et_energie_decroissante(tmp_path):
    config = configurer(tmp_path, "bille_boite", omega=0.0, duree=1.0)
    a = executer_configuration(config, tmp_path / "a.npz")
    relue = lire_trajectoire(tmp_path / "a.npz")
    energie = energie_mecanique(relue.x, relue.v)
    np.testing.assert_array_equal(energie, energie_mecanique(a.x, a.v))
    assert np.max(np.diff(energie)) <= 1e-12


@pytest.mark.parametrize(
    ("parametres", "message"),
    [
        ({"dt": 0}, "dt"),
        ({"dt": "0.01"}, "dt"),
        ({"dt": True}, "dt"),
        ({"rayon": np.nan}, "rayon"),
        ({"duree": -1}, "duree"),
        ({"n_agents": 1.5}, "n_agents"),
        ({"n_agents": True}, "n_agents"),
        ({"n_agents": 0}, "n_agents"),
        ({"rayon": 1.0}, "rayon"),
        ({"gravite": [0.0]}, "gravite"),
        ({"gravite": [0.0, np.inf]}, "gravite"),
        ({"gravite": [False, True]}, "gravite"),
        ({"typo": 1}, "inconnus"),
    ],
)
def test_parametres_invalides_ne_produisent_aucune_archive(tmp_path, parametres, message):
    config = configurer(tmp_path, **parametres)
    with pytest.raises(ValueError, match=message):
        executer_configuration(config, tmp_path / "a.npz")
    assert not (tmp_path / "a.npz").exists()


@pytest.mark.parametrize("graine", [None, -1, True, 1.2])
def test_graine_explicitement_entiere_requise(tmp_path, graine):
    with pytest.raises(ValueError, match="graine"):
        lire_configuration(configurer(tmp_path, graine=graine))


@pytest.mark.parametrize(
    "texte",
    ["", "[]", "version: 1\nversion: 2", "version: [", "!!python/object:invalide {}"],
)
def test_yaml_invalide_refuse(tmp_path, texte):
    chemin = tmp_path / "config.yaml"
    chemin.write_text(texte)
    with pytest.raises(ValueError):
        lire_configuration(chemin)


def test_non_convergence_reelle_interdit_publication(tmp_path, monkeypatch):
    # Un seul balayage ne suffit pas lorsque les deux rangees atteignent le sol.
    def budget_reduit(*args, **kwargs):
        return ProjectionExclusion(*args, **kwargs, iterations=1)

    monkeypatch.setattr("viscocrowd.scenarios.tassement.ProjectionExclusion", budget_reduit)
    config = configurer(tmp_path, n_agents=16, duree=0.8)
    with pytest.raises(ProjectionNonConvergee):
        executer_configuration(config, tmp_path / "a.npz")
    assert not (tmp_path / "a.npz").exists()


def test_depart_hors_boite_refuse_meme_sans_pas(tmp_path):
    config = configurer(tmp_path, "bille_boite", duree=0.0, position_initiale=[2.0, 0.0])
    with pytest.raises(ValueError, match="positions initiales"):
        executer_configuration(config, tmp_path / "a.npz")


def test_cli_et_refus_d_ecraser(tmp_path, capsys):
    config = configurer(tmp_path)
    sortie = tmp_path / "sous-dossier" / "resultat.npz"
    args = ["simuler", str(config), "--sortie", str(sortie)]
    assert main(args) == 0
    assert "4 agent(s), 11 instants" in capsys.readouterr().out
    original = sortie.read_bytes()
    assert main(args) == 1
    assert "existe deja" in capsys.readouterr().err
    assert sortie.read_bytes() == original


@pytest.mark.parametrize("nom", ["bille_boite", "tassement"])
def test_exemples_versionnes_lisibles(nom):
    config = lire_configuration(Path(__file__).parents[1] / "experiments" / f"{nom}.yaml")
    assert config["scenario"] == nom
