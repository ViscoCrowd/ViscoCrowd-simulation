"""Tests de l'assemblage guidage + carte des milieux -> vitesse libre (G3, issue #26).

Le guidage (G1/G2) et la carte des milieux (C6) n'existent pas encore : on les
remplace par des pieces factices, ce qui suffit puisque l'assemblage ne fait que
les combiner. Les valeurs de tau, a_max et s sont ILLUSTRATIVES.
"""

import numpy as np
import pytest

from viscocrowd.core.integrator import pas_semi_implicite, trajectoire
from viscocrowd.core.state import State
from viscocrowd.geometry.boite import BoiteTournante
from viscocrowd.model.milieu import Milieu, ParametresMilieu, pas_libre_milieux, vitesse_libre

SEC = ParametresMilieu(relaxation=0.1, acceleration_max=5.9, vitesse=1.5)
MOUILLE = ParametresMilieu(relaxation=0.1, acceleration_max=1.0, vitesse=1.5)
EAU = ParametresMilieu(relaxation=0.05, acceleration_max=2.0, vitesse=0.5)
TOUS = {Milieu.EAU: EAU, Milieu.MOUILLE: MOUILLE, Milieu.SEC: SEC}


def partout(milieu):
    """Carte factice : le meme milieu sous tous les agents."""
    return lambda x: np.full(x.shape[0], milieu, dtype=np.int64)


def frontiere_en_x0(gauche=Milieu.SEC, droite=Milieu.MOUILLE):
    """Carte factice : un milieu pour x < 0, un autre au-dela."""
    return lambda x: np.where(x[:, 0] < 0.0, gauche, droite).astype(np.int64)


def vers(dx, dy):
    """Guidage factice : la meme direction unitaire pour tous les agents."""
    e = np.array([dx, dy], dtype=float) / np.hypot(dx, dy)
    return lambda etat: np.tile(e, (etat.n, 1))


def a_l_arret(etat):
    """Guidage factice : plus aucune direction, l'agent veut s'arreter."""
    return np.zeros((etat.n, 2))


def etat(positions, vitesses, rayon=0.2):
    x = np.array(positions, dtype=float)
    return State(x=x, v=np.array(vitesses, dtype=float), r=np.full(x.shape[0], rayon))


class TestAssemblage:
    def test_milieu_uniforme_redonne_exactement_vitesse_libre(self):
        """L'assemblage n'ajoute rien : il ne fait qu'aller chercher U, tau et a_max."""
        e = etat([[0.0, 0.0], [1.0, 2.0]], [[0.3, 0.0], [-1.0, 0.4]])
        libre = pas_libre_milieux(vers(3, 4), partout(Milieu.SEC), TOUS)

        u = SEC.vitesse * np.tile([0.6, 0.8], (2, 1))
        attendu = vitesse_libre(e.v, u, SEC.relaxation, SEC.acceleration_max, 1e-3)
        np.testing.assert_array_equal(libre(e, 1e-3), attendu)

    def test_chaque_agent_recoit_les_parametres_de_son_milieu(self):
        """Trois agents, trois sols : chacun est traite comme s'il etait seul sur le sien."""
        e = etat([[-1.0, 0.0], [1.0, 0.0], [2.0, 0.0]], [[0.0, 0.0]] * 3)
        carte = lambda x: np.array([Milieu.SEC, Milieu.MOUILLE, Milieu.EAU])  # noqa: E731
        libre = pas_libre_milieux(vers(1, 0), carte, TOUS)

        obtenu = libre(e, 1e-2)
        for k, p in enumerate((SEC, MOUILLE, EAU)):
            seul = vitesse_libre(
                e.v[k : k + 1], [[p.vitesse, 0.0]], p.relaxation, p.acceleration_max, 1e-2
            )
            np.testing.assert_array_equal(obtenu[k : k + 1], seul)

    def test_facteur_vitesse_multiplie_la_vitesse_souhaitee(self):
        """Niveau de panique (spec § 2.3) : U = facteur * s * e. Sans borne active, a double."""
        lent = ParametresMilieu(relaxation=1.0, acceleration_max=100.0, vitesse=1.0)
        e = etat([[0.0, 0.0]], [[0.0, 0.0]])
        normal = pas_libre_milieux(vers(1, 0), partout(Milieu.SEC), {Milieu.SEC: lent})
        panique = pas_libre_milieux(
            vers(1, 0), partout(Milieu.SEC), {Milieu.SEC: lent}, facteur_vitesse=2.0
        )

        np.testing.assert_allclose(panique(e, 1e-2), 2.0 * normal(e, 1e-2))

    def test_frontiere_identique_des_deux_cotes_ne_change_rien(self):
        """Deux zones aux parametres egaux : trajectoire identique au bit pres.

        Garde-fou du changement de milieu : l'erreur mesuree a la frontiere
        (`TestFrontiere`) doit venir du CONTRASTE d'adherence, pas de l'assemblage.
        """
        depart = etat([[-0.1, 0.0]], [[1.5, 0.0]])
        deux_zones = {Milieu.SEC: MOUILLE, Milieu.MOUILLE: MOUILLE}
        _, x_zones, _ = trajectoire(
            depart, 1e-3, 2.0, pas_libre_milieux(a_l_arret, frontiere_en_x0(), deux_zones)
        )
        _, x_uniforme, _ = trajectoire(
            depart, 1e-3, 2.0, pas_libre_milieux(a_l_arret, partout(Milieu.MOUILLE), TOUS)
        )

        np.testing.assert_array_equal(x_zones, x_uniforme)


def point_d_arret(dt, x0=-0.1, v0=1.5):
    """Agent qui freine en ligne droite a travers la frontiere sec | mouille en x = 0."""
    libre = pas_libre_milieux(a_l_arret, frontiere_en_x0(), TOUS)
    _, x, _ = trajectoire(etat([[x0, 0.0]], [[v0, 0.0]]), dt, 4.0, libre)
    return float(x[-1, 0, 0])


class TestFrontiere:
    """Freinage a travers une frontiere : le sol change sous les pieds de l'agent.

    Parti de x0 = -0,1 m a 1,5 m/s, l'agent freine a a_sec jusqu'a la frontiere,
    qu'il franchit a v1^2 = v0^2 - 2 a_sec |x0|, puis a a_mouille au-dela. Il
    s'arrete en

        x_arret = v1^2 / (2 a_mouille) + a_mouille tau^2 / 2 = 0,540 m

    (meme decomposition que `distance_arret` dans test_milieu.py). Tout sec, il
    s'arreterait en 0,12 m ; tout mouille, en 1,03 m.
    """

    X_ARRET = (1.5**2 - 2 * 5.9 * 0.1) / (2 * 1.0) + 1.0 * 0.1**2 / 2

    def test_l_agent_freine_selon_le_sol_sous_ses_pieds(self):
        x = point_d_arret(dt=1e-3)

        assert x == pytest.approx(self.X_ARRET, abs=1e-2)
        assert 0.12 + 0.1 < x < 1.03 - 0.1  # nettement distinct des deux sols uniformes

    @pytest.mark.parametrize("dt", [2e-3, 1e-3, 5e-4])
    def test_erreur_d_ordre_1_amplifiee_par_le_contraste(self, dt):
        """L'erreur reste proportionnelle a dt, avec une constante bornee.

        Le milieu est lu au DEBUT du pas : le pas qui chevauche la frontiere
        freine encore avec l'adherence du sec. Cet ecart de vitesse se paie
        ensuite sur le mouille, ou il est amplifie par a_sec / a_mouille. Mesure
        en balayant la position de la frontiere dans le pas : erreur entre 2,0 dt
        et 6,9 dt, quel que soit dt, contre 0,8 dt sur un sol uniforme. Un
        changement de milieu evalue en retard de plusieurs pas, ou jamais, sortirait
        de cette borne.
        """
        erreur = abs(point_d_arret(dt) - self.X_ARRET)
        assert erreur < 8.0 * dt


class TestAvecProjection:
    def test_agent_lance_contre_une_paroi_reste_confine(self):
        """Branche tel quel dans pas_semi_implicite : la projection garde le dernier mot.

        Sur sol mouille, l'agent fonce vers la paroi x = R - r et ne peut pas
        freiner a temps. La projection le retient a la paroi, et la vitesse relue
        v = dx / dt n'a plus de composante qui la traverse : le choc est mou,
        meme quand l'agent continue de pousser.
        """
        boite = BoiteTournante(demi_largeur=1.0)
        libre = pas_libre_milieux(vers(1, 0), partout(Milieu.MOUILLE), TOUS)
        e = etat([[0.5, 0.0]], [[1.5, 0.0]])

        for _ in range(1000):
            e = pas_semi_implicite(e, 1e-3, libre, boite.projeter)
            assert boite.violation(e.x, e.r, e.t) <= 1e-14

        assert e.x[0, 0] == pytest.approx(1.0 - 0.2, abs=1e-14)
        assert abs(e.v[0, 0]) < 1e-10  # plus de vitesse normale : il est plaque, immobile


class TestEntreesInvalides:
    @pytest.mark.parametrize(
        ("kwargs", "message"),
        [
            ({"relaxation": 0.0}, "relaxation"),
            ({"relaxation": np.nan}, "relaxation"),
            ({"acceleration_max": -1.0}, "acceleration_max"),
            ({"acceleration_max": np.inf}, "acceleration_max"),
            ({"vitesse": -0.1}, "vitesse"),
            ({"vitesse": np.nan}, "vitesse"),
        ],
    )
    def test_parametres_de_milieu_invalides(self, kwargs, message):
        valeurs = {"relaxation": 0.1, "acceleration_max": 1.0, "vitesse": 1.0, **kwargs}
        with pytest.raises(ValueError, match=message):
            ParametresMilieu(**valeurs)

    def test_vitesse_nulle_admise(self):
        assert ParametresMilieu(relaxation=0.1, acceleration_max=1.0, vitesse=0.0).vitesse == 0.0

    def test_aucun_milieu_declare(self):
        with pytest.raises(ValueError, match="au moins un milieu"):
            pas_libre_milieux(vers(1, 0), partout(Milieu.SEC), {})

    @pytest.mark.parametrize("facteur", [-1.0, np.nan])
    def test_facteur_vitesse_invalide(self, facteur):
        with pytest.raises(ValueError, match="facteur_vitesse"):
            pas_libre_milieux(vers(1, 0), partout(Milieu.SEC), TOUS, facteur_vitesse=facteur)

    def test_agent_sur_un_milieu_sans_parametres(self):
        """Etalonnage E0 : seul le sec est declare. Un agent sur l'eau est une erreur de carte."""
        libre = pas_libre_milieux(
            vers(1, 0), frontiere_en_x0(Milieu.SEC, Milieu.EAU), {Milieu.SEC: SEC}
        )
        e = etat([[-1.0, 0.0], [1.0, 0.0]], [[0.0, 0.0]] * 2)

        with pytest.raises(ValueError, match=r"agents \[1\]"):
            libre(e, 1e-3)

    @pytest.mark.parametrize(
        "sortie",
        [
            np.array([0, 7]),  # pas un milieu
            np.array([-1, 0]),
            np.array([0.0, 2.0]),  # flottants, meme « entiers »
            np.array([0]),  # mauvaise forme
        ],
    )
    def test_carte_mal_formee(self, sortie):
        libre = pas_libre_milieux(vers(1, 0), lambda x: sortie, TOUS)
        with pytest.raises(ValueError, match=r"zone|milieu"):
            libre(etat([[0.0, 0.0], [1.0, 0.0]], [[0.0, 0.0]] * 2), 1e-3)

    @pytest.mark.parametrize("norme", [0.5, 1e-12, 2.0])
    def test_direction_non_normalisee_refusee(self, norme):
        """Un gradient non normalise multiplierait la vitesse souhaitee sans rien signaler."""
        libre = pas_libre_milieux(lambda etat: np.array([[norme, 0.0]]), partout(Milieu.SEC), TOUS)
        with pytest.raises(ValueError, match="unitaire"):
            libre(etat([[0.0, 0.0]], [[0.0, 0.0]]), 1e-3)

    def test_direction_unitaire_a_l_arrondi_pres_admise(self):
        libre = pas_libre_milieux(
            lambda etat: np.array([[1.0 - 5e-10, 0.0]]), partout(Milieu.SEC), TOUS
        )
        assert libre(etat([[0.0, 0.0]], [[0.0, 0.0]]), 1e-3)[0, 0] > 0.0

    @pytest.mark.parametrize(
        "direction", [np.array([[np.nan, 0.0]]), np.array([1.0, 0.0])], ids=["NaN", "forme"]
    )
    def test_direction_mal_formee(self, direction):
        libre = pas_libre_milieux(lambda etat: direction, partout(Milieu.SEC), TOUS)
        with pytest.raises(ValueError, match="direction"):
            libre(etat([[0.0, 0.0]], [[0.0, 0.0]]), 1e-3)
