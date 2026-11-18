"""Relecture piscine : les agents au sol apparaissent, d'apres les evenements de chute."""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pytest

from viscocrowd.io.configuration import lire_configuration
from viscocrowd.io.trajectoires import Trajectoire
from viscocrowd.scenarios.piscine import NOMS_ETATS, PLAGE
from viscocrowd.ui.relecture_piscine import COULEUR_TERRE, LecteurPiscine, agents_a_terre

EXEMPLE = Path(__file__).parents[1] / "experiments/piscine.yaml"
T = np.array([0.0, 1.0, 2.0, 3.0, 4.0])


def chute(agent=0, instant=1.0, duree=2.0):
    return {
        "agent": agent,
        "instant": instant,
        "cause": "glissade",
        "duree_relevage": duree,
        "position": [35.0, 8.0],
    }


def donnees(chutes):
    config = lire_configuration(EXEMPLE)
    config["parametres"]["n_agents"] = 2
    if chutes is not None:
        config["parametres"]["chutes"] = {}
    x = np.tile(np.array([[35.0, 8.0], [40.0, 12.0]]), (len(T), 1, 1))
    evenements = {"sorties": [None, None]}
    if chutes is not None:
        evenements["chutes"] = chutes
    return Trajectoire(
        T,
        x,
        np.zeros_like(x),
        np.full(2, config["parametres"]["rayon"]),
        {"configuration": config, "etats": list(NOMS_ETATS), "evenements": evenements},
        etats=np.full((len(T), 2), PLAGE),
    )


def test_au_sol_de_l_instant_de_chute_jusqu_au_relevage_exclu():
    terre = agents_a_terre(T, 2, [chute(0, 1.0, 2.0), chute(1, 4.0, 10.0)])
    np.testing.assert_array_equal(terre[:, 0], [False, True, True, False, False])
    np.testing.assert_array_equal(terre[:, 1], [False, False, False, False, True])


@pytest.mark.parametrize(
    "fautive",
    [
        {"agent": 0, "instant": 1.0},
        chute(agent=5),
        chute(agent=1.0),
        chute(instant=np.nan),
        chute(instant=9.0),
        chute(duree=-1.0),
    ],
)
def test_evenement_de_chute_invalide(fautive):
    with pytest.raises(ValueError, match="chute"):
        agents_a_terre(T, 2, [fautive])


def test_vue_agent_au_sol_rouge_et_elargi_puis_releve():
    vue = LecteurPiscine(donnees([chute(0, 1.0, 2.0)]), interactif=False)
    try:
        rayon = vue.p.rayon
        vue.aller_au_temps(1.5)
        disque = vue.disques[0]
        assert matplotlib.colors.same_color(disque.get_facecolor(), COULEUR_TERRE)
        assert disque.get_radius() == pytest.approx(rayon * vue.p.chutes.facteur_rayon_terre)
        assert "À terre : 1" in vue.effectifs.get_text()
        assert "Chutes : 1" in vue.effectifs.get_text()
        assert "non calibrés" in vue.legende.get_text()
        vue.aller_au_temps(3.0)
        assert vue.disques[0].get_radius() == rayon
        assert "À terre : 0    Chutes : 1" in vue.effectifs.get_text()
    finally:
        plt.close(vue.figure)


def test_sans_module_de_chutes_la_vue_ne_change_pas():
    vue = LecteurPiscine(donnees(None), interactif=False)
    try:
        assert "À terre" not in vue.effectifs.get_text()
        assert "non calibrés" not in vue.legende.get_text()
        assert not vue.terre.any()
    finally:
        plt.close(vue.figure)
