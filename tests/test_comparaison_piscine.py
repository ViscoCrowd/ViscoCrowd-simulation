"""Tests du protocole de comparaison appariee E1/E2 de la piscine."""

from dataclasses import asdict
from pathlib import Path

import numpy as np
import pytest

from viscocrowd.cli import main
from viscocrowd.io.configuration import lire_configuration
from viscocrowd.model.milieu import ParametresMilieu
from viscocrowd.scenarios.comparaison_piscine import (
    MESURES,
    VARIANTES,
    comparer,
    mesurer,
    mouille_de_variante,
)
from viscocrowd.scenarios.piscine import ParametresPiscine

EXEMPLE = Path(__file__).parents[1] / "experiments/piscine.yaml"
SEC = ParametresMilieu(relaxation=0.5, acceleration_max=5.9, vitesse=1.34)
MOUILLE = ParametresMilieu(relaxation=0.5, acceleration_max=3.3, vitesse=1.34)


@pytest.mark.parametrize("nom", list(VARIANTES))
def test_chaque_variante_ne_reprend_que_ses_parametres(nom):
    variante = asdict(mouille_de_variante(nom, SEC, MOUILLE))
    for champ, valeur in variante.items():
        attendu = getattr(MOUILLE if champ in VARIANTES[nom] else SEC, champ)
        assert valeur == attendu


def test_variante_reference_strictement_identique_au_sec():
    variante = mouille_de_variante("reference", SEC, MOUILLE)
    assert variante == SEC


def test_variante_inconnue_refusee():
    with pytest.raises(ValueError, match="variante inconnue"):
        mouille_de_variante("savon", SEC, MOUILLE)


def test_comparer_refuse_liste_graines_vide():
    config = lire_configuration(EXEMPLE)
    with pytest.raises(ValueError, match="au moins une graine"):
        comparer(config, [])


def test_comparer_refuse_variante_invalide():
    config = lire_configuration(EXEMPLE)
    with pytest.raises(ValueError, match="variante inconnue"):
        comparer(config, [42], variantes=["inexistant"])


def _petite_configuration() -> dict:
    config = lire_configuration(EXEMPLE)
    # Configuration reduite pour un test unitaire rapide (~1 s)
    config["parametres"].update(
        {
            "n_agents": 4,
            "duree": 40.0,
            "durees": {"rebord": 1.0, "echelle": 0.5},
        }
    )
    return config


def test_mesurer_rend_toutes_les_mesures_attendues():
    config = _petite_configuration()
    p = ParametresPiscine(**config["parametres"], graine=config["graine"])
    mesures = mesurer(p)
    assert set(mesures) == set(MESURES)
    for nom in ("t50", "t90", "t100", "attente_eau", "duree_plage", "debit_porte"):
        assert nom in mesures
    assert 0 <= mesures["non_sortis"] <= p.n_agents
    if np.isfinite(mesures["t50"]) and np.isfinite(mesures["t90"]):
        assert mesures["t50"] <= mesures["t90"]
    if np.isfinite(mesures["t90"]) and np.isfinite(mesures["t100"]):
        assert mesures["t90"] <= mesures["t100"]


def test_comparer_apparie_les_graines_entre_variantes():
    config = _petite_configuration()
    graines = [101, 102]
    variantes = ["reference", "complet"]
    resultats = comparer(config, graines, variantes=variantes)

    assert set(resultats) == set(variantes)
    for nom in variantes:
        valeurs = resultats[nom]
        assert valeurs.shape == (len(graines), len(MESURES))
        # Les graines identiques doivent produire des temps coherents
        assert np.all(valeurs[:, MESURES.index("non_sortis")] >= 0)


def test_cli_comparer_piscine_aide(capsys):
    with pytest.raises(SystemExit) as capture:
        main(["comparer-piscine", "--help"])
    assert capture.value.code == 0
    sortie = capsys.readouterr().out
    assert "E1/E2" in sortie

