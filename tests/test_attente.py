"""Carte des temps d'arret : ou la foule a attendu pendant l'evacuation."""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import numpy as np
import pytest
import yaml
from PIL import Image

from viscocrowd.cli import main
from viscocrowd.io.configuration import lire_configuration
from viscocrowd.scenarios.experience import executer_configuration
from viscocrowd.viz.attente import temps_arret

EXEMPLE = Path(__file__).parents[1] / "experiments/piscine.yaml"
UN = np.ones((3, 1), dtype=bool)


def test_agent_immobile_deux_secondes():
    t = np.array([0.0, 1.0, 2.0])
    x = np.full((3, 1, 2), [0.6, 0.6])
    carte = temps_arret(t, x, np.zeros((3, 1, 2)), UN, seuil=0.1, pas=0.25, emprise=(2.0, 2.0))
    assert carte[2, 2] == pytest.approx(2.0) and carte.sum() == pytest.approx(2.0)


def test_agent_en_mouvement_ou_inactif_ne_compte_pas():
    t = np.array([0.0, 1.0, 2.0])
    x = np.full((3, 1, 2), [0.6, 0.6])
    rapide = np.full((3, 1, 2), [1.0, 0.0])
    reglages = {"seuil": 0.1, "pas": 0.25, "emprise": (2.0, 2.0)}
    assert temps_arret(t, x, rapide, UN, **reglages).sum() == 0.0
    assert temps_arret(t, x, np.zeros((3, 1, 2)), ~UN, **reglages).sum() == 0.0


def test_total_independant_de_la_case():
    t = np.linspace(0.0, 4.0, 5)
    x = np.tile([[0.3, 0.3], [1.7, 2.9]], (5, 1, 1))
    v, actifs = np.zeros((5, 2, 2)), np.ones((5, 2), dtype=bool)
    a = temps_arret(t, x, v, actifs, seuil=0.1, pas=0.25, emprise=(4.0, 4.0))
    b = temps_arret(t, x, v, actifs, seuil=0.1, pas=0.125, emprise=(4.0, 4.0))
    assert a.sum() == pytest.approx(b.sum()) == pytest.approx(8.0)


def test_archive_espacee_ponderee_par_l_ecart_reel():
    t = np.array([0.0, 0.5, 2.0])  # ecarts de 0,5 puis 1,5 s
    x = np.full((3, 1, 2), [0.6, 0.6])
    carte = temps_arret(t, x, np.zeros((3, 1, 2)), UN, seuil=0.1, pas=0.25, emprise=(2.0, 2.0))
    assert carte.sum() == pytest.approx(2.0)


def test_parametres_refuses():
    t, x, v = np.zeros(2), np.zeros((2, 1, 2)), np.zeros((2, 1, 2))
    actifs = np.ones((2, 1), dtype=bool)
    with pytest.raises(ValueError):
        temps_arret(t, x, v, actifs, seuil=0.1, pas=0.0, emprise=(2.0, 2.0))
    with pytest.raises(ValueError):
        temps_arret(t, x, v, actifs, seuil=-1.0, pas=0.25, emprise=(2.0, 2.0))


def test_commande_png_et_refus(tmp_path, capsys):
    config = lire_configuration(EXEMPLE)
    config["parametres"] |= {"n_agents": 6, "duree": 20.0}
    chemin = tmp_path / "petit.yaml"
    chemin.write_text(yaml.safe_dump(config), encoding="utf-8")
    archive = tmp_path / "a.npz"
    executer_configuration(chemin, archive)
    png = tmp_path / "attente.png"
    assert main(["attente", str(archive), "--image", str(png)]) == 0
    with Image.open(png) as image:
        assert image.format == "PNG"
    assert "pers·s" in capsys.readouterr().out
    assert main(["attente", str(archive), "--image", str(png)]) == 1
