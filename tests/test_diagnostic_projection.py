"""Reproduire un echec isole sans rejouer toute la simulation ni valider son resultat."""

from pathlib import Path

import numpy as np
import pytest
import yaml

from viscocrowd.cli import main
from viscocrowd.geometry.boite import BoiteTournante
from viscocrowd.geometry.projection import ProjectionExclusion, ProjectionNonConvergee
from viscocrowd.io.diagnostic_projection import (
    ecrire_diagnostic,
    lire_diagnostic,
    rejouer_diagnostic,
)
from viscocrowd.io.trajectoires import lire_trajectoire
from viscocrowd.scenarios import tassement
from viscocrowd.scenarios.experience import executer_configuration

CONFIG = {"version": 1, "scenario": "tassement", "graine": 1, "parametres": {"n_agents": 3}}


def echec():
    p = ProjectionExclusion(BoiteTournante(demi_largeur=1.0).projeter, iterations=1, strict=True)
    with pytest.raises(ProjectionNonConvergee) as erreur:
        p(np.array([[-0.4, 0.0], [0.0, 0.0], [0.4, 0.0]]), np.full(3, 0.3), 1.25)
    return erreur.value


def test_rejouer_meme_residu_et_comparer_un_budget_superieur(tmp_path):
    erreur = echec()
    fichier = tmp_path / "echec.npz"
    ecrire_diagnostic(fichier, erreur, CONFIG, {"commit": "reference"})
    diagnostic = lire_diagnostic(fichier)
    bilan = rejouer_diagnostic(diagnostic)
    assert bilan["residu_rejoue_m"] == erreur.residu
    assert bilan["ecart_positions_archive_m"] == 0
    assert bilan["instant_s"] == 1.25
    assert not bilan["converge"]
    assert bilan["contacts_hors_tolerance_archives"]
    assert rejouer_diagnostic(diagnostic, iterations=300)["converge"]
    assert main(["diagnostiquer-projection", str(fichier)]) == 1
    assert main(["diagnostiquer-projection", str(fichier), "--iterations", "300"]) == 0
    assert main(["diagnostiquer-projection", str(fichier), "--iterations", "0"]) == 2
    with pytest.raises(ValueError, match="champs"):
        lire_trajectoire(fichier)
    avant = fichier.read_bytes()
    with pytest.raises(FileExistsError):
        ecrire_diagnostic(fichier, erreur, CONFIG, {})
    assert fichier.read_bytes() == avant


@pytest.mark.parametrize("strict", [False, True])
def test_garde_le_pire_appel_sans_partager_les_tableaux(strict):
    p = ProjectionExclusion(iterations=1, strict=strict)
    x = np.array([[-0.1, 0.0], [0.0, 0.0], [0.1, 0.0]])
    r = np.full(3, 0.3)

    def appeler(t):
        if strict:
            with pytest.raises(ProjectionNonConvergee):
                p(x, r, t)
        else:
            p(x, r, t)

    appeler(2.0)
    residu = p.recouvrement_max
    x *= 4
    appeler(3.0)
    r[:] = 0.01
    with pytest.raises(ProjectionNonConvergee) as capture:
        p.verifier_convergence()
    erreur = capture.value
    assert p.non_convergences == 2
    assert erreur.residu == residu
    assert erreur.instantane.instant == 2.0
    np.testing.assert_array_equal(erreur.instantane.rayons, np.full(3, 0.3))
    assert erreur.instantane.x_libre[0, 0] == -0.1


def test_pas_d_instantane_sur_le_chemin_convergent():
    p = ProjectionExclusion(strict=True)
    p(np.array([[-0.4, 0.0], [0.4, 0.0]]), np.full(2, 0.3), 0.0)
    assert p.pire_echec is None
    p.verifier_convergence()


def test_simulation_reelle_archive_l_echec_et_cli_annonce_le_chemin(tmp_path, monkeypatch, capsys):
    def projection(*args, **kwargs):
        return ProjectionExclusion(*args, **kwargs, iterations=1)

    monkeypatch.setattr(tassement, "ProjectionExclusion", projection)
    config = CONFIG | {"parametres": {"n_agents": 16, "duree": 1.0, "dt": 0.01}}
    chemin = tmp_path / "config.yaml"
    chemin.write_text(yaml.safe_dump(config))
    sortie = tmp_path / "calcul.npz"
    assert main(["simuler", str(chemin), "--sortie", str(sortie)]) == 1
    assert not sortie.exists()
    diagnostic = sortie.with_suffix(".diagnostic.npz")
    assert str(diagnostic) in capsys.readouterr().err
    bilan = rejouer_diagnostic(lire_diagnostic(diagnostic))
    assert not bilan["converge"]
    assert bilan["ecart_positions_archive_m"] == 0
    assert bilan["residu_rejoue_m"] == bilan["residu_archive_m"]
    # Un diagnostic deja present n'est pas ecrase ; l'erreur physique reste principale.
    avant = diagnostic.read_bytes()
    with pytest.raises(ProjectionNonConvergee) as erreur:
        executer_configuration(chemin, sortie)
    assert any("non sauvegarde" in note for note in erreur.value.__notes__)
    assert diagnostic.read_bytes() == avant


@pytest.mark.parametrize("champ", ["instant", "x_libre", "rayons", "metadonnees"])
def test_archive_invalide_refusee(tmp_path, champ):
    chemin = tmp_path / "diagnostic.npz"
    ecrire_diagnostic(chemin, echec(), CONFIG, {})
    with np.load(chemin, allow_pickle=False) as archive:
        contenu = dict(archive)
    contenu[champ] = np.array("[]") if champ == "metadonnees" else np.array(np.nan)
    np.savez(chemin, **contenu)
    assert main(["diagnostiquer-projection", str(chemin)]) == 2


def test_succes_ne_produit_pas_de_diagnostic(tmp_path):
    config = Path(__file__).parents[1] / "experiments/tassement.yaml"
    contenu = yaml.safe_load(config.read_text())
    contenu["parametres"].update(n_agents=4, duree=0.01)
    chemin = tmp_path / "court.yaml"
    chemin.write_text(yaml.safe_dump(contenu))
    executer_configuration(chemin, tmp_path / "calcul.npz")
    assert not (tmp_path / "calcul.diagnostic.npz").exists()


@pytest.mark.parametrize("scenario", ["couloir", "piscine"])
def test_reconstruction_des_domaines_guides(tmp_path, scenario):
    from viscocrowd.geometry.couloir import Couloir
    from viscocrowd.io.configuration import lire_configuration
    from viscocrowd.scenarios.experience import _parametres

    config = lire_configuration(Path(__file__).parents[1] / f"experiments/{scenario}.yaml")
    p = _parametres(config)
    if scenario == "couloir":
        domaine = Couloir(p.longueur, p.largeur, p.rectangles)
        centre = np.array([p.longueur / 2, p.largeur / 2])
    else:
        domaine = p.piscine
        b = domaine.bassin
        centre = np.array([(b.x_min + b.x_max) / 2, (b.y_min + b.y_max) / 2])
    projection = ProjectionExclusion(domaine.projeter, iterations=1, strict=True)
    x = centre + np.array([[-0.1, 0], [0, 0], [0.1, 0]])
    with pytest.raises(ProjectionNonConvergee) as erreur:
        projection(x, np.full(3, p.rayon), 2.0)
    chemin = tmp_path / "diagnostic.npz"
    ecrire_diagnostic(chemin, erreur.value, config, {})
    bilan = rejouer_diagnostic(lire_diagnostic(chemin))
    assert bilan["ecart_positions_archive_m"] == 0
    assert bilan["residu_rejoue_m"] == bilan["residu_archive_m"]
