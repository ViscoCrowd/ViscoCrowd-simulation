"""Configurations reduites de la piscine, partagees par les tests.

Meme logique que `parametres(**changements)` de `test_piscine_scenario.py`, avec deux
differences : une population et une duree reduites par defaut (6 agents, 10 s), pour des
tests de quelques secondes, et une cle `geometrie` FUSIONNEE dans la geometrie de reference
au lieu de la remplacer (`geometrie={"largeur_porte": 0.9}` ne change que la porte).
"""

from __future__ import annotations

from pathlib import Path

import yaml

from viscocrowd.io.configuration import lire_configuration
from viscocrowd.scenarios.piscine import ParametresPiscine

RACINE = Path(__file__).parents[1]
EXEMPLE = RACINE / "experiments/piscine.yaml"
EXEMPLE_GOULOT = RACINE / "experiments/goulot.yaml"
REDUCTION = {"n_agents": 6, "duree": 10.0}  # 6 agents, 10 s simulees


def reference() -> dict:
    """Table `parametres` de la configuration de reference, telle que lue dans le YAML."""
    return lire_configuration(EXEMPLE)["parametres"]


def _parametres_reduits_dict(**surcharges) -> dict:
    parametres = reference() | REDUCTION
    for nom, valeur in surcharges.items():
        if nom == "geometrie":
            parametres["geometrie"] = parametres["geometrie"] | valeur
        else:
            parametres[nom] = valeur
    return parametres


def parametres_reduits(**surcharges) -> ParametresPiscine:
    """Reference a 6 agents et 10 s, avec `surcharges` (geometrie fusionnee)."""
    graine = lire_configuration(EXEMPLE)["graine"]
    return ParametresPiscine(**_parametres_reduits_dict(**surcharges), graine=graine)


def piscine_reduite(dossier: Path, **surcharges) -> Path:
    """Ecrit la meme configuration reduite en YAML dans `dossier / "piscine.yaml"`."""
    configuration = lire_configuration(EXEMPLE)
    configuration["parametres"] = _parametres_reduits_dict(**surcharges)
    chemin = Path(dossier) / "piscine.yaml"
    chemin.write_text(yaml.safe_dump(configuration, allow_unicode=True), encoding="utf-8")
    return chemin


def simuler_archive_reduite(chemin: Path, **surcharges) -> Path:
    """Simule la configuration reduite et l'archive en `chemin` (.npz) ; rend `chemin`."""
    from viscocrowd.scenarios.experience import executer_configuration

    chemin = Path(chemin)
    executer_configuration(piscine_reduite(chemin.parent, **surcharges), chemin)
    return chemin
