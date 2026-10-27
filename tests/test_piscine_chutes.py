"""Tests de l'integration du modele de chutes et de la carte 2D des incidents."""

from pathlib import Path

from viscocrowd.io.configuration import lire_configuration
from viscocrowd.model.chutes import ParametresChutes
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
