"""Obstacle rectangulaire : projection exacte hors de l'obstacle, et couloir qui l'integre."""

import numpy as np
import pytest

from viscocrowd.geometry.couloir import Couloir
from viscocrowd.geometry.obstacle import ObstacleRectangle

PILIER = ObstacleRectangle(6.0, 7.0, -0.5, 0.5)
R = 0.2


class TestRepousser:
    def test_point_pres_d_une_face_ramene_a_un_rayon(self):
        x = PILIER.repousser(np.array([[5.9, 0.1]]), R)
        np.testing.assert_allclose(x, [[5.8, 0.1]], atol=1e-15)

    def test_point_pres_d_un_coin_ramene_sur_l_arrondi(self):
        """Le rectangle gonfle a des coins arrondis : on recule le long de la diagonale."""
        x = PILIER.repousser(np.array([[5.95, 0.55]]), R)
        np.testing.assert_allclose(np.linalg.norm(x[0] - [6.0, 0.5]), R, atol=1e-15)
        np.testing.assert_allclose((x[0] - [6.0, 0.5]) / R, [-np.sqrt(0.5), np.sqrt(0.5)])

    @pytest.mark.parametrize(
        ("dedans", "attendu"),
        [
            ([6.1, 0.0], [5.8, 0.0]),  # face gauche la plus proche
            ([6.95, 0.1], [7.2, 0.1]),  # face droite
            ([6.5, -0.45], [6.5, -0.7]),  # face basse
            ([6.5, 0.45], [6.5, 0.7]),  # face haute
        ],
    )
    def test_centre_dans_l_obstacle_sort_par_la_face_la_plus_proche(self, dedans, attendu):
        np.testing.assert_allclose(PILIER.repousser(np.array([dedans]), R), [attendu])

    def test_points_admissibles_inchanges_et_projection_idempotente(self):
        x = np.random.default_rng(4).uniform([4.0, -2.0], [9.0, 2.0], size=(2000, 2))
        une_fois = PILIER.repousser(x, R)
        loin = PILIER.distance(x) >= R
        np.testing.assert_array_equal(une_fois[loin], x[loin])
        np.testing.assert_allclose(PILIER.repousser(une_fois, R), une_fois, atol=1e-14)
        assert PILIER.violation(une_fois, R) <= 1e-15
        # Et la projection deplace au minimum : jamais plus loin que le bord gonfle.
        assert np.all(PILIER.distance(une_fois[~loin]) <= R + 1e-12)

    def test_violation_mesure_le_chevauchement_y_compris_au_coeur(self):
        x = np.array([[5.9, 0.0], [6.5, 0.0], [3.0, 0.0]])
        assert PILIER.violation(x[:1], R) == pytest.approx(0.1)
        assert PILIER.violation(x[1:2], R) == pytest.approx(0.5 + R)  # profondeur 0,5 m
        assert PILIER.violation(x[2:], R) == 0.0

    @pytest.mark.parametrize("bornes", [(1.0, 1.0, 0.0, 1.0), (0.0, 1.0, np.nan, 1.0)])
    def test_obstacle_degenere_refuse(self, bornes):
        with pytest.raises(ValueError):
            ObstacleRectangle(*bornes)


class TestCouloirAvecObstacle:
    def test_parois_et_obstacle_respectes_a_la_precision_machine(self):
        couloir = Couloir(12.0, 3.0, (PILIER,))
        x = np.random.default_rng(5).uniform([-1.0, -2.0], [13.0, 2.0], size=(5000, 2))
        r = np.full(5000, R)
        projete = couloir.projeter(x, r, 0.0)
        assert couloir.violation(projete, r, 0.0) <= 1e-15

    def test_violation_detecte_le_pilier(self):
        couloir = Couloir(12.0, 3.0, (PILIER,))
        assert couloir.violation(np.array([[6.5, 0.0]]), np.array([R]), 0.0) == pytest.approx(0.7)

    @pytest.mark.parametrize(
        "obstacle",
        [
            ObstacleRectangle(-1.0, 1.0, -0.5, 0.5),  # traverse la paroi amont
            ObstacleRectangle(5.0, 6.0, -2.0, 0.0),  # depasse la paroi laterale
        ],
    )
    def test_obstacle_hors_du_couloir_refuse(self, obstacle):
        with pytest.raises(ValueError, match="interieur"):
            Couloir(12.0, 3.0, (obstacle,))
