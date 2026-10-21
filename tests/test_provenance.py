"""Une archive doit dire quel code l'a produite, et si ce code etait modifie."""

import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

from viscocrowd.io.configuration import lire_configuration
from viscocrowd.io.provenance import VARIABLE_COMMIT, provenance_code
from viscocrowd.io.trajectoires import lire_trajectoire
from viscocrowd.scenarios import experience
from viscocrowd.scenarios.experience import executer_configuration

EXEMPLE = Path(__file__).parents[1] / "experiments/bille_boite.yaml"
SHA = "0123456789abcdef0123456789abcdef01234567"

avec_git = pytest.mark.skipif(shutil.which("git") is None, reason="git absent de l'environnement")


def git(racine, *arguments):
    subprocess.run(["git", "-C", str(racine), *arguments], check=True, capture_output=True)


@pytest.fixture
def depot(tmp_path, monkeypatch):
    """Petit depot avec un fichier de code et un document, sans configuration globale."""
    monkeypatch.delenv(VARIABLE_COMMIT, raising=False)
    (tmp_path / "src").mkdir()
    (tmp_path / "src/moteur.py").write_text("PAS = 1\n")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs/notes.md").write_text("notes\n")
    git(tmp_path, "init", "-q")
    git(tmp_path, "add", ".")
    identite = ("-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false")
    git(tmp_path, *identite, "commit", "-q", "-m", "init")
    return tmp_path


@avec_git
def test_depot_propre(depot):
    p = provenance_code(depot)
    commit = subprocess.run(
        ["git", "-C", str(depot), "rev-parse", "HEAD"], capture_output=True, text=True
    ).stdout.strip()
    assert p == {"commit": commit, "modifications_locales": False, "source": "git"}


@avec_git
@pytest.mark.parametrize(
    "modification",
    [
        lambda d: (d / "src/moteur.py").write_text("PAS = 2\n"),  # code modifie
        lambda d: (d / "src/nouveau.py").write_text(""),  # code non suivi
        lambda d: (d / "experiments").mkdir() or (d / "experiments/c.yaml").write_text("a: 1"),
    ],
)
def test_code_ou_configuration_modifies_sont_signales(depot, modification):
    modification(depot)
    assert provenance_code(depot)["modifications_locales"] is True


@avec_git
def test_documentation_modifiee_ne_marque_pas_l_archive(depot):
    (depot / "docs/notes.md").write_text("autres notes\n")
    (depot / "docs/brouillon.md").write_text("")
    assert provenance_code(depot)["modifications_locales"] is False


@avec_git
def test_sous_dossier_d_un_depot_n_emprunte_pas_son_commit(depot):
    assert provenance_code(depot / "src")["source"] == "indisponible"


def test_sans_depot_le_commit_vient_de_l_environnement(tmp_path, monkeypatch):
    monkeypatch.setenv(VARIABLE_COMMIT, SHA.upper())
    assert provenance_code(tmp_path) == {
        "commit": SHA,
        "modifications_locales": None,
        "source": "environnement",
    }


@pytest.mark.parametrize("valeur", ["", "abc", "inconnu", SHA + "0"])
def test_sans_depot_ni_commit_valide_rien_n_est_invente(tmp_path, monkeypatch, valeur):
    monkeypatch.setenv(VARIABLE_COMMIT, valeur)
    assert provenance_code(tmp_path) == {
        "commit": None,
        "modifications_locales": None,
        "source": "indisponible",
    }


def test_sans_executable_git(tmp_path, monkeypatch):
    def absent(*args, **kwargs):
        raise FileNotFoundError("git")

    monkeypatch.setattr(subprocess, "run", absent)
    monkeypatch.setenv(VARIABLE_COMMIT, SHA)
    assert provenance_code(tmp_path)["source"] == "environnement"


def test_l_archive_enregistre_la_provenance(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "viscocrowd.scenarios.experience.provenance_code",
        lambda: {"commit": SHA, "modifications_locales": True, "source": "git"},
    )
    config = lire_configuration(EXEMPLE)
    config["parametres"]["duree"] = 0.05
    fichier = tmp_path / "bille.yaml"
    fichier.write_text(yaml.safe_dump(config))
    executer_configuration(fichier, tmp_path / "bille.npz")
    code = lire_trajectoire(tmp_path / "bille.npz").metadonnees["code"]
    assert code == {"commit": SHA, "modifications_locales": True, "source": "git"}


@pytest.mark.parametrize("changement", [{"commit": "a" * 40}, {"modifications_locales": True}])
def test_changement_de_code_pendant_le_calcul_refuse_l_archive(tmp_path, monkeypatch, changement):
    courant = {"commit": SHA, "modifications_locales": False, "source": "git"}
    monkeypatch.setattr(experience, "provenance_code", lambda: courant.copy())
    simuler = experience.simuler_bille

    def calcul_avec_changement(p):
        resultat = simuler(p)
        courant.update(changement)  # commit ou edition intervenus pendant le calcul
        return resultat

    monkeypatch.setattr(experience, "simuler_bille", calcul_avec_changement)
    config = lire_configuration(EXEMPLE)
    config["parametres"]["duree"] = 0.05
    fichier = tmp_path / "bille.yaml"
    fichier.write_text(yaml.safe_dump(config))
    sortie = tmp_path / "bille.npz"
    with pytest.raises(ValueError, match=r"provenance.*pendant"):
        executer_configuration(fichier, sortie)
    assert not sortie.exists()
