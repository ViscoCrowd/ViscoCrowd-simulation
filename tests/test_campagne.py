"""Reprise apres interruption, echec ou fichier endommage, avec vrais petits calculs."""

import json
from pathlib import Path

import pytest
import yaml

from viscocrowd.cli import main
from viscocrowd.io.configuration import lire_configuration
from viscocrowd.scenarios import campagne


@pytest.fixture
def configurations(tmp_path):
    config = lire_configuration(Path(__file__).parents[1] / "experiments/couloir.yaml")
    config["parametres"].update(n_agents=4, colonnes=2, duree=0.02)
    fichiers = []
    for i in range(2):
        config["parametres"]["duree"] += 0.01
        fichier = tmp_path / f"cas-{i}.yaml"
        fichier.write_text(yaml.safe_dump(config))
        fichiers.append(fichier)
    return fichiers


def test_interruption_puis_reprise_ne_recalcule_pas_les_cas_termines(
    configurations, tmp_path, monkeypatch
):
    sortie = tmp_path / "campagne"
    executer = campagne.executer_configuration
    appels = []

    def interrompre(config, archive):
        appels.append(archive.name)
        if len(appels) == 2:
            raise KeyboardInterrupt
        return executer(config, archive)

    monkeypatch.setattr(campagne, "executer_configuration", interrompre)
    with pytest.raises(KeyboardInterrupt):
        campagne.executer_campagne(configurations, sortie, graines=[1, 2])
    assert not (sortie / ".verrou").exists()
    premier = (sortie / "0001.npz").read_bytes()
    appels.clear()

    def compter(config, archive):
        appels.append(archive.name)
        return executer(config, archive)

    monkeypatch.setattr(campagne, "executer_configuration", compter)
    suivi = campagne.executer_campagne(configurations, sortie, graines=[1, 2], reprendre=True)
    assert appels == ["0002.npz", "0003.npz", "0004.npz"]
    assert all(r["statut"] == "termine" for r in suivi["resultats"])
    assert (sortie / "0001.npz").read_bytes() == premier
    appels.clear()
    campagne.executer_campagne(configurations, sortie, graines=[1, 2], reprendre=True)
    assert appels == []


def test_archive_corrompue_conservee_et_recalculee(configurations, tmp_path):
    sortie = tmp_path / "campagne"
    campagne.executer_campagne(configurations[:1], sortie)
    (sortie / "0001.npz").write_bytes(b"interruption pendant l'ecriture")
    suivi = campagne.executer_campagne(configurations[:1], sortie, reprendre=True)
    assert suivi["resultats"][0]["statut"] == "termine"
    assert (sortie / "0001.invalide-1.npz").read_bytes() == b"interruption pendant l'ecriture"


@pytest.mark.parametrize("exception", [ValueError, RuntimeError])
def test_echec_reste_visible_et_code_cli_non_nul(configurations, tmp_path, monkeypatch, exception):
    executer = campagne.executer_configuration

    def echouer(config, archive):
        if archive.name == "0001.npz":
            raise exception("deplacement inadmissible")
        return executer(config, archive)

    monkeypatch.setattr(campagne, "executer_configuration", echouer)
    sortie = tmp_path / "campagne"
    assert main(["campagne", *map(str, configurations), "--sortie", str(sortie)]) == 1
    suivi = json.loads((sortie / "campagne.json").read_text())
    assert [r["statut"] for r in suivi["resultats"]] == ["echec", "termine"]
    assert "deplacement" in suivi["resultats"][0]["erreur"]


@pytest.mark.parametrize("changement", ["plan", "code", "environnement"])
def test_reprise_incompatible_refusee(configurations, tmp_path, monkeypatch, changement):
    sortie = tmp_path / "campagne"
    campagne.executer_campagne(configurations, sortie)
    avant = (sortie / "campagne.json").read_bytes()
    contexte = campagne.contexte()
    if changement == "plan":
        config = lire_configuration(configurations[0])
        config["graine"] += 1
        configurations[0].write_text(yaml.safe_dump(config))
    elif changement == "code":
        contexte["sources_sha256"] = "autre contenu"
    else:
        contexte["python"] = "autre version"
    monkeypatch.setattr(campagne, "contexte", lambda: contexte)
    with pytest.raises(ValueError, match="different"):
        campagne.executer_campagne(configurations, sortie, reprendre=True)
    assert (sortie / "campagne.json").read_bytes() == avant


def test_verrou_et_doublons_refuses(configurations, tmp_path):
    sortie = tmp_path / "campagne"
    sortie.mkdir()
    (sortie / ".verrou").write_text("autre processus")
    with pytest.raises(ValueError, match="verrouillee"):
        campagne.executer_campagne(configurations, sortie)
    assert (sortie / ".verrou").read_text() == "autre processus"
    with pytest.raises(ValueError, match="distinctes"):
        campagne.executer_campagne(configurations, sortie, graines=[1, 1])
    with pytest.raises(ValueError, match="identiques"):
        campagne.executer_campagne([configurations[0]] * 2, sortie)


def test_cli_reprise_explicite_et_repertoire_non_vide(configurations, tmp_path):
    sortie = tmp_path / "campagne"
    args = ["campagne", str(configurations[0]), "--sortie", str(sortie)]
    assert main([*args, "--reprendre"]) == 1
    assert main(args) == 0
    assert main(args) == 1
    assert main([*args, "--reprendre"]) == 0


def test_bille_sans_graines_et_changement_en_cours(configurations, tmp_path, monkeypatch):
    bille = Path(__file__).parents[1] / "experiments/bille_boite.yaml"
    with pytest.raises(ValueError, match="deterministe"):
        campagne.executer_campagne([bille], tmp_path / "bille", graines=[1])
    contexte = campagne.contexte()
    original = campagne.executer_configuration

    def changer(config, archive):
        resultat = original(config, archive)
        monkeypatch.setattr(campagne, "contexte", lambda: contexte | {"python": "change"})
        return resultat

    monkeypatch.setattr(campagne, "executer_configuration", changer)
    resultat = campagne.executer_campagne(configurations[:1], tmp_path / "change")
    assert resultat["resultats"][0]["statut"] == "echec"
