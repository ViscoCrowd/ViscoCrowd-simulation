"""Les etats et evenements archives pilotent la vue, y compris une occupation inachevee."""

from copy import deepcopy
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pytest
import yaml
from PIL import Image

from viscocrowd.cli import main
from viscocrowd.io.configuration import lire_configuration
from viscocrowd.io.trajectoires import Trajectoire, ecrire_trajectoire
from viscocrowd.scenarios.experience import executer_configuration
from viscocrowd.scenarios.piscine import NOMS_ETATS, ParametresPiscine
from viscocrowd.ui.relecture_piscine import LecteurPiscine


@pytest.fixture
def donnees():
    config = lire_configuration(Path(__file__).parents[1] / "experiments/piscine.yaml")
    config["parametres"]["n_agents"] = 2
    p = ParametresPiscine(**config["parametres"], graine=config["graine"])
    site = p.piscine.sites()[0]
    attente, bord, arrivee = site.attente(p.rayon), site.position, site.arrivee(p.rayon)
    x = np.array([[attente, [5, 5]], [bord, [5, 5]], [arrivee, [5, 5]], [[49, 10], [5, 5]]])
    return Trajectoire(
        np.array([0.0, 0.2, 2.2, 40.0]),
        x,
        np.zeros_like(x),
        np.full(2, p.rayon),
        {
            "configuration": config,
            "etats": list(NOMS_ETATS),
            "evenements": {"sorties": [39.9, None]},
        },
        etats=np.array([[0, 0], [1, 0], [2, 0], [3, 0]]),
    )


def test_relecture_positions_etats_occupation_et_sortie_sans_moteur(donnees, monkeypatch):
    def interdit(*args, **kwargs):
        raise AssertionError("aucune simulation pendant la relecture")

    monkeypatch.setattr("viscocrowd.scenarios.piscine.simuler_piscine", interdit)
    vue = LecteurPiscine(donnees)
    try:
        vue.slider.set_val(1.0)
        assert vue.index == 1
        np.testing.assert_array_equal([d.center for d in vue.disques], donnees.x[1])
        assert vue.occupes.sum() == 1 and vue.occupes[0]
        assert "Franchissement : 1" in vue.effectifs.get_text()
        vue.aller_au_temps(2.2)
        assert not vue.occupes.any()
        vue.aller_au_temps(40.0)
        assert not vue.disques[0].get_visible() and vue.disques[1].get_visible()
        assert vue.compteur.get_text() == "Évacués : 1 / 2"
        vue.aller_au_temps(0.0)
        assert all(d.get_visible() for d in vue.disques)
        assert vue.compteur.get_text() == "Évacués : 0 / 2"
    finally:
        plt.close(vue.figure)


def test_occupation_en_cours_sans_evenement_termine(donnees):
    donnees.t, donnees.x, donnees.v, donnees.etats = [
        a[:2] for a in (donnees.t, donnees.x, donnees.v, donnees.etats)
    ]
    donnees.metadonnees["evenements"]["sorties"] = [None, None]
    vue = LecteurPiscine(donnees, interactif=False)
    try:
        vue.aller_au_temps(0.2)
        assert vue.occupes[0]
    finally:
        plt.close(vue.figure)


@pytest.mark.parametrize("defaut", ["absents", "legende", "code", "retour", "sorties"])
def test_archive_incoherente_refusee(donnees, defaut):
    if defaut == "absents":
        donnees.etats = None
    elif defaut == "legende":
        donnees.metadonnees["etats"] = ["autre"]
    elif defaut == "code":
        donnees.etats[-1, 0] = 4
    elif defaut == "retour":
        donnees.etats[-1, 0] = 0
    else:
        donnees.metadonnees["evenements"]["sorties"][0] = None
    with pytest.raises(ValueError):
        LecteurPiscine(donnees, interactif=False)


def test_franchissement_hors_site_refuse_des_l_ouverture(donnees):
    """L'instant fautif (t = 0,2 s) n'est jamais affiche : le refus vient de l'ouverture."""
    donnees.x[1, 0] += 0.1
    figures = plt.get_fignums()
    with pytest.raises(ValueError, match=r"occupation.*t = 0\.20 s"):
        LecteurPiscine(donnees, interactif=False)
    assert plt.get_fignums() == figures  # aucune figure laissee ouverte


def test_site_partage_refuse_des_l_ouverture(donnees):
    """Deux agents en franchissement sur le meme site : capacite unitaire violee."""
    donnees.x[1, 1] = donnees.x[1, 0]
    donnees.etats[1:, 1] = [1, 2, 2]
    with pytest.raises(ValueError, match="occupation"):
        LecteurPiscine(donnees, interactif=False)


def test_exports_cli_png_gif_et_refus_ecrasement(donnees, tmp_path):
    # Accelerer uniquement la lecture pour un GIF court, jamais le temps physique.
    archive = tmp_path / "piscine.npz"
    ecrire_trajectoire(archive, donnees)
    png, gif = tmp_path / "vue.png", tmp_path / "film.gif"
    args = [
        "rejouer",
        str(archive),
        "--image",
        str(png),
        "--gif",
        str(gif),
        "--instant",
        ".2",
        "--vitesse",
        "40",
    ]
    assert main(args) == 0
    with Image.open(png) as image:
        assert image.format == "PNG" and image.width > 1000
    with Image.open(gif) as image:
        assert image.format == "GIF" and image.n_frames >= 2
    original = png.read_bytes()
    assert main(args) == 1
    assert png.read_bytes() == original


def test_geometrie_vient_de_l_archive(donnees):
    original = deepcopy(donnees.metadonnees)
    vue = LecteurPiscine(donnees, interactif=False)
    try:
        assert vue.p.piscine.longueur_emprise == 48.0
        assert len(vue.marqueurs_sites) == len(vue.p.piscine.sites())
        assert donnees.metadonnees == original
    finally:
        plt.close(vue.figure)


def test_cli_refuse_une_configuration_non_structuree(donnees, tmp_path):
    donnees.metadonnees["configuration"] = []
    fichier = tmp_path / "invalide.npz"
    ecrire_trajectoire(fichier, donnees)
    assert main(["rejouer", str(fichier), "--image", str(tmp_path / "vue.png")]) == 1


@pytest.mark.parametrize(("tous_les_pas", "instants"), [(1, 7), (2, 4)])
def test_archive_espacee_relue_et_signalee(tmp_path, tous_les_pas, instants):
    """Archive de #70 (un instant tous les K pas) : relue telle quelle, espacement affiche."""
    config = lire_configuration(Path(__file__).parents[1] / "experiments/piscine.yaml")
    config["parametres"].update(n_agents=4, duree=0.055)
    fichier = tmp_path / "piscine.yaml"
    fichier.write_text(yaml.safe_dump(config))
    archive = tmp_path / "piscine.npz"
    donnees = executer_configuration(fichier, archive, archiver_tous=tous_les_pas)
    assert len(donnees.t) == instants  # premier et dernier pas toujours conserves
    vue = LecteurPiscine(donnees, interactif=False)
    try:
        assert ("1 image tous les 2 pas" in vue.legende.get_text()) == (tous_les_pas == 2)
    finally:
        plt.close(vue.figure)
