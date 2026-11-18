"""Rejouer la campagne finale : plan controle, placeholders, reprise et echecs explicites."""

from pathlib import Path

import pytest

from viscocrowd.cli import construire_analyseur
from viscocrowd.scenarios.campagne_finale import arguments, lire_plan, rejouer

PLAN = Path(__file__).parents[1] / "experiments/campagne-finale.yaml"


def test_chaque_commande_du_plan_est_acceptee_par_la_cli():
    plan = lire_plan(PLAN)
    analyseur = construire_analyseur()
    for calcul in plan["calculs"]:
        analyseur.parse_args(arguments(calcul["commande"], plan["graines"], Path("x.json")))


def test_placeholders_remplaces():
    argv = arguments(
        "balayer-piscine p.yaml --graines {graines} --sortie {sortie}", [3, 4], Path("d/a.json")
    )
    assert argv == ["balayer-piscine", "p.yaml", "--graines", "3", "4", "--sortie", "d/a.json"]


def test_identifiant_en_double_refuse(tmp_path):
    plan = tmp_path / "p.yaml"
    plan.write_text(
        "version: 1\ngraines: [1]\ncalculs:\n"
        + "  - {identifiant: a, mesure: m, commande: --version}\n" * 2,
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="en double"):
        lire_plan(plan)


def test_reprise_et_echec(tmp_path):
    plan = {
        "version": 1,
        "graines": [1],
        "calculs": [
            {"identifiant": "ok", "mesure": "m", "commande": "--version"},
            {"identifiant": "ko", "mesure": "m", "commande": "commande-inconnue"},
        ],
    }
    lignes = []
    assert rejouer(plan, tmp_path, progression=lignes.append) == ["ko"]
    assert "viscocrowd" in (tmp_path / "ok.txt").read_text(encoding="utf-8")
    assert (tmp_path / "ko.echec.txt").exists() and not (tmp_path / "ko.txt").exists()
    # Relance : le calcul fini n'est pas refait, celui en echec l'est.
    lignes.clear()
    assert rejouer(plan, tmp_path, progression=lignes.append) == ["ko"]
    assert any("ok : deja fait" in ligne for ligne in lignes)
    with pytest.raises(ValueError, match="inconnus"):
        rejouer(plan, tmp_path, seulement=["absent"])


def test_bilan_partiel_mis_de_cote_a_la_reprise(tmp_path, monkeypatch):
    """Un balayage interrompu laisse son JSON sans journal : la relance doit le refaire.

    `balayer-piscine` ecrit son bilan apres chaque valeur et refuse une sortie existante.
    Sans precaution, la reprise echouait donc a chaque relance (revue de #148).
    """
    import viscocrowd.cli as cli

    appels = []

    def commande(argv):
        bilan = Path(argv[argv.index("--sortie") + 1])
        if bilan.exists():
            return 1  # comme balayer-piscine : « existe deja »
        bilan.write_text("{}", encoding="utf-8")
        appels.append(argv)
        return 1 if len(appels) == 1 else 0  # interrompu la premiere fois

    monkeypatch.setattr(cli, "main", commande)
    plan = {
        "version": 1,
        "graines": [1],
        "calculs": [{"identifiant": "b", "mesure": "m", "commande": "x --sortie {sortie}"}],
    }
    assert rejouer(plan, tmp_path, progression=lambda _: None) == ["b"]
    assert (tmp_path / "b.json").exists() and not (tmp_path / "b.txt").exists()
    assert rejouer(plan, tmp_path, progression=lambda _: None) == []
    assert (tmp_path / "b.txt").exists()
    assert (tmp_path / "b.json.precedent").exists()
