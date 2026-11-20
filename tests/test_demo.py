"""Configurations de demonstration (`make demo`) : toujours valides quand le code evolue."""

from pathlib import Path

import pytest

from viscocrowd.io.configuration import lire_configuration
from viscocrowd.scenarios.piscine import ParametresPiscine

RACINE = Path(__file__).parents[1]
DEMO = RACINE / "experiments/demo"


@pytest.mark.parametrize("yaml", sorted(DEMO.glob("*.yaml")), ids=lambda p: p.stem)
def test_configuration_de_demo_valide(yaml):
    config = lire_configuration(yaml)
    ParametresPiscine(**config["parametres"], graine=config["graine"])


def test_chaque_configuration_est_documentee():
    lisez_moi = (DEMO / "README.md").read_text(encoding="utf-8")
    for yaml in DEMO.glob("*.yaml"):
        assert yaml.name in lisez_moi


def test_cible_demo_dans_le_makefile_et_run_ps1():
    assert "\ndemo:" in (RACINE / "Makefile").read_text(encoding="utf-8")
    assert '"demo" {' in (RACINE / "run.ps1").read_text(encoding="utf-8")
