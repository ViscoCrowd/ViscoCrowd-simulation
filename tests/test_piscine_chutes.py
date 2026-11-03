"""Tests de l'integration du modele de chutes et de la carte 2D des incidents."""

import json
import math
from pathlib import Path

import numpy as np
import pytest
import yaml

from viscocrowd.core.rng import generateur
from viscocrowd.io.configuration import lire_configuration
from viscocrowd.model.chutes import GestionnaireChutes, ParametresChutes
from viscocrowd.scenarios.experience import executer_configuration
from viscocrowd.scenarios.piscine import ParametresPiscine, simuler_piscine
from viscocrowd.viz.figures import figure_carte_chutes

EXEMPLE = Path(__file__).parents[1] / "experiments/piscine.yaml"


def test_simulation_piscine_sans_chutes_par_defaut():
    config = lire_configuration(EXEMPLE)
    p = ParametresPiscine(
        **(config["parametres"] | {"n_agents": 5, "duree": 20.0}),
        graine=config["graine"],
    )
    assert p.chutes is None
    r = simuler_piscine(p)
    assert r.chutes == ()


def test_simulation_piscine_avec_chutes_actives(tmp_path):
    config = lire_configuration(EXEMPLE)
    params_chutes = ParametresChutes(lambda_chute=50.0, lambda_domino=50.0)
    p = ParametresPiscine(
        **(
            config["parametres"]
            | {
                "n_agents": 8,
                "facteur_vitesse": 1.4,
                "duree": 40.0,
                "durees": {"rebord": 1.0, "echelle": 0.5},
                "chutes": params_chutes,
            }
        ),
        graine=123,
    )
    r = simuler_piscine(p)

    # Verifier que les incidents de chutes sont enregistres
    assert len(r.chutes) > 0
    causes = {c.cause for c in r.chutes}
    assert causes.issubset({"glissade", "domino"})

    # Invariants physiques respectes meme avec les chutes
    assert r.violation_paroi_max() <= 1e-14

    # Generation de la carte 2D des chutes
    chemin_figure = figure_carte_chutes(r, tmp_path)
    assert chemin_figure.exists()
    assert chemin_figure.stat().st_size > 1000


def _parametres(n_agents=1, graine=1, **autres):
    config = lire_configuration(EXEMPLE)
    return ParametresPiscine(
        **(config["parametres"] | {"n_agents": n_agents} | autres), graine=graine
    )


def _adherence_illimitee():
    milieux = lire_configuration(EXEMPLE)["parametres"]["parametres_milieux"]
    return {nom: {**m, "acceleration_max": 1e6} for nom, m in milieux.items()}


def test_sans_exces_d_adherence_le_module_ne_change_rien():
    """Spec § 7.2 : tout ecart signalerait un couplage parasite."""
    milieux = _adherence_illimitee()
    sans = simuler_piscine(_parametres(20, parametres_milieux=milieux))
    avec = simuler_piscine(_parametres(20, parametres_milieux=milieux, chutes=ParametresChutes()))
    assert avec.chutes == ()
    np.testing.assert_array_equal(avec.x, sans.x)


def test_meme_graine_memes_chutes():
    """Spec § 7.4 : malgre l'alea, deux executions sont identiques au bit pres."""
    chutes = ParametresChutes(lambda_chute=50.0, lambda_domino=50.0)
    a = simuler_piscine(_parametres(8, facteur_vitesse=1.4, chutes=chutes))
    b = simuler_piscine(_parametres(8, facteur_vitesse=1.4, chutes=chutes))
    assert a.chutes and a.chutes == b.chutes
    np.testing.assert_array_equal(a.x, b.x)


@pytest.mark.invariant
def test_tomber_ne_depasse_pas_l_adherence():
    """Au pas de la chute, l'agent freine sous a_max : il ne s'arrete pas d'un coup.

    Seul ce pas est controle : ensuite, pres d'un bord, le rayon qui grandit fait
    repousser le corps par la projection, comme tout contact, sans borne d'adherence.
    """
    # Sol tres glissant : l'agent accelere longtemps sous a_max, et tombe donc en marchant.
    milieux = lire_configuration(EXEMPLE)["parametres"]["parametres_milieux"]
    milieux = milieux | {"MOUILLE": milieux["MOUILLE"] | {"acceleration_max": 1.0}}
    p = _parametres(
        graine=4,
        facteur_vitesse=1.4,
        parametres_milieux=milieux,
        chutes=ParametresChutes(lambda_chute=1.0),
    )
    r = simuler_piscine(p)
    assert r.chutes
    a_max = max(m.acceleration_max for m in p.parametres_milieux.values())
    vitesse_max = 0.0
    for chute in r.chutes:
        k = int(np.searchsorted(r.t, chute.instant - 1e-9))
        vitesse_max = max(vitesse_max, np.hypot(*r.v[k, 0]))
        assert np.hypot(*(r.v[k + 1, 0] - r.v[k, 0])) / p.dt <= a_max * (1 + 1e-9)
    assert vitesse_max > 0.1  # sinon, s'arreter d'un coup passerait aussi le test


@pytest.mark.invariant
def test_les_corps_au_sol_respectent_les_murs_avec_leur_rayon_reel():
    """La violation rapportee porte sur le rayon elargi, pas sur le rayon nominal."""
    chutes = ParametresChutes(lambda_chute=50.0, lambda_domino=50.0)
    r = simuler_piscine(_parametres(20, facteur_vitesse=1.4, chutes=chutes))
    assert r.chutes
    assert r.violation_paroi_max() <= 1e-14


def test_un_corps_sorti_n_est_plus_un_obstacle():
    """Un corps pousse dehors cesse d'etre un obstacle pour ceux qui restent."""
    gestionnaire = GestionnaireChutes(2, ParametresChutes(), 0)
    gestionnaire.faire_tomber(0, 0.0, "glissade", (1.0, 1.0))
    gestionnaire.retirer(0)
    assert gestionnaire.nombre_a_terre == 0
    direction = np.array([[1.0, 0.0], [1.0, 0.0]])
    x = np.array([[0.0, 1.0], [0.0, 1.0]])
    resultat = gestionnaire.vitesses_desirees_effectives(x, direction, np.full(2, 0.2))
    np.testing.assert_array_equal(resultat, direction)


def test_les_chutes_ont_leur_propre_flux_de_tirages():
    """Les chutes ne relisent pas les tirages qui ont place les agents."""
    assert generateur(7).uniform() != GestionnaireChutes(1, ParametresChutes(), 7).rng.uniform()


@pytest.mark.parametrize("dt", [0.01, 0.005, 0.0025])
def test_probabilite_de_chute_independante_de_dt(dt):
    """Spec § 7.1 : a exces constant, la fraction tombee suit 1 - exp(-lambda exces T)."""
    n, duree, exces = 4000, 0.5, 1.0
    parametres = ParametresChutes(lambda_chute=2.0, mediane_relevage=1e6)
    gestionnaire = GestionnaireChutes(n, parametres, 3)
    vitesse_desiree = np.tile([(1.0 + exces) * 0.5, 0.0], (n, 1))  # |U - 0| / tau = 1 + exces
    arguments = {
        "x": np.zeros((n, 2)),
        "v": np.zeros((n, 2)),
        "vitesse_desiree": vitesse_desiree,
        "a_max": np.ones(n),
        "tau": np.full(n, 0.5),
        "rayons_nominaux": np.full(n, 0.2),
    }
    for pas in range(round(duree / dt)):
        gestionnaire.mettre_a_jour(instant=pas * dt, dt=dt, **arguments)
    attendu = 1.0 - math.exp(-parametres.lambda_chute * exces * duree)
    ecart_type = math.sqrt(attendu * (1.0 - attendu) / n)
    assert abs(gestionnaire.nombre_a_terre / n - attendu) < 3.0 * ecart_type


def test_les_parametres_et_les_chutes_vont_dans_l_archive(tmp_path):
    """La carte des chutes se retrouve depuis l'archive, avec ses parametres."""
    config = lire_configuration(EXEMPLE)
    config["parametres"] |= {
        "n_agents": 8,
        "facteur_vitesse": 1.4,
        "duree": 40.0,
        "chutes": {"lambda_chute": 50.0, "lambda_domino": 50.0},
    }
    source = tmp_path / "chutes.yaml"
    source.write_text(yaml.safe_dump(config), encoding="utf-8")
    json.dumps(_parametres(chutes=ParametresChutes()).en_dictionnaire(), allow_nan=False)

    archive = executer_configuration(source, tmp_path / "chutes.npz")

    assert archive.metadonnees["configuration"]["parametres"]["chutes"]["lambda_chute"] == 50.0
    assert archive.metadonnees["evenements"]["chutes"]
