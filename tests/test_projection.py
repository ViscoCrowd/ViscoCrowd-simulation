"""Tests unitaires de la projection sur l'exclusion entre agents."""

import numpy as np
import pytest

from viscocrowd.core.integrator import pas_semi_implicite
from viscocrowd.core.rng import generateur
from viscocrowd.core.state import State
from viscocrowd.geometry.boite import BoiteTournante
from viscocrowd.geometry.grille import recouvrement_max
from viscocrowd.geometry.projection import ProjectionExclusion

TOLERANCE = 1e-6
PRECISION_PAROI = 1e-14


class TestPaire:
    """Une paire isolee se corrige EXACTEMENT, en un balayage : c'est la loi de choc mou."""

    def test_chaque_disque_recule_de_la_moitie_du_recouvrement(self):
        r = np.array([0.1, 0.1])
        x = np.array([[0.0, 0.0], [0.15, 0.0]])  # recouvrement de 0,05 m

        proj = ProjectionExclusion(tolerance=TOLERANCE)
        y = proj(x, r, 0.0)

        np.testing.assert_allclose(y, [[-0.025, 0.0], [0.175, 0.0]], atol=1e-15)
        assert proj.iterations_max == 1

    def test_la_correction_suit_la_ligne_des_centres(self):
        """Pas d'axe privilegie : on le verifie sur une paire oblique."""
        r = np.array([0.1, 0.1])
        x = np.array([[0.0, 0.0], [0.09, 0.12]])  # distance 0,15 : recouvrement 0,05

        y = ProjectionExclusion(tolerance=TOLERANCE)(x, r, 0.0)

        assert np.linalg.norm(y[1] - y[0]) == pytest.approx(0.2, abs=1e-12)
        # Le centre de gravite ne bouge pas, et la direction des centres est conservee.
        np.testing.assert_allclose(y.mean(axis=0), x.mean(axis=0), atol=1e-15)
        direction = (y[1] - y[0]) / np.linalg.norm(y[1] - y[0])
        np.testing.assert_allclose(direction, [0.6, 0.8], atol=1e-12)

    def test_rayons_differents(self):
        r = np.array([0.05, 0.2])
        x = np.array([[0.0, 0.0], [0.2, 0.0]])  # somme des rayons 0,25 : recouvrement 0,05

        y = ProjectionExclusion(tolerance=TOLERANCE)(x, r, 0.0)

        assert np.linalg.norm(y[1] - y[0]) == pytest.approx(0.25, abs=1e-12)

    def test_disques_confondus_se_separent(self):
        """Centres identiques : pas de ligne des centres, on prend une direction fixe."""
        r = np.array([0.1, 0.1])
        y = ProjectionExclusion(tolerance=TOLERANCE)(np.zeros((2, 2)), r, 0.0)

        assert np.linalg.norm(y[1] - y[0]) == pytest.approx(0.2, abs=1e-12)

    def test_configuration_admissible_inchangee(self):
        """Projeter un point deja dans K ne doit rien deplacer, pas meme d'un epsilon."""
        r = np.full(3, 0.1)
        x = np.array([[0.0, 0.0], [0.2, 0.0], [0.0, 0.5]])  # deux disques tangents, un libre

        proj = ProjectionExclusion(tolerance=TOLERANCE)
        np.testing.assert_array_equal(proj(x, r, 0.0), x)


class TestChocMou:
    def test_deux_disques_qui_se_rencontrent_s_arretent_au_contact(self):
        """Choc de deux disques de vitesses opposees dans le schema complet.

        La vitesse est relue a partir du deplacement : la projection supprime la
        composante normale, les disques finissent en contact et AU REPOS, sans
        rebond. C'est la traduction discrete du choc mou, a verifier ici.
        """
        etat = State(
            x=np.array([[-0.5, 0.0], [0.5, 0.0]]),
            v=np.array([[1.0, 0.0], [-1.0, 0.0]]),
            r=np.array([0.1, 0.1]),
        )
        projection = ProjectionExclusion(tolerance=TOLERANCE)
        dt = 1e-3

        for _ in range(1000):
            etat = pas_semi_implicite(etat, dt, lambda e, _dt: e.v, projection)

        distance = np.linalg.norm(etat.x[1] - etat.x[0])
        assert distance >= 0.2 - TOLERANCE
        assert distance == pytest.approx(0.2, abs=1e-3)  # en contact, pas separes
        # Au repos, a la tolerance pres : un residu de TOLERANCE/dt serait deja trop.
        assert np.max(np.abs(etat.v)) < 5 * TOLERANCE / dt
        # Symetrie : le centre de gravite est reste a l'origine.
        np.testing.assert_allclose(etat.x.mean(axis=0), [0.0, 0.0], atol=1e-9)


class TestNuageDense:
    @pytest.fixture
    def boite(self):
        return BoiteTournante(demi_largeur=1.0)

    @pytest.mark.parametrize("graine", [0, 1, 2])
    def test_depart_tres_recouvrant(self, boite, graine):
        """100 disques tires au hasard, donc massivement recouverts : tout doit se resoudre."""
        n, rayon = 100, 0.04  # 20 % de la surface de la boite
        x = generateur(graine).uniform(-0.9, 0.9, size=(n, 2))
        r = np.full(n, rayon)
        assert recouvrement_max(x, r) > 0.05  # le depart est bien fautif

        proj = ProjectionExclusion(boite.projeter, tolerance=TOLERANCE, iterations=500)
        y = proj(x, r, 0.0)

        assert recouvrement_max(y, r) <= TOLERANCE
        assert boite.violation(y, r, 0.0) < PRECISION_PAROI
        assert proj.non_convergences == 0

    def test_rayons_heterogenes(self, boite):
        n = 60
        rng = generateur(7)
        x = rng.uniform(-0.8, 0.8, size=(n, 2))
        r = rng.uniform(0.03, 0.07, size=n)

        y = ProjectionExclusion(boite.projeter, tolerance=TOLERANCE, iterations=500)(x, r, 0.0)

        assert recouvrement_max(y, r) <= TOLERANCE
        assert boite.violation(y, r, 0.0) < PRECISION_PAROI

    def test_boite_en_rotation_evaluee_a_l_instant_d_arrivee(self):
        """Le domaine est appele avec le temps passe a la projection."""
        boite = BoiteTournante(demi_largeur=1.0, omega=3.0)
        n, t = 40, 0.7
        x = generateur(4).uniform(-0.9, 0.9, size=(n, 2))
        r = np.full(n, 0.05)

        y = ProjectionExclusion(boite.projeter, tolerance=TOLERANCE, iterations=500)(x, r, t)

        assert boite.violation(y, r, t) < PRECISION_PAROI


class TestLimites:
    def test_surcharge_impossible_est_signalee_sans_exception(self):
        """Plus de disques que la boite ne peut en contenir : on le MESURE, on ne le cache pas."""
        boite = BoiteTournante(demi_largeur=1.0)
        n = 100
        r = np.full(n, 0.17)  # surface des disques ~ 91 % de celle de la boite : impossible
        x = generateur(0).uniform(-0.8, 0.8, size=(n, 2))

        proj = ProjectionExclusion(boite.projeter, tolerance=TOLERANCE, iterations=50)
        y = proj(x, r, 0.0)

        assert proj.non_convergences == 1
        assert proj.recouvrement_max > TOLERANCE
        assert proj.iterations_max == 50
        # Meme en echec, les parois restent respectees : le domaine est reprojete en dernier.
        assert boite.violation(y, r, 0.0) < PRECISION_PAROI

    @pytest.mark.parametrize("n", [0, 1])
    def test_moins_de_deux_agents_seul_le_domaine_agit(self, n):
        boite = BoiteTournante(demi_largeur=1.0)
        x = np.full((n, 2), 5.0)  # loin hors de la boite
        r = np.full(n, 0.1)

        y = ProjectionExclusion(boite.projeter)(x, r, 0.0)

        assert y.shape == (n, 2)
        if n:
            assert boite.violation(y, r, 0.0) < PRECISION_PAROI

    def test_l_entree_n_est_pas_modifiee(self):
        r = np.array([0.1, 0.1])
        x = np.array([[0.0, 0.0], [0.15, 0.0]])
        copie = x.copy()

        ProjectionExclusion(tolerance=TOLERANCE)(x, r, 0.0)

        np.testing.assert_array_equal(x, copie)

    def test_compteurs_cumules(self):
        r = np.array([0.1, 0.1])
        proj = ProjectionExclusion(tolerance=TOLERANCE)
        proj(np.array([[0.0, 0.0], [0.15, 0.0]]), r, 0.0)
        proj(np.array([[0.0, 0.0], [1.0, 0.0]]), r, 0.0)

        assert proj.n_appels == 2
        assert proj.non_convergences == 0

    @pytest.mark.parametrize(
        ("kwargs", "message"),
        [({"tolerance": 0.0}, "tolerance"), ({"iterations": 0}, "iteration")],
    )
    def test_parametres_invalides(self, kwargs, message):
        with pytest.raises(ValueError, match=message):
            ProjectionExclusion(**kwargs)
