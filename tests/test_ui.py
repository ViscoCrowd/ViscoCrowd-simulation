"""Tests de l'apercu de la piscine : mise en forme pure, sans ouvrir de fenetre."""

import matplotlib

matplotlib.use("Agg")  # rendu hors ecran : aucun test ne doit ouvrir de fenetre
import matplotlib.pyplot as plt
import numpy as np
import pytest

from viscocrowd.ui.parametres import ParametresAffichage, ParametresMilieu
from viscocrowd.ui.piscine import _formater_temps, _formater_valeur, creer_figure


@pytest.mark.parametrize(
    ("secondes", "attendu"),
    [
        (0.0, "00:00.00"),
        (12.5, "00:12.50"),
        (59.99, "00:59.99"),
        (60.0, "01:00.00"),
        (3725.5, "62:05.50"),
    ],
)
def test_formater_temps(secondes, attendu):
    assert _formater_temps(secondes) == attendu


def test_formater_temps_ne_deborde_pas_a_l_arrondi():
    """59,999 s s'arrondit a 60 s : la minute doit passer, pas afficher 00:59.100."""
    assert _formater_temps(59.999) == "01:00.00"


@pytest.mark.parametrize("invalide", [-0.01, float("nan"), float("inf")])
def test_formater_temps_refuse_les_valeurs_invalides(invalide):
    with pytest.raises(ValueError, match="temps simule"):
        _formater_temps(invalide)


@pytest.mark.parametrize(
    ("valeur", "attendu"),
    [
        (None, "—"),
        (100, "100"),
        (np.int64(100), "100"),
        (20262027, "20262027"),
        (0.5, "0,5"),
        (0.123456, "0,1235"),
    ],
)
def test_formater_valeur(valeur, attendu):
    assert _formater_valeur(valeur) == attendu


def test_parametres_vides_par_defaut():
    """Aucune valeur physique n'est imposee : tout est non renseigne."""
    p = ParametresAffichage()
    assert p.nombre_agents is None
    assert p.dt is None
    assert p.graine is None
    assert p.eau == ParametresMilieu()
    assert p.mouille.acceleration_max is None


def test_creer_figure_sans_parametres():
    fig = creer_figure()
    try:
        assert len(fig.axes) == 2  # le plan et le panneau de parametres
    finally:
        plt.close(fig)


def test_creer_figure_avec_parametres():
    parametres = ParametresAffichage(nombre_agents=100, dt=0.01, eau=ParametresMilieu(vitesse=0.5))
    fig = creer_figure(parametres=parametres, temps_simule=12.5)
    try:
        textes = [t.get_text() for t in fig.findobj(matplotlib.text.Text)]
        assert "00:12.50" in textes
        assert "100" in textes
    finally:
        plt.close(fig)
