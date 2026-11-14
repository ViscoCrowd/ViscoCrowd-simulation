"""M8 : diagramme fondamental, classes de densite et mesure devant le goulot E0 (#124)."""

import json
import math
from pathlib import Path

import numpy as np
import pytest
import yaml

from viscocrowd.cli import main
from viscocrowd.io.configuration import lire_configuration
from viscocrowd.observables.densite import Rectangle
from viscocrowd.observables.diagramme import classer
from viscocrowd.scenarios.diagramme_goulot import agreger, mesurer, serie_voronoi

GOULOT = Path(__file__).parents[1] / "experiments/goulot.yaml"


class TestClasser:
    def test_moyennes_et_ecarts_par_classe(self):
        rho = np.array([0.1, 0.2, 0.6, 0.7])
        v = np.array([1.0, 1.2, 0.5, 0.7])
        c = classer(rho, v, [0.0, 0.5, 1.0])
        np.testing.assert_array_equal(c.effectifs, [2, 2])
        np.testing.assert_allclose(c.densite, [0.15, 0.65])
        np.testing.assert_allclose(c.vitesse, [1.1, 0.6])
        np.testing.assert_allclose(c.debit, [(0.1 + 0.24) / 2, (0.3 + 0.49) / 2])
        np.testing.assert_allclose(c.ecart_vitesse, [np.std([1.0, 1.2], ddof=1)] * 2)

    def test_classe_vide_ou_d_un_seul_point(self):
        c = classer([0.1, 1.2], [1.0, 0.4], [0.0, 0.5, 1.0, 1.5])
        np.testing.assert_array_equal(c.effectifs, [1, 0, 1])
        assert math.isnan(c.vitesse[1]) and math.isnan(c.debit[1])
        assert math.isnan(c.ecart_vitesse[0])  # un seul point : pas d'ecart-type

    def test_hors_des_bornes_non_compte(self):
        """La borne haute est exclue : [b_k, b_k+1[."""
        c = classer([0.5, 1.0, 2.0], [1.0, 1.0, 1.0], [0.0, 1.0])
        np.testing.assert_array_equal(c.effectifs, [1])

    @pytest.mark.parametrize(
        ("rho", "v", "bornes"),
        [
            ([np.nan], [1.0], [0.0, 1.0]),
            ([-0.1], [1.0], [0.0, 1.0]),
            ([0.1], [-1.0], [0.0, 1.0]),
            ([0.1], [1.0], [1.0, 0.0]),
            ([0.1], [1.0], [0.0]),
            ([0.1, 0.2], [1.0], [0.0, 1.0]),
        ],
    )
    def test_entrees_refusees(self, rho, v, bornes):
        with pytest.raises(ValueError):
            classer(rho, v, bornes)


def reseau_en_translation(a: float, vitesse: np.ndarray, t: np.ndarray) -> np.ndarray:
    """Reseau hexagonal de pas a, translate a vitesse constante : (P, N, 2)."""
    points = [
        (x0 + (0.5 * a if k % 2 else 0.0), y0)
        for k, y0 in enumerate(np.arange(1.0, 9.0, a * math.sqrt(3) / 2))
        for x0 in np.arange(1.0, 18.0, a)
    ]
    x0 = np.array(points)
    return x0[None, :, :] + t[:, None, None] * vitesse[None, None, :]


class TestSerieVoronoi:
    SALLE = Rectangle(0.0, 20.0, 0.0, 10.0)
    ZONE = Rectangle(8.0, 12.0, 4.0, 6.0)

    def test_reseau_hexagonal_exact(self):
        """Densite 2 / (sqrt(3) a^2) et vitesse |v| exactes, quel que soit le cadrage de M."""
        a, vitesse = 0.6, np.array([0.8, 0.3])
        t = np.array([0.0, 0.1, 0.2, 0.3])
        serie = serie_voronoi(t, reseau_en_translation(a, vitesse, t), self.SALLE, self.ZONE)
        np.testing.assert_allclose(serie.t, t[1:])
        np.testing.assert_allclose(serie.densite, 2.0 / (math.sqrt(3) * a**2), rtol=1e-9)
        np.testing.assert_allclose(serie.vitesse, np.hypot(*vitesse), rtol=1e-9)
        np.testing.assert_allclose(serie.debit, serie.densite * serie.vitesse)

    def test_debut_et_pas_de_mesure(self):
        t = np.arange(0.0, 1.05, 0.1)
        x = reseau_en_translation(0.6, np.array([0.5, 0.0]), t)
        serie = serie_voronoi(t, x, self.SALLE, self.ZONE, debut=0.25, pas_mesure=3)
        np.testing.assert_allclose(serie.t, [0.3, 0.6, 0.9])

    def test_agents_hors_de_la_salle_ignores(self):
        """Un agent deja engage dans le goulot, hors de la salle, n'a pas de cellule."""
        t = np.array([0.0, 0.1])
        x = reseau_en_translation(0.6, np.array([0.5, 0.0]), t)
        dehors = np.array([[[25.0, 5.0]], [[25.05, 5.0]]])
        avec = serie_voronoi(t, np.concatenate([x, dehors], axis=1), self.SALLE, self.ZONE)
        sans = serie_voronoi(t, x, self.SALLE, self.ZONE)
        np.testing.assert_array_equal(avec.densite, sans.densite)

    @pytest.mark.parametrize(
        ("t", "options"),
        [
            (np.array([0.0, 0.0]), {}),
            (np.array([0.0, 0.1]), {"pas_mesure": 0}),
            (np.array([0.0, 0.1]), {"debut": np.nan}),
        ],
    )
    def test_entrees_refusees(self, t, options):
        x = reseau_en_translation(0.6, np.array([0.5, 0.0]), t)
        with pytest.raises(ValueError):
            serie_voronoi(t, x, self.SALLE, self.ZONE, **options)


@pytest.fixture
def goulot_reduit(tmp_path):
    """E0 a 20 agents : quelques secondes de calcul, une vraie foule devant le goulot."""
    configuration = lire_configuration(GOULOT)
    configuration["parametres"]["n_agents"] = 20
    configuration["parametres"]["duree"] = 30.0
    chemin = tmp_path / "goulot.yaml"
    chemin.write_text(yaml.safe_dump(configuration), encoding="utf-8")
    return configuration, chemin


class TestGoulotReel:
    def test_points_plausibles_et_classes(self, goulot_reduit):
        configuration, _ = goulot_reduit
        zone = Rectangle(6.0, 7.8, 1.5, 3.5)
        series = mesurer(configuration, [1.2], [1], zone, debut=1.0, pas_mesure=10)
        (serie,) = series.values()
        assert serie.t.size > 10 and np.all(serie.t >= 1.0)
        # Densite physique : sous l'empilement compact de disques de 0,2 m (7,2 pers/m^2).
        assert np.all((serie.densite > 0.0) & (serie.densite < 7.3))
        # Vitesse : jamais au-dela de la vitesse souhaitee, 1,34 m/s au facteur 1.
        assert np.all((serie.vitesse >= 0.0) & (serie.vitesse <= 1.34 + 1e-9))
        classes = agreger(series, 0.5)
        assert classes.effectifs.sum() == serie.t.size

    def test_zone_hors_de_la_salle_refusee(self, goulot_reduit):
        configuration, _ = goulot_reduit
        with pytest.raises(ValueError, match="incluse"):
            mesurer(
                configuration, [1.2], [1], Rectangle(7.0, 9.0, 1.5, 3.5), debut=1.0, pas_mesure=10
            )

    def test_commande(self, goulot_reduit, tmp_path, capsys):
        _, chemin = goulot_reduit
        bilan = tmp_path / "m8" / "diagramme.json"
        code = main(
            [
                "diagramme-goulot",
                str(chemin),
                "--largeurs",
                "1.2",
                "--graines",
                "1",
                "--figure",
                str(tmp_path),
                "--sortie",
                str(bilan),
            ]
        )
        assert code == 0
        assert (tmp_path / "fig08_diagramme_fondamental.png").exists()
        contenu = json.loads(bilan.read_text(encoding="utf-8"))
        (serie,) = contenu["series"]
        assert sum(contenu["classes"]["effectifs"]) == len(serie["t"])
        assert "Weidmann" in capsys.readouterr().out

    def test_commande_refuse_un_autre_scenario(self, capsys):
        piscine = Path(__file__).parents[1] / "experiments/piscine.yaml"
        assert main(["diagramme-goulot", str(piscine), "--graines", "1"]) == 1
        assert "goulot" in capsys.readouterr().err
