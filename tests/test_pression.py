"""Carte des forces de contact : chaines de force retrouvees depuis la projection."""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import numpy as np
import pytest
import yaml
from PIL import Image

from viscocrowd.cli import main
from viscocrowd.io.configuration import lire_configuration
from viscocrowd.scenarios.piscine import EAU, PLAGE, ParametresPiscine, simuler_piscine
from viscocrowd.viz.pression import contacts, forces_de_contact

EXEMPLE = Path(__file__).parents[1] / "experiments/piscine.yaml"


def test_colonne_poussee_contre_un_mur_la_force_se_cumule():
    """Trois disques pousses a 1 m/s^2 vers un mur : contacts de 1 puis 2 fois la poussee."""
    x = np.array([[0.0, 0.0], [0.4, 0.0], [0.8, 0.0]])
    a = np.array([[-1.0, 0.0]] * 3)  # la projection annule la poussee vers +x
    lam = forces_de_contact(x, a, np.array([[0, 1], [1, 2]]), np.array([False, False, True]))
    np.testing.assert_allclose(lam, [1.0, 2.0], atol=1e-9)


def test_sans_mur_l_equilibre_libre_ne_fabrique_pas_de_force():
    """Deux disques qui se touchent sans se pousser : contact nul."""
    x = np.array([[0.0, 0.0], [0.4, 0.0]])
    lam = forces_de_contact(x, np.zeros((2, 2)), np.array([[0, 1]]), np.zeros(2, dtype=bool))
    np.testing.assert_allclose(lam, [0.0], atol=1e-12)


def test_deux_disques_qui_se_poussent_l_un_l_autre():
    x = np.array([[0.0, 0.0], [0.4, 0.0]])
    a = np.array([[-3.0, 0.0], [3.0, 0.0]])  # chacun repousse de 3 m/s^2
    lam = forces_de_contact(x, a, np.array([[0, 1]]), np.zeros(2, dtype=bool))
    np.testing.assert_allclose(lam, [3.0], atol=1e-9)


def test_aucun_contact():
    assert (
        forces_de_contact(np.zeros((1, 2)), np.zeros((1, 2)), np.empty((0, 2), int), [False]).size
        == 0
    )


def test_residu_nul_pour_une_colonne_equilibree():
    """Les intensites retrouvees expliquent exactement les corrections : residu nul."""
    x = np.array([[0.0, 0.0], [0.4, 0.0], [0.8, 0.0]])
    a = np.array([[-1.0, 0.0]] * 3)
    lam, residu = forces_de_contact(
        x, a, np.array([[0, 1], [1, 2]]), np.array([False, False, True]), avec_residu=True
    )
    np.testing.assert_allclose(lam, [1.0, 2.0], atol=1e-9)
    assert residu == pytest.approx(0.0, abs=1e-9)


def test_residu_signale_une_poussee_inexpliquee():
    """Deux disques sans mur pousses dans le meme sens : aucun lambda >= 0 ne l'explique."""
    x = np.array([[0.0, 0.0], [0.4, 0.0]])
    a = np.array([[1.0, 0.0], [1.0, 0.0]])
    _, residu = forces_de_contact(
        x, a, np.array([[0, 1]]), np.zeros(2, dtype=bool), avec_residu=True
    )
    assert residu > 0.5


def test_residu_sans_contact():
    lam, residu = forces_de_contact(
        np.zeros((1, 2)), np.zeros((1, 2)), np.empty((0, 2), int), [False], avec_residu=True
    )
    assert lam.size == 0 and residu == 0.0


def test_contacts_ignorent_les_agents_inactifs_et_les_jeux_larges():
    x = np.array([[0.0, 0.0], [0.4, 0.0], [0.8, 0.0], [5.0, 5.0]])
    r = np.full(4, 0.2)
    np.testing.assert_array_equal(contacts(x, r, np.ones(4, bool)), [[0, 1], [1, 2]])
    np.testing.assert_array_equal(
        contacts(x, r, np.array([True, False, True, True])), np.empty((0, 2))
    )


def test_mesurer_les_contraintes_ne_change_pas_la_trajectoire():
    config = lire_configuration(EXEMPLE)
    p = ParametresPiscine(**(config["parametres"] | {"n_agents": 12, "duree": 8.0}), graine=3)
    sans = simuler_piscine(p)
    avec = simuler_piscine(p, contraintes=True)
    np.testing.assert_array_equal(avec.x, sans.x)
    np.testing.assert_array_equal(avec.v, sans.v)
    assert sans.contraintes is None
    assert avec.contraintes.shape == avec.x.shape
    inactifs = (avec.etats != EAU) & (avec.etats != PLAGE)
    assert np.all(avec.contraintes[inactifs] == 0.0)
    assert np.all(np.isfinite(avec.contraintes))


def test_commande_png_et_refus(tmp_path, capsys):
    config = lire_configuration(EXEMPLE)
    config["parametres"] |= {"n_agents": 4, "duree": 60.0}
    chemin = tmp_path / "petit.yaml"
    chemin.write_text(yaml.safe_dump(config))
    png = tmp_path / "pression.png"
    args = ["pression", str(chemin), "--image", str(png), "--instant", "5"]
    assert main(args) == 0
    assert "résidu relatif" in capsys.readouterr().out
    with Image.open(png) as image:
        assert image.format == "PNG" and image.width > 1000
    original = png.read_bytes()
    assert main(args) == 1
    assert png.read_bytes() == original


@pytest.mark.parametrize("forme", [(3, 2), (2, 4, 2)])
def test_contraintes_de_mauvaise_forme_refusees(forme):
    from viscocrowd.io.trajectoires import Trajectoire
    from viscocrowd.viz.pression import LecteurPression

    x = np.zeros((2, 3, 2))
    donnees = Trajectoire(np.array([0.0, 1.0]), x, x, np.full(3, 0.2), {}, etats=None)
    with pytest.raises(ValueError, match="contraintes"):
        LecteurPression(donnees, np.zeros(forme), lambda *a: None, interactif=False)
