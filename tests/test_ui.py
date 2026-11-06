"""Tests de l'apercu de la piscine : mise en forme pure, sans ouvrir de fenetre."""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # rendu hors ecran : aucun test ne doit ouvrir de fenetre
import matplotlib.pyplot as plt
import numpy as np
import pytest
from matplotlib.backend_bases import MouseEvent

from viscocrowd.io.configuration import lire_configuration
from viscocrowd.model.milieu import ParametresMilieu
from viscocrowd.scenarios.piscine import ParametresPiscine
from viscocrowd.ui import parametres as module_parametres
from viscocrowd.ui.parametres import ParametresAffichage
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
    assert p.eau is None and p.mouille is None and p.sec is None


def test_creer_figure_sans_parametres():
    fig = creer_figure()
    try:
        axes = {ax.get_label(): ax for ax in fig.axes}
        assert axes["plan"].get_visible()
        assert not axes["parametres"].get_visible()
        assert axes["commande_parametres"].get_visible()
    finally:
        plt.close(fig)


def test_creer_figure_avec_parametres():
    eau = ParametresMilieu(relaxation=0.5, acceleration_max=1.6, vitesse=0.5)
    parametres = ParametresAffichage(nombre_agents=100, dt=0.01, eau=eau)
    fig = creer_figure(parametres=parametres, temps_simule=12.5, afficher_parametres=True)
    try:
        textes = [t.get_text() for t in fig.findobj(matplotlib.text.Text)]
        assert "00:12.50" in textes
        assert "100" in textes
    finally:
        plt.close(fig)


def test_une_seule_classe_de_milieu_pour_le_modele_et_l_affichage():
    """L'interface reutilise la classe du modele, controles compris (#26, point 3)."""
    assert module_parametres.ParametresMilieu is ParametresMilieu
    with pytest.raises(ValueError):
        ParametresAffichage(
            eau=ParametresMilieu(relaxation=0.5, acceleration_max=-1.0, vitesse=0.5)
        )


def test_panneau_rempli_depuis_le_scenario_piscine():
    """Les valeurs affichees sont celles du YAML de reference, sans recopie a la main."""
    config = lire_configuration(Path(__file__).parents[1] / "experiments/piscine.yaml")
    p = ParametresPiscine(**config["parametres"], graine=config["graine"])
    affichage = ParametresAffichage.depuis_piscine(p)
    milieux = config["parametres"]["parametres_milieux"]
    assert affichage.eau == ParametresMilieu(**milieux["EAU"])
    assert affichage.mouille == ParametresMilieu(**milieux["MOUILLE"])
    assert affichage.sec == ParametresMilieu(**milieux["SEC"])
    assert affichage.nombre_agents == p.n_agents and affichage.graine == p.graine
    assert affichage.niveau_panique == p.facteur_vitesse
    assert affichage.longueur_zone_mouillee == p.piscine.largeur_mouillee
    assert (affichage.temps_rebord, affichage.temps_echelle) == (
        p.durees["rebord"],
        p.durees["echelle"],
    )
    fig = creer_figure(parametres=affichage, afficher_parametres=True)
    try:
        textes = [t.get_text() for t in fig.findobj(matplotlib.text.Text)]
        assert "0,69" in textes  # vitesse dans l'eau, shirvani2020
        assert textes.count("1,34") == 2  # mouille et sec
    finally:
        plt.close(fig)


@pytest.mark.parametrize("afficher_parametres", [False, True])
def test_bouton_parametres_conserve_zoom_valeurs_et_echelle(afficher_parametres):
    """De vrais clics doivent liberer la place sans perdre l'etat de la vue."""
    fig = creer_figure(
        parametres=ParametresAffichage(nombre_agents=100),
        temps_simule=12.5,
        afficher_parametres=afficher_parametres,
    )
    try:
        axes = {ax.get_label(): ax for ax in fig.axes}
        plan, panneau = axes["plan"], axes["parametres"]
        # Un utilisateur a zoome puis redimensionne sa fenetre avant de cliquer.
        plan.set(xlim=(10, 45), ylim=(0, 15))
        fig.set_size_inches(10, 7)
        fig.canvas.draw()
        for _ in range(2):
            visible = panneau.get_visible()
            largeur_avant = plan.bbox.width
            x, y = axes["commande_parametres"].transAxes.transform((0.5, 0.5))
            for nom in ("button_press_event", "button_release_event"):
                evenement = MouseEvent(nom, fig.canvas, x, y, button=1)
                fig.canvas.callbacks.process(nom, evenement)
            fig.canvas.draw()

            assert panneau.get_visible() is not visible
            assert plan.bbox.width > largeur_avant if visible else plan.bbox.width < largeur_avant
            np.testing.assert_allclose(plan.get_xlim(), (10, 45))
            np.testing.assert_allclose(plan.get_ylim(), (0, 15))
            origine, x_unite, y_unite = plan.transData.transform([(0, 0), (1, 0), (0, 1)])
            assert np.linalg.norm(x_unite - origine) == pytest.approx(
                np.linalg.norm(y_unite - origine)
            )
            assert "100" in [texte.get_text() for texte in panneau.texts]
            assert "00:12.50" in [texte.get_text() for texte in fig.texts]
        assert panneau.get_visible() == afficher_parametres
    finally:
        plt.close(fig)
