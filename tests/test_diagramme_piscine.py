"""M8 devant la porte de la piscine (#124) : salle convexe, agents ignores, mesure reelle."""

from pathlib import Path

import numpy as np
import pytest

from viscocrowd.geometry.obstacle import ObstacleRectangle
from viscocrowd.io.configuration import lire_configuration
from viscocrowd.scenarios import diagramme_piscine as dp
from viscocrowd.scenarios.diagramme_goulot import serie_voronoi
from viscocrowd.scenarios.piscine import ParametresPiscine

EXEMPLE = Path(__file__).parents[1] / "experiments/piscine.yaml"


@pytest.fixture(scope="module")
def configuration():
    return lire_configuration(EXEMPLE)


@pytest.fixture(scope="module")
def piscine(configuration):
    return ParametresPiscine(**configuration["parametres"], graine=1).piscine


def test_salle_convexe_devant_la_porte(piscine):
    """La salle est un rectangle hors du bassin, qui contient la zone devant la porte."""
    salle = dp.salle_porte(piscine, 10.0)
    assert salle.x_min > piscine.bassin.x_max + 1.0
    assert salle.x_max == piscine.longueur_emprise
    zone = dp.zone_porte(piscine)
    assert salle.contient(zone)
    (_, y_bas), (_, y_haut) = piscine.porte
    assert zone.y_min < y_bas and zone.y_max > y_haut  # la zone couvre l'axe de la porte


@pytest.mark.parametrize("recul", [20.0, 19.5, 0.0, -1.0, float("nan")])
def test_recul_qui_atteint_le_bassin_refuse(piscine, recul):
    with pytest.raises(ValueError, match="recul"):
        dp.salle_porte(piscine, recul)


def test_obstacle_dans_la_salle_refuse(configuration):
    geometrie = configuration["parametres"]["geometrie"] | {
        "obstacles": [{"x_min": 44.0, "x_max": 45.0, "y_min": 2.0, "y_max": 3.0}]
    }
    p = ParametresPiscine(**(configuration["parametres"] | {"geometrie": geometrie}), graine=1)
    assert isinstance(p.piscine.obstacles[0], ObstacleRectangle)
    with pytest.raises(ValueError, match="obstacle"):
        dp.salle_porte(p.piscine, 10.0)


def test_agents_hors_de_la_salle_ignores(piscine):
    """Nageurs, agents deja sortis et agents loin de la porte n'ont pas de cellule."""
    salle, zone = dp.salle_porte(piscine, 10.0), dp.zone_porte(piscine)
    xs, ys = np.meshgrid(np.arange(40.5, 47.6, 0.6), np.arange(1.0, 19.6, 0.6))
    plage = np.column_stack((xs.ravel(), ys.ravel()))
    autres = np.array([[15.0, 10.0], [27.0, 5.0], [49.0, 10.25], [33.0, 10.0]])
    t = np.array([0.0, 0.1])
    deplacement = np.array([0.03, 0.0])  # tous a 0,3 m/s vers la porte
    seule = np.stack([plage, plage + deplacement])
    tous = np.stack([np.vstack([plage, autres]), np.vstack([plage + deplacement, autres])])
    a = serie_voronoi(t, seule, salle, zone)
    b = serie_voronoi(t, tous, salle, zone)
    np.testing.assert_allclose(b.densite, a.densite, rtol=0, atol=1e-12)
    np.testing.assert_allclose(b.vitesse, [0.3], rtol=0, atol=1e-12)


def test_mesure_reelle_courte(configuration):
    """Dix baigneurs, une graine : deux series, mouille et sec, dans le domaine physique."""
    config = configuration | {"parametres": configuration["parametres"] | {"n_agents": 10}}
    series = dp.mesurer(config, [1], recul=10.0, zone=None, debut=0.0, pas_mesure=10)
    assert set(series) == {("mouille", 1), ("sec", 1)}
    for s in series.values():
        assert s.t.size > 0
        assert np.all(np.isfinite(s.densite)) and np.all(s.densite >= 0)
        assert np.all(s.densite < 7.3)  # empilement compact des disques
        assert np.all(s.vitesse <= 1.5 * 1.34 * 1.5)  # m/s, marge sur la vitesse souhaitee
    classes = dp.agreger(series, 0.25)
    assert set(classes) == {"mouille", "sec"}
    np.testing.assert_array_equal(classes["mouille"].bornes, classes["sec"].bornes)
