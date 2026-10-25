"""Relation vitesse-espacement : meneur, jeu, facteur, et branchement sur le pas libre."""

import numpy as np
import pytest

from viscocrowd.core.state import State
from viscocrowd.model.espacement import facteur_espacement, jeu_au_meneur
from viscocrowd.model.milieu import Milieu, ParametresMilieu, pas_libre_milieux

R = np.array([0.2, 0.2])
VERS_X = np.array([[1.0, 0.0], [1.0, 0.0]])
PORTEE = 10.0  # m : tous les meneurs comptent dans ces petits cas


def vers_la_sortie(x):
    """Temps restant d'une sortie lointaine en +x, a 1 m/s : le plus a droite est le plus avance."""
    return 100.0 - np.asarray(x)[:, 0]


class TestMeneur:
    def test_agent_seul_sans_meneur(self):
        x = np.zeros((1, 2))
        assert jeu_au_meneur(x, [0.2], [[1.0, 0.0]], [5.0], PORTEE) == [np.inf]

    def test_file_le_suiveur_voit_le_jeu_le_meneur_rien(self):
        x = np.array([[0.0, 0.0], [1.0, 0.0]])
        np.testing.assert_allclose(
            jeu_au_meneur(x, R, VERS_X, vers_la_sortie(x), PORTEE), [0.6, np.inf]
        )

    def test_couloir_de_demi_largeur_r_i_plus_r_j(self):
        """Decale lateralement de r_i + r_j ou plus : pas sur la trajectoire (Tordeux, l)."""
        x = np.array([[0.0, 0.0], [1.0, 0.4]])
        np.testing.assert_array_equal(
            jeu_au_meneur(x, R, VERS_X, vers_la_sortie(x), PORTEE), [np.inf, np.inf]
        )
        x = np.array([[0.0, 0.0], [1.0, -0.39]])  # de part et d'autre de l'axe : 2 (r_i + r_j)
        assert np.isfinite(jeu_au_meneur(x, R, VERS_X, vers_la_sortie(x), PORTEE)[0])

    def test_agent_derriere_ignore(self):
        x = np.array([[0.0, 0.0], [-1.0, 0.0]])
        e = np.array([[1.0, 0.0], [-1.0, 0.0]])  # dos a dos
        np.testing.assert_array_equal(jeu_au_meneur(x, R, e, [1.0, 1.0], PORTEE), [np.inf, np.inf])

    def test_deux_agents_qui_convergent_un_seul_attend(self):
        """Chacun est devant l'autre : seul le moins avance ralentit, le plus avance passe."""
        x = np.array([[0.0, 0.0], [1.0, 0.0]])
        e = np.array([[1.0, 0.0], [-1.0, 0.0]])
        np.testing.assert_allclose(jeu_au_meneur(x, R, e, [3.0, 2.0], PORTEE), [0.6, np.inf])

    def test_aucun_cycle_meme_a_trois(self):
        """A devant B devant C devant A : un ordre strict casse le cycle, A n'attend pas."""
        angles = np.deg2rad([90.0, 210.0, 330.0])
        x = 0.5 * np.column_stack((np.cos(angles), np.sin(angles)))
        e = np.roll(x, -1, axis=0) - x  # chacun vise le suivant
        e /= np.linalg.norm(e, axis=1)[:, None]
        r = np.full(3, 0.2)
        sans_ordre = jeu_au_meneur(x, r, e, np.zeros(3), PORTEE)
        assert np.all(np.isinf(sans_ordre))  # avances egales : personne ne suit personne
        jeu = jeu_au_meneur(x, r, e, [1.0, 2.0, 3.0], PORTEE)
        assert np.isinf(jeu[0])  # le plus avance n'a jamais de meneur
        assert np.sum(np.isfinite(jeu)) <= 2

    def test_le_plus_proche_des_meneurs(self):
        x = np.array([[0.0, 0.0], [2.0, 0.0], [1.0, 0.1]])
        e = np.tile([1.0, 0.0], (3, 1))
        jeu = jeu_au_meneur(x, np.full(3, 0.2), e, vers_la_sortie(x), PORTEE)
        assert jeu[0] == pytest.approx(np.hypot(1.0, 0.1) - 0.4)

    def test_portee_limite_la_recherche(self):
        x = np.array([[0.0, 0.0], [1.0, 0.0]])
        a = vers_la_sortie(x)
        assert np.isinf(jeu_au_meneur(x, R, VERS_X, a, 0.5)[0])  # jeu 0,6 m > 0,5 m
        assert jeu_au_meneur(x, R, VERS_X, a, 0.7)[0] == pytest.approx(0.6)

    def test_meme_resultat_que_la_recherche_exhaustive(self):
        """La recherche par paires proches rend les memes jeux que toutes les paires."""
        rng = np.random.default_rng(1)
        x = rng.uniform(0.0, 6.0, size=(120, 2))
        r = rng.uniform(0.15, 0.25, size=120)
        e = rng.normal(size=(120, 2))
        e /= np.linalg.norm(e, axis=1)[:, None]
        avance = rng.uniform(0.0, 10.0, size=120)
        portee = 0.6
        d = x[None, :, :] - x[:, None, :]
        devant = np.einsum("ijk,ik->ij", d, e)
        lateral = np.abs(d[..., 1] * e[:, None, 0] - d[..., 0] * e[:, None, 1])
        contact = r[:, None] + r[None, :]
        suit = (devant > 0) & (lateral < contact) & (avance[None, :] < avance[:, None])
        jeux = np.where(suit, np.hypot(d[..., 0], d[..., 1]) - contact, np.inf)
        attendu = np.where(jeux.min(axis=1) < portee, jeux.min(axis=1), np.inf)
        np.testing.assert_allclose(jeu_au_meneur(x, r, e, avance, portee), attendu)

    def test_direction_nulle_sans_meneur(self):
        x = np.array([[0.0, 0.0], [1.0, 0.0]])
        e = np.array([[0.0, 0.0], [1.0, 0.0]])
        assert jeu_au_meneur(x, R, e, vers_la_sortie(x), PORTEE)[0] == np.inf


class TestFacteur:
    @pytest.mark.parametrize(("ecart", "attendu"), [(1.0, 1.0), (0.4 + 0.3, 0.75), (0.4, 0.0)])
    def test_vitesse_optimale_de_tordeux(self, ecart, attendu):
        """V(s) = min(v0, max(0, s/T)) : v0 = 1 m/s, T = 0,4 s."""
        x = np.array([[0.0, 0.0], [ecart, 0.0]])
        f = facteur_espacement(x, R, VERS_X, vers_la_sortie(x), np.array([1.0, 1.0]), 0.4)
        np.testing.assert_allclose(f, [attendu, 1.0])

    def test_recouvrement_donne_un_arret_pas_un_recul(self):
        x = np.array([[0.0, 0.0], [0.399, 0.0]])
        assert facteur_espacement(x, R, VERS_X, vers_la_sortie(x), np.ones(2), 0.3)[0] == 0.0

    def test_agent_a_l_arret_sans_division_par_zero(self):
        x = np.array([[0.0, 0.0], [0.5, 0.0]])
        f = facteur_espacement(x, R, VERS_X, vers_la_sortie(x), np.zeros(2), 0.3)
        np.testing.assert_array_equal(f, 1.0)

    @pytest.mark.parametrize("temps", [0.0, -0.3, np.nan, np.inf])
    def test_temps_invalide_refuse(self, temps):
        with pytest.raises(ValueError, match="temps"):
            facteur_espacement(np.zeros((2, 2)), R, VERS_X, [1.0, 2.0], np.ones(2), temps)

    def test_formes_et_valeurs_invalides_refusees(self):
        with pytest.raises(ValueError, match="formes"):
            jeu_au_meneur(np.zeros((2, 2)), np.array([0.2]), VERS_X, [1.0, 2.0], PORTEE)
        with pytest.raises(ValueError):
            jeu_au_meneur(np.array([[np.nan, 0.0], [1.0, 0.0]]), R, VERS_X, [1.0, 2.0], PORTEE)
        with pytest.raises(ValueError, match="NaN"):
            jeu_au_meneur(np.zeros((2, 2)), R, VERS_X, [np.nan, 2.0], PORTEE)
        with pytest.raises(ValueError, match="positive"):
            facteur_espacement(np.zeros((2, 2)), R, VERS_X, [1.0, 2.0], [1.0, -1.0], 0.3)


SEC = {Milieu.SEC: ParametresMilieu(relaxation=0.5, acceleration_max=100.0, vitesse=1.0)}


def _libre(temps_espacement, avancement=vers_la_sortie):
    return pas_libre_milieux(
        lambda etat: np.tile([1.0, 0.0], (etat.n, 1)),
        lambda x: np.full(x.shape[0], Milieu.SEC, dtype=np.int64),
        SEC,
        temps_espacement=temps_espacement,
        avancement=avancement,
    )


def test_pas_libre_le_suiveur_vise_jeu_sur_t():
    etat = State(x=np.array([[0.0, 0.0], [0.7, 0.0]]), v=np.zeros((2, 2)), r=R, t=0.0)
    v = _libre(0.6)(etat, 0.01)
    # Vitesse visee : 0,5 m/s pour le suiveur (jeu 0,3 m), 1 m/s pour le meneur ; v + dt U/tau.
    np.testing.assert_allclose(v[:, 0], [0.01 * 0.5 / 0.5, 0.01 * 1.0 / 0.5])
    np.testing.assert_array_equal(v[:, 1], 0.0)


def test_pas_libre_sans_espacement_inchange():
    etat = State(x=np.array([[0.0, 0.0], [0.7, 0.0]]), v=np.zeros((2, 2)), r=R, t=0.0)
    np.testing.assert_array_equal(_libre(None, None)(etat, 0.01)[:, 0], 0.02)


@pytest.mark.parametrize("temps", [0.0, -1.0, np.nan])
def test_pas_libre_refuse_un_temps_invalide(temps):
    with pytest.raises(ValueError, match="temps_espacement"):
        _libre(temps)


def test_pas_libre_exige_l_avancement_avec_l_espacement():
    """Sans ordre d'avancement, des cycles d'attente redeviendraient possibles."""
    with pytest.raises(ValueError, match="avancement"):
        _libre(0.3, None)
