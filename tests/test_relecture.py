"""Relecture sans moteur : positions, horloge, commandes et exports reels."""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pytest
from PIL import Image

from viscocrowd.cli import main
from viscocrowd.io.configuration import lire_configuration
from viscocrowd.io.trajectoires import Trajectoire, ecrire_trajectoire
from viscocrowd.ui.relecture import LecteurCouloir, indices_animation


@pytest.fixture
def donnees():
    config = lire_configuration(Path(__file__).parents[1] / "experiments/couloir.yaml")
    config["parametres"].update(
        n_agents=2, colonnes=2, longueur=2.0, frontieres=[], milieux=["SEC"]
    )
    x = np.array([[[0.5, 0.0], [0.8, 0.5]], [[2.2, 0.0], [1.2, 0.5]], [[3.0, 0.0], [2.5, 0.5]]])
    return Trajectoire(
        np.array([0.0, 0.2, 1.0]), x, np.zeros_like(x), np.full(2, 0.2), {"configuration": config}
    )


@pytest.fixture
def lecteur(donnees, monkeypatch):
    def interdit(*args, **kwargs):
        raise AssertionError("la relecture ne doit jamais relancer le moteur")

    monkeypatch.setattr("viscocrowd.scenarios.couloir.simuler_couloir", interdit)
    vue = LecteurCouloir(donnees)
    yield vue
    plt.close(vue.figure)


def test_navigation_restitue_positions_rayons_temps_et_passages(lecteur, donnees):
    lecteur.slider.set_val(0.3)
    assert lecteur.index == 1  # dernier instant archive <= temps demande
    np.testing.assert_array_equal([d.center for d in lecteur.disques], donnees.x[1])
    np.testing.assert_array_equal([d.radius for d in lecteur.disques], donnees.rayons)
    assert "00.20 s" in lecteur.temps.get_text()
    assert lecteur.compteur.get_text().endswith("1")
    lecteur.aller_au_temps(1.0)
    assert lecteur.compteur.get_text().endswith("2")
    lecteur.aller_au_temps(0.0)
    assert lecteur.compteur.get_text().endswith("0")


def test_pause_vitesse_et_fin_de_lecture(lecteur, monkeypatch):
    horloge = [100.0]
    monkeypatch.setattr("viscocrowd.ui.relecture.time.monotonic", lambda: horloge[0])
    lecteur.vitesse = 2.0
    lecteur.basculer()
    horloge[0] += 0.15
    lecteur._tic()
    assert lecteur.index == 1
    lecteur.basculer()  # pause
    horloge[0] += 10.0
    lecteur._tic()
    assert lecteur.index == 1
    lecteur.basculer()
    horloge[0] += 1.0
    lecteur._tic()
    assert lecteur.index == 2
    assert not lecteur.en_lecture
    assert lecteur.bouton.label.get_text() == "Lire"
    lecteur.basculer()  # repartir du debut apres la fin
    assert lecteur.index == 0


@plt.rc_context({"figure.dpi": 150, "savefig.dpi": 150})
def test_export_gif_irregulier_garde_premier_et_dernier_instant(donnees, tmp_path):
    indices = indices_animation(donnees.t, fps=5, vitesse=1.0)
    np.testing.assert_array_equal(indices, [0, 1, 1, 1, 1, 2])
    vue = LecteurCouloir(donnees, interactif=False)
    try:
        fichier = tmp_path / "film.gif"
        vue.exporter_gif(fichier, fps=5)
        with Image.open(fichier) as image:
            assert image.format == "GIF"
            assert image.n_frames >= 2
            assert image.size == (1200, 540)
        assert vue.index == 2
    finally:
        plt.close(vue.figure)


def test_commande_png_et_refus_d_ecraser(donnees, tmp_path):
    archive, image = tmp_path / "a.npz", tmp_path / "image.png"
    ecrire_trajectoire(archive, donnees)
    args = ["rejouer", str(archive), "--image", str(image), "--instant", ".2"]
    assert main(args) == 0
    with Image.open(image) as png:
        assert png.format == "PNG"
    original = image.read_bytes()
    assert main(args) == 1
    assert image.read_bytes() == original


@pytest.mark.parametrize("instant", [-1.0, 2.0, np.nan])
def test_instant_invalide(lecteur, instant):
    with pytest.raises(ValueError, match="instant"):
        lecteur.aller_au_temps(instant)


def test_un_seul_instant_reste_affichable(donnees):
    unique = Trajectoire(
        donnees.t[:1], donnees.x[:1], donnees.v[:1], donnees.rayons, donnees.metadonnees
    )
    vue = LecteurCouloir(unique)
    assert vue.slider is None
    np.testing.assert_array_equal(indices_animation(unique.t, 5, 1.0), [0])
    plt.close(vue.figure)


def test_obstacles_lus_dans_l_archive_et_dessines(tmp_path):
    """Le pilier vient de la configuration archivee, a l'echelle metrique, sans moteur."""
    import yaml

    from viscocrowd.scenarios.experience import executer_configuration

    config = lire_configuration(Path(__file__).parents[1] / "experiments/couloir_obstacle.yaml")
    config["parametres"]["duree"] = 0.05
    fichier = tmp_path / "obstacle.yaml"
    fichier.write_text(yaml.safe_dump(config))
    donnees = executer_configuration(fichier, tmp_path / "obstacle.npz")
    vue = LecteurCouloir(donnees, interactif=False)
    try:
        assert len(vue.obstacles) == 1
        pilier = vue.obstacles[0]
        assert pilier.get_xy() == (6.0, -0.5)
        assert (pilier.get_width(), pilier.get_height()) == (1.0, 1.0)
        assert any("CONTOURNEMENT" in texte.get_text() for texte in vue.figure.texts)
    finally:
        plt.close(vue.figure)


def test_configuration_absente_refusee(donnees):
    donnees.metadonnees.clear()
    with pytest.raises(ValueError, match="archive du scenario couloir"):
        LecteurCouloir(donnees)
