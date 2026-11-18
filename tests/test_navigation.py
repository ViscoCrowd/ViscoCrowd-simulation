"""Navigation locale par heuristiques visuelles (Moussaid et al. 2011, #158)."""

from pathlib import Path

import numpy as np
import pytest

from viscocrowd.core.state import State
from viscocrowd.geometry.obstacle import ObstacleRectangle
from viscocrowd.io.configuration import lire_configuration
from viscocrowd.model.milieu import Milieu, ParametresMilieu, pas_libre_milieux
from viscocrowd.model.navigation import (
    ParametresNavigation,
    ScenePlage,
    _collisions_pietons,
    _distance_rectangles,
    facteurs_individuels,
    vitesses_souhaitees,
)
from viscocrowd.scenarios.piscine import PLAGE, ParametresPiscine, simuler_piscine

EXEMPLE = Path(__file__).parents[1] / "experiments/piscine.yaml"
R = 0.2
# Une grande salle vide : seuls les obstacles places par chaque test comptent.
SALLE = ScenePlage(boite=(-100.0, 100.0, -100.0, 100.0), rectangles=())


def une_direction(angle):
    return np.array([[[np.cos(angle), np.sin(angle)]]])


class TestParametres:
    def test_valeurs_de_l_article_par_defaut(self):
        p = ParametresNavigation()
        assert (p.champ_vision, p.horizon, p.temps_anticipation) == (75.0, 10.0, None)
        assert p.dispersion_vitesse == pytest.approx(0.2 / 1.3, abs=0.01)

    @pytest.mark.parametrize(
        "champ",
        [
            {"champ_vision": 0.0},
            {"champ_vision": 200.0},
            {"horizon": -1.0},
            {"directions": 4},
            {"directions": 1},
            {"dispersion_vitesse": 0.6},
            {"dispersion_vitesse": -0.1},
            {"temps_anticipation": 0.0},
        ],
    )
    def test_valeurs_hors_domaine_refusees(self, champ):
        with pytest.raises(ValueError):
            ParametresNavigation(**champ)


class TestFacteursIndividuels:
    def test_loi_normale_tronquee_et_reproductible(self):
        p = ParametresNavigation(dispersion_vitesse=0.15)
        f = facteurs_individuels(20000, p, graine=3)
        assert f.mean() == pytest.approx(1.0, abs=0.005)
        assert f.std() == pytest.approx(0.15, rel=0.03)
        assert f.min() >= 1 - 3 * 0.15 and f.max() <= p.facteur_maximal
        np.testing.assert_array_equal(f, facteurs_individuels(20000, p, graine=3))

    def test_sans_dispersion_tous_identiques(self):
        f = facteurs_individuels(5, ParametresNavigation(dispersion_vitesse=0.0), graine=1)
        np.testing.assert_array_equal(f, np.ones(5))


class TestDistances:
    def test_mur_droit_devant(self):
        """Face a une face du rectangle, la distance est l'ecart moins le rayon."""
        rect = ObstacleRectangle(5.0, 6.0, -1.0, 1.0)
        d = _distance_rectangles(np.zeros((1, 2)), np.array([R]), une_direction(0.0), [rect])
        assert d[0, 0] == pytest.approx(5.0 - R)

    def test_coin_arrondi(self):
        """Vers un sommet, on touche le disque de rayon r centre sur le sommet."""
        rect = ObstacleRectangle(5.0, 6.0, 1.0, 2.0)
        x = np.array([[0.0, 1.0 - 0.1]])  # 0,1 m sous la face basse : le rayon frole le coin
        d = _distance_rectangles(x, np.array([R]), une_direction(0.0), [rect])
        attendu = 5.0 - np.sqrt(R**2 - 0.1**2)
        assert d[0, 0] == pytest.approx(attendu)

    def test_contre_un_coin_on_peut_s_eloigner(self):
        """Pose contre un coin arrondi (tolerance de projection), on n'est bloque que vers lui."""
        rect = ObstacleRectangle(0.0, 1.0, 0.0, 1.0)
        x = np.array([[1.0 + (R - 1e-6) / np.sqrt(2), 1.0 + (R - 1e-6) / np.sqrt(2)]])
        vers = _distance_rectangles(x, np.array([R]), une_direction(-3 * np.pi / 4), [rect])
        loin = _distance_rectangles(x, np.array([R]), une_direction(np.pi / 4), [rect])
        assert vers[0, 0] == 0.0
        assert np.isinf(loin[0, 0])

    def test_murs_circulaires(self):
        """Anneau 5-7 m : vers l'exterieur on touche le mur exterieur, vers le centre l'interieur."""
        anneau = ScenePlage(
            boite=(-100.0, 100.0, -100.0, 100.0),
            rectangles=(),
            disques=((0.0, 0.0, 5.0),),
            enceinte=(0.0, 0.0, 7.0),
        )
        x, v, v0, tau = np.array([[6.0, 0.0]]), np.zeros((1, 2)), np.array([2.0]), np.array([0.5])
        params = ParametresNavigation(champ_vision=1.0, directions=3)
        # Vers l'exterieur : jeu de 7 - 0,2 - 6 = 0,8 m (a 1 mm pres), v = jeu / tau, plafonne.
        u = vitesses_souhaitees(
            x, v, np.array([R]), v0, np.array([[1.0, 0.0]]), tau, anneau, params
        )
        assert np.hypot(*u[0]) == pytest.approx((0.8 + 1e-3) / 0.5, rel=1e-3)
        # Vers le centre : jeu de 6 - 5 - 0,2 = 0,8 m.
        u = vitesses_souhaitees(
            x, v, np.array([R]), v0, np.array([[-1.0, 0.0]]), tau, anneau, params
        )
        assert np.hypot(*u[0]) == pytest.approx((0.8 + 1e-3) / 0.5, rel=1e-3)
        # Le long du cercle, ni l'un ni l'autre n'est atteint avant longtemps : v0.
        u = vitesses_souhaitees(
            x, v, np.array([R]), np.array([0.3]), np.array([[0.0, 1.0]]), tau, anneau, params
        )
        assert np.hypot(*u[0]) == pytest.approx(0.3)

    def test_rectangle_derriere_ignore(self):
        rect = ObstacleRectangle(-6.0, -5.0, -1.0, 1.0)
        d = _distance_rectangles(np.zeros((1, 2)), np.array([R]), une_direction(0.0), [rect])
        assert np.isinf(d[0, 0])

    def test_collision_frontale_anticipee(self):
        """Deux agents face a face : i parcourt sa part du jeu avant le contact."""
        x = np.array([[0.0, 0.0], [4.0, 0.0]])
        v = np.array([[1.0, 0.0], [-1.0, 0.0]])
        v0 = np.array([1.0, 1.0])
        e = np.stack([une_direction(0.0)[0], une_direction(np.pi)[0]])
        d = _collisions_pietons(x, v, np.full(2, R), v0, e, 10.0, figes=False)
        # Jeu de 3,6 m parcouru a 2 m/s : contact a 1,8 s, soit 1,8 m pour chacun.
        np.testing.assert_allclose(d[:, 0], [1.8, 1.8])

    def test_meme_vitesse_derriere_pas_de_collision(self):
        """Suivre quelqu'un qui va aussi vite ne mene a aucune collision."""
        x = np.array([[0.0, 0.0], [2.0, 0.0]])
        v = np.array([[1.0, 0.0], [1.0, 0.0]])
        e = np.stack([une_direction(0.0)[0], une_direction(0.0)[0]])
        d = _collisions_pietons(x, v, np.full(2, R), np.ones(2), e, 10.0, figes=False)
        assert np.isinf(d[0, 0])


class TestHeuristiques:
    def test_seul_il_va_droit_au_but_a_sa_vitesse(self):
        u = vitesses_souhaitees(
            np.zeros((1, 2)),
            np.zeros((1, 2)),
            np.array([R]),
            np.array([1.3]),
            np.array([[1.0, 0.0]]),
            np.array([0.5]),
            SALLE,
            ParametresNavigation(),
        )
        np.testing.assert_allclose(u, [[1.3, 0.0]], atol=1e-12)

    def test_il_contourne_un_pieton_immobile(self):
        """Un pieton arrete droit devant : la direction choisie s'ecarte de l'axe."""
        x = np.array([[0.0, 0.0], [2.0, 0.0]])
        v = np.array([[1.3, 0.0], [0.0, 0.0]])
        u = vitesses_souhaitees(
            x,
            v,
            np.full(2, R),
            np.array([1.3, 0.0]),
            np.array([[1.0, 0.0], [1.0, 0.0]]),
            np.full(2, 0.5),
            SALLE,
            ParametresNavigation(),
        )
        assert abs(u[0, 1]) > 0.1  # il devie
        assert u[0, 0] > 0.0  # sans faire demi-tour

    def test_mur_proche_il_ralentit(self):
        """Seconde heuristique : un mur a 0,5 m (jeu de 0,3 m) limite la vitesse a jeu / tau."""
        mur = ScenePlage(
            boite=(-100.0, 100.0, -100.0, 100.0),
            rectangles=(ObstacleRectangle(0.5, 1.0, -50.0, 50.0),),
        )
        u = vitesses_souhaitees(
            np.zeros((1, 2)),
            np.zeros((1, 2)),
            np.array([R]),
            np.array([1.3]),
            np.array([[1.0, 0.0]]),
            np.array([0.5]),
            mur,
            ParametresNavigation(champ_vision=10.0, directions=3),
        )
        vitesse = np.hypot(*u[0])
        # Jeu vu a 1 mm pres (marge face aux parois, tolerance de projection) : 0,301 m.
        assert vitesse == pytest.approx((0.5 - R + 1e-3) / 0.5, abs=1e-9)

    @pytest.mark.parametrize(
        ("avance", "vitesse"),
        [
            (None, (0.5 - 2 * R) / 0.5),  # sans ordre, il s'arrete derriere l'autre
            ([2.0, 1.0], (0.5 - 2 * R) / 0.5),  # l'autre est plus avance : idem
            ([1.0, 2.0], 1.3),  # l'autre est moins avance : il ne l'attend pas
        ],
    )
    def test_on_n_attend_que_plus_avance_que_soi(self, avance, vitesse):
        """Seconde heuristique : seuls freinent les agents plus pres de la sortie.

        Devant un goulot etroit, deux agents cote a cote s'attendaient l'un l'autre, a
        l'arret, et la foule se figeait (E0, 17 novembre : N = 40, b = 0,8 m, 10 graines
        sur 10 bouchees). Champ de vision reduit : seule la ligne droite est examinee.
        """
        x = np.array([[0.0, 0.0], [0.5, 0.0]])
        u = vitesses_souhaitees(
            x,
            np.zeros((2, 2)),
            np.full(2, R),
            np.array([1.3, 0.0]),
            np.array([[1.0, 0.0], [1.0, 0.0]]),
            np.full(2, 0.5),
            SALLE,
            ParametresNavigation(champ_vision=1.0, directions=3),
            None if avance is None else np.array(avance),
        )
        # A 1 degre pres de l'axe, le jeu vu change de 2e-5 m.
        assert np.hypot(*u[0]) == pytest.approx(vitesse, abs=1e-3)

    def test_sans_destination_pas_de_vitesse(self):
        u = vitesses_souhaitees(
            np.zeros((1, 2)),
            np.zeros((1, 2)),
            np.array([R]),
            np.array([1.3]),
            np.zeros((1, 2)),
            np.array([0.5]),
            SALLE,
            ParametresNavigation(),
        )
        np.testing.assert_array_equal(u, [[0.0, 0.0]])


def parametres_piscine(**changements):
    config = lire_configuration(EXEMPLE)
    return ParametresPiscine(**(config["parametres"] | changements), graine=config["graine"])


def part_contre_le_bord(r):
    """Part des positions de plage, le long du bassin, a moins de 1 cm du plus pres possible."""
    b, rayon = r.parametres.piscine.bassin, r.parametres.rayon
    ecarts = []
    for x, e in zip(r.x, r.etats, strict=True):
        pl = x[(e == PLAGE) & (x[:, 0] > b.x_min) & (x[:, 0] < b.x_max)]
        ecarts += list(np.minimum(np.abs(pl[:, 1] - b.y_max), np.abs(pl[:, 1] - b.y_min)))
    return float(np.mean(np.array(ecarts) < rayon + 0.01))


@pytest.fixture(scope="module")
def deux_evacuations():
    """30 baigneurs, la meme graine, avec et sans navigation : environ 15 s de calcul."""
    sans = simuler_piscine(parametres_piscine(n_agents=30))
    avec = simuler_piscine(parametres_piscine(n_agents=30, navigation={}))
    return sans, avec


class TestScenario:
    @pytest.mark.invariant
    def test_tous_sortent_sans_violer_les_murs(self, deux_evacuations):
        _, avec = deux_evacuations
        assert np.all(np.isfinite(avec.sorties))
        assert avec.violation_paroi_max() <= avec.parametres.tolerance

    def test_la_file_contre_le_bord_disparait(self, deux_evacuations):
        """Sans navigation, la plupart des plagistes longent le bassin au plus pres (#158)."""
        sans, avec = deux_evacuations
        assert part_contre_le_bord(sans) > 0.8
        assert part_contre_le_bord(avec) < 0.3

    def test_meme_graine_meme_evacuation(self, deux_evacuations):
        _, avec = deux_evacuations
        encore = simuler_piscine(parametres_piscine(n_agents=30, navigation={}))
        np.testing.assert_array_equal(avec.x, encore.x)

    def test_parametres_serialises_et_relus(self):
        p = parametres_piscine(n_agents=5, navigation={"champ_vision": 45.0})
        d = p.en_dictionnaire()
        assert d["navigation"]["champ_vision"] == 45.0
        assert ParametresPiscine(**d).navigation == p.navigation

    def test_le_plus_rapide_borne_le_pas_de_temps(self):
        """Le facteur individuel maximal compte dans le deplacement par pas (rayon / 5)."""
        # A dt = 0,0185 s, le plus rapide sans dispersion (2,01 m/s) fait 0,037 m par pas,
        # sous r/5 = 0,04 m ; avec 3 x 0,15 de dispersion, 0,054 m : refuse.
        parametres_piscine(n_agents=5, dt=0.0185)
        with pytest.raises(ValueError, match="dt trop grand"):
            parametres_piscine(n_agents=5, dt=0.0185, navigation={})


SOL_SEC = ParametresMilieu(relaxation=0.5, acceleration_max=5.9, vitesse=1.34)


class TestCumulAvecEspacement:
    """Piscine : navigation et temps_espacement se cumulent, a dessein (revue de #163).

    Le goulot E0 et l'anneau refusent la combinaison. Dans la piscine, T reste actif dans
    l'eau, ou personne ne navigue ; sur la plage, la seconde heuristique repart de la
    vitesse NOMINALE et T y est sans effet. Ne pas aligner la piscine sur le goulot.
    """

    # Deux agents sur l'axe, 0,6 m d'ecart : jeu 0,2 m, T = 0,35 s freinerait le suiveur
    # a 0,57 m/s.
    ETAT = State(x=np.array([[0.0, 0.0], [0.6, 0.0]]), v=np.zeros((2, 2)), r=np.full(2, R))

    @staticmethod
    def vers_x(etat):
        return np.tile([1.0, 0.0], (etat.n, 1))

    @staticmethod
    def partout(points):
        return np.full(points.shape[0], Milieu.SEC, dtype=np.int64)

    def libre(self, temps_espacement, navigation):
        def naviguer(etat, e, nominale, tau, u):
            return vitesses_souhaitees(
                etat.x,
                etat.v,
                etat.r,
                nominale,
                e,
                tau,
                SALLE,
                ParametresNavigation(),
                -etat.x[:, 0],
            )

        return pas_libre_milieux(
            self.vers_x,
            self.partout,
            {Milieu.SEC: SOL_SEC},
            temps_espacement=temps_espacement,
            avancement=lambda x: -x[:, 0],
            vitesse_souhaitee=naviguer if navigation else None,
        )(self.ETAT, 0.01)

    def test_sur_la_plage_t_est_sans_effet(self):
        np.testing.assert_array_equal(self.libre(0.35, True), self.libre(None, True))

    def test_sans_navigation_t_freine_bien_le_suiveur(self):
        """Temoin : la situation est bien de celles ou T agit."""
        assert self.libre(0.35, False)[0, 0] < self.libre(None, False)[0, 0]

    def test_la_piscine_accepte_la_combinaison(self):
        p = parametres_piscine(n_agents=5, navigation={})
        assert p.temps_espacement == 0.35 and p.navigation is not None
