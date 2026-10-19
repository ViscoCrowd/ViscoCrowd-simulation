"""Tests de l'effet du sol sur la marche (spec § 2.4).

Les valeurs de tau et a_max utilisees ici sont ILLUSTRATIVES : elles servent a
verifier le comportement du schema, pas a calibrer les milieux (tache C6).
"""

import numpy as np
import pytest

from viscocrowd.model.milieu import acceleration, vitesse_libre


def un_agent(vecteur: tuple[float, float]) -> np.ndarray:
    return np.array([vecteur], dtype=float)


class TestAcceleration:
    def test_sans_limite_on_corrige_l_ecart_en_un_temps_tau(self):
        """Ecart de 1 m/s, tau = 0,5 s : acceleration de 1 / 0,5 = 2 m/s^2."""
        a = acceleration(un_agent((0.0, 0.0)), un_agent((1.0, 0.0)), 0.5, 10.0)
        np.testing.assert_allclose(a, [[2.0, 0.0]])

    def test_l_adherence_borne_la_norme_sans_changer_la_direction(self):
        """L'agent voudrait (3, 4) m/s^2, de norme 5 ; le sol n'en permet que 1.

        On garde la direction (3, 4) et on ramene la norme a 1 : (0,6 ; 0,8).
        Borner chaque composante a 1 aurait donne (1, 1), une autre direction.
        """
        a = acceleration(un_agent((0.0, 0.0)), un_agent((3.0, 4.0)), 1.0, 1.0)

        np.testing.assert_allclose(a, [[0.6, 0.8]])
        assert np.linalg.norm(a) == pytest.approx(1.0)

    def test_agent_deja_a_sa_vitesse_desiree(self):
        """Aucun ecart : acceleration nulle, et surtout pas de division par zero."""
        a = acceleration(un_agent((1.0, 0.5)), un_agent((1.0, 0.5)), 0.5, 2.0)
        np.testing.assert_array_equal(a, [[0.0, 0.0]])

    def test_parametres_differents_pour_chaque_agent(self):
        """Deux agents, meme envie, sols differents : seul celui du sol glissant est borne."""
        v = np.zeros((2, 2))
        u = np.array([[1.5, 0.0], [1.5, 0.0]])
        a = acceleration(v, u, relaxation=0.5, acceleration_max=np.array([5.9, 1.0]))

        np.testing.assert_allclose(a, [[3.0, 0.0], [1.0, 0.0]])

    @pytest.mark.parametrize("nom", ["relaxation", "acceleration_max"])
    @pytest.mark.parametrize("valeur", [0.0, -1.0, np.nan])
    def test_parametre_invalide_rejete(self, nom, valeur):
        parametres = {"relaxation": 0.5, "acceleration_max": 2.0, nom: valeur}
        with pytest.raises(ValueError, match=nom):
            acceleration(un_agent((0.0, 0.0)), un_agent((1.0, 0.0)), **parametres)

    def test_vitesse_non_finie_rejetee(self):
        with pytest.raises(ValueError, match="non finies"):
            acceleration(un_agent((np.nan, 0.0)), un_agent((1.0, 0.0)), 0.5, 2.0)


def marcher(v0, u, relaxation, acceleration_max, dt=1e-3, duree=5.0):
    """Fait marcher un agent seul, sans contrainte. Rend sa vitesse et sa distance parcourue."""
    v = un_agent(v0)
    u = un_agent(u)
    distance = 0.0
    for _ in range(round(duree / dt)):
        v = vitesse_libre(v, u, relaxation, acceleration_max, dt)
        distance += (
            float(np.linalg.norm(v)) * dt
        )  # semi-implicite : position avec la vitesse NOUVELLE
    return v, distance


class TestComportement:
    def test_relaxation_exponentielle(self):
        """Sans limite d'adherence, au bout d'un temps tau l'agent a rattrape 63 % de l'ecart.

        C'est la definition physique de tau : l'ecart decroit comme exp(-t / tau),
        donc il reste exp(-1) = 37 % de l'ecart initial a t = tau.
        """
        tau = 0.5
        v, _ = marcher((0.0, 0.0), (1.0, 0.0), tau, acceleration_max=1e6, dt=1e-4, duree=tau)
        assert v[0, 0] == pytest.approx(1.0 - np.exp(-1.0), abs=1e-3)

    def test_freinage_plus_long_sur_sol_glissant(self):
        """L'inertie du carrelage mouille, en un test.

        Un agent lance a 1,5 m/s veut s'arreter net. Sur sol sec (a_max eleve)
        il s'arrete vite ; sur sol glissant, le sol ne fournit pas la traction :
        il glisse plus loin. Tant que l'adherence est saturee, la distance
        d'arret est celle d'un freinage a a_max constant, v0^2 / (2 a_max).
        """
        v0 = 1.5
        _, distance_sec = marcher((v0, 0.0), (0.0, 0.0), relaxation=0.1, acceleration_max=5.9)
        v_fin, distance_mouille = marcher(
            (v0, 0.0), (0.0, 0.0), relaxation=0.1, acceleration_max=1.0
        )

        assert distance_mouille > 3 * distance_sec
        assert distance_mouille == pytest.approx(v0**2 / (2 * 1.0), rel=0.05)
        assert np.linalg.norm(v_fin) < 1e-6  # il finit bien par s'arreter

    def test_vitesse_libre_rejette_un_pas_de_temps_invalide(self):
        with pytest.raises(ValueError, match="pas de temps"):
            vitesse_libre(un_agent((0.0, 0.0)), un_agent((1.0, 0.0)), 0.5, 2.0, dt=0.0)
