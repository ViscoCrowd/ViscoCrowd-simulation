"""Tests du schema d'integration semi-implicite, sans contrainte."""

import numpy as np
import pytest

from viscocrowd.core.integrator import chute_libre, pas_semi_implicite, trajectoire
from viscocrowd.core.state import GRAVITE, State


def chute_libre_exacte(x0, v0, g, dt, n):
    """Solution EXACTE du schema discret semi-implicite apres n pas.

    On ne compare pas a la parabole continue : le schema a sa propre solution
    fermee, et c'est elle qui doit etre reproduite au bit pres. Comparer a la
    solution continue melangerait erreur de discretisation et erreur de code,
    et le test ne saurait plus distinguer les deux.

        v_n = v0 + n dt g
        x_n = x0 + n dt v0 + dt^2 g n(n+1)/2
    """
    v = v0 + n * dt * g
    x = x0 + n * dt * v0 + dt**2 * g * (n * (n + 1) / 2.0)
    return x, v


class TestChuteLibre:
    def test_reproduit_la_solution_exacte_du_schema(self):
        dt, n_pas = 1e-3, 500
        x0 = np.array([0.3, 0.5])
        v0 = np.array([0.1, -0.2])

        etat = State(
            x=x0.reshape(1, 2).copy(),
            v=v0.reshape(1, 2).copy(),
            r=np.array([0.05]),
        )
        for _ in range(n_pas):
            etat = pas_semi_implicite(etat, dt, chute_libre(GRAVITE))

        x_attendu, v_attendu = chute_libre_exacte(x0, v0, GRAVITE, dt, n_pas)

        np.testing.assert_allclose(etat.x[0], x_attendu, rtol=0, atol=1e-12)
        np.testing.assert_allclose(etat.v[0], v_attendu, rtol=0, atol=1e-12)
        assert etat.t == pytest.approx(n_pas * dt)

    def test_la_masse_n_influence_pas_la_trajectoire(self):
        """La masse se simplifie dans la formulation par minimisation.

        Elle n'apparait nulle part dans le schema : c'est une propriete du
        modele, pas un detail d'implementation, donc elle merite un test.
        """
        etat = State.single((0.0, 1.0), (0.5, 0.0))
        _, x, _ = trajectoire(etat, 1e-3, 1.0, chute_libre(GRAVITE))

        # Aucune API ne permet de passer une masse a l'integrateur : la
        # trajectoire est donc identique quelle que soit la masse supposee.
        assert x.shape == (1001, 1, 2)

    def test_gravite_nulle_donne_un_mouvement_rectiligne_uniforme(self):
        etat = State.single((0.0, 0.0), (1.0, 2.0))
        t, x, v = trajectoire(etat, 1e-2, 1.0, chute_libre(np.zeros(2)))

        attendu = np.broadcast_to(np.array([1.0, 2.0]), (t.size, 2))
        np.testing.assert_allclose(v[:, 0, :], attendu, atol=1e-14)
        np.testing.assert_allclose(x[:, 0, 0], t * 1.0, atol=1e-12)
        np.testing.assert_allclose(x[:, 0, 1], t * 2.0, atol=1e-12)


class TestGardeFous:
    @pytest.mark.parametrize("dt", [0.0, -1e-3])
    def test_pas_de_temps_non_positif_rejete(self, dt):
        etat = State.single((0.0, 0.0))
        with pytest.raises(ValueError, match="strictement positif"):
            pas_semi_implicite(etat, dt, chute_libre(GRAVITE))

    def test_rayon_negatif_rejete(self):
        with pytest.raises(ValueError, match="rayons"):
            State(
                x=np.zeros((1, 2)),
                v=np.zeros((1, 2)),
                r=np.array([-0.1]),
            )

    def test_formes_incoherentes_rejetees(self):
        with pytest.raises(ValueError, match="meme forme"):
            State(
                x=np.zeros((3, 2)),
                v=np.zeros((2, 2)),
                r=np.ones(3),
            )
