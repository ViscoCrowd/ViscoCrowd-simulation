"""Tests du protocole de comparaison appariee E1/E2 de la piscine."""

from dataclasses import asdict
from pathlib import Path

import numpy as np
import pytest
import yaml

import viscocrowd.scenarios.comparaison_piscine as mod_comp
from viscocrowd.cli import main
from viscocrowd.io.configuration import lire_configuration
from viscocrowd.model.milieu import ParametresMilieu
from viscocrowd.scenarios.comparaison_piscine import (
    LIBELLES,
    MESURES,
    VARIANTES,
    ProtocoleIncomplet,
    comparer,
    mesurer,
    mouille_de_variante,
    regrouper_variantes,
)
from viscocrowd.scenarios.piscine import ParametresPiscine

EXEMPLE = Path(__file__).parents[1] / "experiments/piscine.yaml"
COULOIR = Path(__file__).parents[1] / "experiments/couloir.yaml"
SEC = ParametresMilieu(relaxation=0.5, acceleration_max=5.9, vitesse=1.34)
MOUILLE = ParametresMilieu(relaxation=0.5, acceleration_max=3.3, vitesse=1.34)
MOUILLE_DISTINCT = ParametresMilieu(relaxation=0.8, acceleration_max=3.3, vitesse=1.10)


@pytest.mark.parametrize("nom", list(VARIANTES))
def test_chaque_variante_ne_reprend_que_ses_parametres(nom):
    variante = asdict(mouille_de_variante(nom, SEC, MOUILLE_DISTINCT))
    for champ, valeur in variante.items():
        attendu = getattr(MOUILLE_DISTINCT if champ in VARIANTES[nom] else SEC, champ)
        assert valeur == attendu


def test_variante_reference_strictement_identique_au_sec():
    variante = mouille_de_variante("reference", SEC, MOUILLE_DISTINCT)
    assert variante == SEC


def test_variante_inconnue_refusee():
    with pytest.raises(ValueError, match="variante inconnue"):
        mouille_de_variante("savon", SEC, MOUILLE)


def test_regrouper_variantes_fusionne_les_milieux_identiques():
    groupes = regrouper_variantes(SEC, MOUILLE)
    assert list(groupes) == ["reference", "complet"]
    assert groupes["reference"] == ("reference", "vitesse", "relaxation")
    assert groupes["complet"] == ("adherence", "vitesse+adherence", "complet")

    distincts = regrouper_variantes(SEC, MOUILLE_DISTINCT)
    assert list(distincts) == list(VARIANTES)
    assert all(len(eq) == 1 for eq in distincts.values())


def test_comparer_refuse_liste_graines_vide_ou_en_double():
    config = lire_configuration(EXEMPLE)
    with pytest.raises(ValueError, match="au moins une graine"):
        comparer(config, [])
    with pytest.raises(ValueError, match="graines doivent etre distinctes"):
        comparer(config, [7, 7])
    with pytest.raises(ValueError, match="entier positif ou nul"):
        comparer(config, [True])  # type: ignore[list-item]


def test_comparer_refuse_variante_invalide_ou_en_double():
    config = lire_configuration(EXEMPLE)
    with pytest.raises(ValueError, match="au moins une variante"):
        comparer(config, [42], variantes=[])
    with pytest.raises(ValueError, match="variante inconnue"):
        comparer(config, [42], variantes=["inexistant"])
    with pytest.raises(ValueError, match="variantes doivent etre distinctes"):
        comparer(config, [42], variantes=["reference", "reference"])


def _petite_configuration(n_agents: int = 4, duree: float = 40.0) -> dict:
    config = lire_configuration(EXEMPLE)
    config["parametres"].update(
        {
            "n_agents": n_agents,
            "duree": duree,
            "durees": {"rebord": 1.0, "echelle": 0.5},
        }
    )
    return config


def test_mesurer_rend_toutes_les_mesures_attendues():
    config = _petite_configuration()
    p = ParametresPiscine(**config["parametres"], graine=config["graine"])
    mesures = mesurer(p)
    assert set(mesures) == set(MESURES)
    assert all(np.isfinite(mesures[m]) for m in MESURES)
    assert mesures["t50"] <= mesures["t90"] <= mesures["t100"]


def test_mesurer_refuse_protocole_incomplet():
    # Duree trop courte : aucun agent n'a le temps de franchir le bassin ni de sortir
    config_eau = _petite_configuration(n_agents=4, duree=0.2)
    p_eau = ParametresPiscine(**config_eau["parametres"], graine=1)
    with pytest.raises(ProtocoleIncomplet, match="non sortis avant"):
        mesurer(p_eau)


def test_comparer_apparie_les_graines_et_mutualise_les_variantes_identiques(monkeypatch):
    config = _petite_configuration()
    graines = [101, 102]
    appels = []
    vrai_mesurer = mod_comp.mesurer

    def espion(p: ParametresPiscine) -> dict[str, float]:
        appels.append((p.graine, p.parametres_milieux))
        return vrai_mesurer(p)

    monkeypatch.setattr(mod_comp, "mesurer", espion)
    resultats = comparer(config, graines)

    assert set(resultats) == set(VARIANTES)
    # 2 groupes distincts (SEC vs MOUILLE) x 2 graines = 4 simulations au lieu de 12
    assert len(appels) == 2 * len(graines)
    np.testing.assert_array_equal(resultats["reference"], resultats["vitesse"])
    np.testing.assert_array_equal(resultats["reference"], resultats["relaxation"])
    np.testing.assert_array_equal(resultats["complet"], resultats["adherence"])
    np.testing.assert_array_equal(resultats["complet"], resultats["vitesse+adherence"])


def test_cli_comparer_piscine_aide(capsys):
    with pytest.raises(SystemExit) as capture:
        main(["comparer-piscine", "--help"])
    assert capture.value.code == 0
    sortie = capsys.readouterr().out
    assert "E1/E2" in sortie


def test_cli_comparer_piscine_bout_en_bout(tmp_path, capsys):
    config = _petite_configuration(n_agents=4, duree=40.0)
    fichier = tmp_path / "piscine_test.yaml"
    fichier.write_text(yaml.safe_dump(config), encoding="utf-8")

    code = main(["comparer-piscine", str(fichier), "--graines", "101", "102"])
    assert code == 0
    sortie = capsys.readouterr().out
    assert LIBELLES["reference"] in sortie
    assert LIBELLES["complet"] in sortie
    assert "Variantes identiques fusionnees" in sortie
    assert "étendue (min -- max)" in sortie
    assert "écart apparié Δ vs E1" in sortie


def test_cli_comparer_piscine_affiche_tiret_si_debit_indefini(tmp_path, capsys):
    # Avec 1 seul agent, debit_seyfried renvoie NaN -> la colonne debit_porte affiche "-"
    config = _petite_configuration(n_agents=1, duree=40.0)
    fichier = tmp_path / "piscine_1agent.yaml"
    fichier.write_text(yaml.safe_dump(config), encoding="utf-8")

    code = main(["comparer-piscine", str(fichier), "--variantes", "reference"])
    assert code == 0
    sortie = capsys.readouterr().out
    assert LIBELLES["reference"] in sortie
    assert " -\n" in sortie


def test_cli_comparer_piscine_erreurs(tmp_path, capsys):
    # Mauvais scenario
    code = main(["comparer-piscine", str(COULOIR)])
    assert code == 1
    assert "Comparaison refusee" in capsys.readouterr().err

    # Protocole incomplet (duree trop courte)
    config = _petite_configuration(n_agents=4, duree=0.2)
    fichier = tmp_path / "piscine_courte.yaml"
    fichier.write_text(yaml.safe_dump(config), encoding="utf-8")
    code_court = main(["comparer-piscine", str(fichier)])
    assert code_court == 1
    err = capsys.readouterr().err
    assert "Comparaison refusee" in err
    assert "non sortis" in err
