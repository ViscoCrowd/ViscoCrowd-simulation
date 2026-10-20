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

    @pytest.mark.parametrize("dt", [0.0, -1e-3, np.nan])
    def test_vitesse_libre_rejette_un_pas_de_temps_invalide(self, dt):
        with pytest.raises(ValueError, match="pas de temps"):
            vitesse_libre(un_agent((0.0, 0.0)), un_agent((1.0, 0.0)), 0.5, 2.0, dt=dt)


def parcourir(v0, u, relaxation, acceleration_max, dt=1e-3, duree=5.0):
    """Fait marcher un agent seul, sans contrainte, parti de l'origine.

    Returns:
        Positions et vitesses a chaque pas, de forme (P, 2), en m et m/s.
    """
    v = un_agent(v0)
    u = un_agent(u)
    x = np.zeros((1, 2))
    positions, vitesses = [x[0]], [v[0]]
    for _ in range(round(duree / dt)):
        v = vitesse_libre(v, u, relaxation, acceleration_max, dt)
        x = x + dt * v  # semi-implicite : position avec la vitesse NOUVELLE
        positions.append(x[0])
        vitesses.append(v[0])
    return np.array(positions), np.array(vitesses)


def marcher(v0, u, relaxation, acceleration_max, dt=1e-3, duree=5.0):
    """Rend la vitesse finale (1, 2) et la longueur du chemin parcouru, en m."""
    positions, vitesses = parcourir(v0, u, relaxation, acceleration_max, dt, duree)
    distance = float(np.sum(np.linalg.norm(np.diff(positions, axis=0), axis=1)))
    return vitesses[-1:], distance


def distance_arret(v0, relaxation, acceleration_max):
    """Distance d'arret exacte du modele continu, adherence saturee au depart.

    Tant que |v| / tau > a_max, l'agent freine a a_max constant ; il lui reste
    alors une vitesse a_max * tau, qu'il perd par relaxation exponentielle sur
    une distance a_max * tau^2. Les deux phases donnent

        d = v0^2 / (2 a_max) + a_max tau^2 / 2.

    Le second terme est l'ecart de 0,4 % que laissait l'approximation v0^2 / (2 a_max).
    """
    return v0**2 / (2 * acceleration_max) + acceleration_max * relaxation**2 / 2


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
        il glisse plus loin, sur la distance donnee par `distance_arret`.
        """
        v0 = 1.5
        _, distance_sec = marcher((v0, 0.0), (0.0, 0.0), relaxation=0.1, acceleration_max=5.9)
        v_fin, distance_mouille = marcher(
            (v0, 0.0), (0.0, 0.0), relaxation=0.1, acceleration_max=1.0
        )

        assert distance_mouille > 3 * distance_sec
        # Ecart mesure : 7e-4 en relatif a dt = 1e-3 s, erreur d'ordre 1 du schema.
        assert distance_mouille == pytest.approx(distance_arret(v0, 0.1, 1.0), rel=2e-3)
        assert np.linalg.norm(v_fin) < 1e-6  # il finit bien par s'arreter

    def test_distance_d_arret_converge_a_l_ordre_1_en_dt(self):
        """Sensibilite a dt (spec § 5, critere 4) : diviser dt par 2 divise l'erreur par 2.

        Le schema semi-implicite est d'ordre 1 : l'erreur sur la distance d'arret
        doit etre proportionnelle a dt. Mesure : rapport 2,000 entre deux pas
        successifs, erreur de 8e-4 m a dt = 1e-3 s. Une borne d'acceleration mal
        appliquee (selon dt, ou en retard d'un pas) casserait cette proportionnalite.
        """
        v0, tau, a_max = 1.5, 0.1, 1.0
        erreurs = []
        for dt in (4e-3, 2e-3, 1e-3):
            positions, _ = parcourir((v0, 0.0), (0.0, 0.0), tau, a_max, dt=dt)
            erreurs.append(abs(positions[-1, 0] - distance_arret(v0, tau, a_max)))

        rapports = np.array(erreurs[:-1]) / np.array(erreurs[1:])
        np.testing.assert_allclose(rapports, 2.0, rtol=0.05)
        assert erreurs[-1] < 1e-3  # m


def virage_a_angle_droit(acceleration_max, relaxation=0.1, v0=1.5, dt=2e-4):
    """Agent lance a v0 selon x, qui veut repartir a v0 selon y. Rend (positions, vitesses)."""
    return parcourir((v0, 0.0), (0.0, v0), relaxation, acceleration_max, dt=dt, duree=3.0)


class TestVirage:
    """L'autre moitie de l'inertie : sur sol glissant, on ne peut pas non plus tourner vite.

    Pour un virage a angle droit, le modele a une solution exacte. Tant que
    l'adherence est saturee, l'agent accelere a a_max dans la direction de
    U - v. Or cet ecart diminue alors dans sa propre direction : celle-ci ne
    change pas, et l'acceleration est un vecteur CONSTANT, de direction (-1, 1).
    La trajectoire est une parabole, comme celle d'un projectile.
    """

    @pytest.mark.parametrize("a_max", [5.9, 1.0])
    def test_depassement_selon_la_direction_initiale(self, a_max):
        """L'agent continue sur sa lancee avant de tourner, d'une distance exacte.

        La vitesse selon x vaut |U - v| / sqrt(2), qui decroit lineairement puis
        exponentiellement, comme dans `distance_arret` avec un ecart initial
        sqrt(2) v0. D'ou un depassement

            dx = (v0^2 / a_max + a_max tau^2 / 2) / sqrt(2).

        Ecart mesure a dt = 2e-4 s : 7e-4 en relatif sur sol sec, 1e-4 sur sol mouille.
        """
        v0, tau = 1.5, 0.1
        positions, _ = virage_a_angle_droit(a_max, tau, v0)

        attendu = (v0**2 / a_max + a_max * tau**2 / 2) / np.sqrt(2)
        assert positions[:, 0].max() == pytest.approx(attendu, rel=2e-3)

    @pytest.mark.parametrize("a_max", [5.9, 1.0])
    def test_rayon_de_courbure_jamais_inferieur_a_v2_sur_a_max(self, a_max):
        """Le rayon de virage est borne par l'adherence : R >= |v|^2 / a_max.

        C'est la relation du virage d'un vehicule : tourner sur un cercle de
        rayon R a la vitesse v demande une acceleration laterale v^2 / R, que le
        sol doit fournir. Elle ne peut donc pas depasser a_max.

        Le rayon de courbure discret vaut |v|^3 / |v x a|, avec a = (v_{n+1} - v_n) / dt.
        La borne doit tenir a chaque pas, et etre ATTEINTE au sommet de la
        parabole, ou l'acceleration est perpendiculaire a la vitesse. Mesure :
        minimum de R / (|v|^2 / a_max) egal a 1,000000.
        """
        dt = 2e-4
        _, vitesses = virage_a_angle_droit(a_max, dt=dt)
        v = vitesses[:-1]
        a = np.diff(vitesses, axis=0) / dt

        norme = np.linalg.norm(v, axis=1)
        lateral = np.abs(v[:, 0] * a[:, 1] - v[:, 1] * a[:, 0])  # |v x a| = |v| a_laterale
        en_virage = lateral > 1e-9  # en ligne droite, le rayon est infini
        rapport = (norme**3 / lateral)[en_virage] / (norme[en_virage] ** 2 / a_max)

        assert np.all(rapport >= 1.0 - 1e-9)
        assert rapport.min() == pytest.approx(1.0, abs=1e-3)

    def test_virage_plus_large_sur_sol_glissant(self):
        """Meme agent, meme envie de tourner : sur sol glissant, il deborde bien plus loin."""
        positions_sec, _ = virage_a_angle_droit(acceleration_max=5.9)
        positions_mouille, _ = virage_a_angle_droit(acceleration_max=1.0)

        assert positions_mouille[:, 0].max() > 3 * positions_sec[:, 0].max()
