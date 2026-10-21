"""Tests unitaires de la projection sur l'exclusion entre agents."""

import numpy as np
import pytest

from viscocrowd.core.integrator import pas_semi_implicite
from viscocrowd.core.rng import generateur
from viscocrowd.core.state import State
from viscocrowd.geometry.boite import BoiteTournante
from viscocrowd.geometry.grille import paires_candidates, recouvrement_max
from viscocrowd.geometry.projection import (
    _RANG_EXTRAPOLATION,
    ProjectionExclusion,
    ProjectionNonConvergee,
)

TOLERANCE = 1e-6
PRECISION_PAROI = 1e-14

# Configurations a contacts multiples, petites et verifiables a la main, servant
# a la fois a la comparaison avec Gauss-Seidel et au controle du centre de gravite.
CAS_MULTICONTACT = {
    "3 alignes": (np.array([[-0.09, 0.0], [0.0, 0.0], [0.09, 0.0]]), 0.05),
    "triangle serre": (
        np.array([[-0.045, 0.0], [0.045, 0.0], [0.0, 0.09 * np.sqrt(3) / 2]]),
        0.05,
    ),
    "amas 12": (generateur(3).uniform(-0.2, 0.2, size=(12, 2)), 0.05),
}


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
        [
            ({"tolerance": 0.0}, "tolerance"),
            # `NaN <= 0` est faux : une tolerance NaN passait le controle, puis
            # `residu > NaN` etant faux lui aussi, tout appel se declarait converge.
            ({"tolerance": np.nan}, "tolerance"),
            ({"tolerance": np.inf}, "tolerance"),
            ({"iterations": 0}, "iteration"),
            # Un budget NaN passait `iterations < 1`, aucun balayage ne se faisait,
            # et la boucle de recherche des paires tournait sans fin des le premier
            # recouvrement.
            ({"iterations": np.nan}, "iteration"),
            ({"iterations": 2.5}, "iteration"),
        ],
    )
    def test_parametres_invalides(self, kwargs, message):
        with pytest.raises(ValueError, match=message):
            ProjectionExclusion(**kwargs)

    @pytest.mark.parametrize("demi_largeur", [0.0, -1.0, np.nan, np.inf])
    def test_boite_de_demi_largeur_invalide_rejetee(self, demi_largeur):
        """Une boite NaN rendait des positions NaN, refusees bien plus loin, sans cause."""
        with pytest.raises(ValueError, match="demi-largeur"):
            BoiteTournante(demi_largeur=demi_largeur)


def _gauss_seidel(x, r, tolerance=TOLERANCE, budget=20000):
    """Oracle de reference : corrections SEQUENTIELLES, une paire apres l'autre.

    C'est l'algorithme que la spec annoncait avant la PR #6. Il sert ici de point
    de comparaison, pas de code de production : la boucle Python paire par paire
    est precisement ce que la version Jacobi evite.
    """
    x = np.array(x, dtype=float, copy=True)
    balayages = 0
    for _ in range(budget):
        paires = paires_candidates(x, r)
        if paires.shape[0] == 0:
            break
        balayages += 1
        bouge = False
        for i, j in paires:
            ecart = x[j] - x[i]
            distance = float(np.linalg.norm(ecart))
            recouvrement = r[i] + r[j] - distance
            if recouvrement <= 0.0:
                continue
            direction = ecart / distance if distance > 1e-12 else np.array([1.0, 0.0])
            x[i] -= 0.5 * recouvrement * direction
            x[j] += 0.5 * recouvrement * direction
            bouge = True
        if not bouge or recouvrement_max(x, r) <= tolerance:
            break
    return x, balayages


class TestComparaisonGaussSeidel:
    """Jacobi accelere contre Gauss-Seidel : ce qui est garanti, ce qui ne l'est pas.

    Repond a la relecture de la PR #6. Le point a retenir pour le rapport : les
    deux methodes rendent une configuration ADMISSIBLE, aucune des deux ne rend
    la projection euclidienne de x_libre sur K.
    """

    @pytest.mark.parametrize("cas", list(CAS_MULTICONTACT))
    def test_les_deux_methodes_rendent_une_configuration_admissible(self, cas):
        """Le seul resultat commun aux deux : plus de recouvrement. C'est l'essentiel."""
        x, rayon = CAS_MULTICONTACT[cas]
        r = np.full(x.shape[0], rayon)

        y_jacobi = ProjectionExclusion(tolerance=TOLERANCE, iterations=500)(x, r, 0.0)
        y_gs, _ = _gauss_seidel(x, r)

        assert recouvrement_max(y_jacobi, r) <= TOLERANCE
        assert recouvrement_max(y_gs, r) <= TOLERANCE

    @pytest.mark.parametrize("cas", list(CAS_MULTICONTACT))
    def test_aucune_des_deux_n_est_la_projection_euclidienne(self, cas):
        """Ni l'une ni l'autre ne minimise |x - x_libre|.

        Les deux restent du meme ordre de grandeur : Jacobi ne part pas a l'autre
        bout de K. Mais les ecarts mesures (|dX| a 1,3 % pres sur l'amas de 12,
        et Jacobi 15 % MOINS loin sur le triangle serre) interdisent d'ecrire
        « projection de Gauss-Seidel » dans le rapport.
        """
        x, rayon = CAS_MULTICONTACT[cas]
        r = np.full(x.shape[0], rayon)

        y_jacobi = ProjectionExclusion(tolerance=TOLERANCE, iterations=500)(x, r, 0.0)
        y_gs, _ = _gauss_seidel(x, r)

        deplacement_jacobi = np.linalg.norm(y_jacobi - x)
        deplacement_gs = np.linalg.norm(y_gs - x)

        assert deplacement_jacobi == pytest.approx(deplacement_gs, rel=0.20), (
            f"{cas} : |dX| Jacobi {deplacement_jacobi:.4e} m "
            f"contre Gauss-Seidel {deplacement_gs:.4e} m"
        )

    def test_jacobi_ne_domine_pas_gauss_seidel_sur_le_deplacement(self):
        """Aucune des deux n'est systematiquement plus proche du pas libre.

        Si une methode venait a gagner sur TOUS les cas, il faudrait rouvrir la
        question : ce serait l'indice qu'elle approche le minimiseur.
        """
        gagnants = set()
        for x, rayon in CAS_MULTICONTACT.values():
            r = np.full(x.shape[0], rayon)
            y_jacobi = ProjectionExclusion(tolerance=TOLERANCE, iterations=500)(x, r, 0.0)
            y_gs, _ = _gauss_seidel(x, r)
            gagnants.add(
                "jacobi" if np.linalg.norm(y_jacobi - x) < np.linalg.norm(y_gs - x) else "gs"
            )

        assert gagnants == {"jacobi", "gs"}, (
            f"une methode domine l'autre sur tous les cas ({gagnants}) : "
            "a reexaminer, elle approche peut-etre le minimiseur"
        )


class TestChocMultiple:
    """Chocs a TROIS corps et plus, isoles : aucune dissipation d'ensemble ne masque rien.

    Repond a la relecture de la PR #6. Le choc a deux disques est exact par
    construction (une paire isolee est corrigee en un balayage) : il ne peut pas
    detecter le rebond que l'extrapolation introduit en contacts multiples. Ces
    tests mesurent l'energie cinetique residuelle RAPPORTEE a l'energie
    d'arrivee, ce que l'invariant global du tassement ne sait pas faire.
    """

    # Energie cinetique residuelle apres un choc, rapportee a l'energie d'arrivee.
    # Avec l'extrapolation active des le premier balayage, le pire cas mesure sur
    # des chaines de 3 a 32 disques valait 1,0e-3 (soit 3 % de la vitesse
    # d'arrivee restituee). En retardant l'extrapolation au rang 80 et en faisant
    # repartir sa rampe de zero, il tombe a 9,0e-7, soit 0,09 % en vitesse.
    RESTITUTION_MAX = 5e-6

    @staticmethod
    def _choquer(x0, v0, rayon=0.1, dt=1e-3, pas=2000, tolerance=TOLERANCE):
        """Lache des disques les uns contre les autres, sans force exterieure."""
        etat = State(
            x=np.array(x0, dtype=float),
            v=np.array(v0, dtype=float),
            r=np.full(len(x0), rayon),
        )
        projection = ProjectionExclusion(tolerance=tolerance)
        energie_initiale = 0.5 * float(np.sum(etat.v**2))

        for _ in range(pas):
            etat = pas_semi_implicite(etat, dt, lambda e, _dt: e.v, projection)

        return etat, energie_initiale, projection

    def test_trois_disques_alignes_s_arretent_tous_au_contact(self):
        """Les deux exterieurs convergent vers un disque central immobile.

        Le disque central est pousse des DEUX cotes dans le meme balayage : c'est
        la configuration que le choc a deux corps ne couvre pas.
        """
        etat, energie_initiale, projection = self._choquer(
            [[-0.5, 0.0], [0.0, 0.0], [0.5, 0.0]],
            [[1.0, 0.0], [0.0, 0.0], [-1.0, 0.0]],
        )

        energie = 0.5 * float(np.sum(etat.v**2))
        assert energie / energie_initiale < self.RESTITUTION_MAX, (
            f"rebond artificiel : {energie:.3e} J restants sur "
            f"{energie_initiale:.3f} J ({energie / energie_initiale:.2e})"
        )
        # Les trois restent alignes, en contact, et le central n'a pas bouge.
        assert np.max(np.abs(etat.x[:, 1])) < 1e-12
        np.testing.assert_allclose(etat.x[1], [0.0, 0.0], atol=1e-9)
        for a, b in ((0, 1), (1, 2)):
            distance = np.linalg.norm(etat.x[b] - etat.x[a])
            assert distance >= 0.2 - TOLERANCE  # jamais d'interpenetration
            assert distance == pytest.approx(0.2, abs=1e-3)  # en contact, pas separes
        assert projection.non_convergences == 0

    # Trois disques lances vers le centre : chacun touchera les deux autres.
    _ANGLES = np.array([90.0, 210.0, 330.0]) * np.pi / 180.0
    TRIANGLE = 0.5 * np.stack([np.cos(_ANGLES), np.sin(_ANGLES)], axis=1)
    VERS_LE_CENTRE = -TRIANGLE / 0.5  # 1 m/s

    @staticmethod
    def _cotes(x):
        return np.array([np.linalg.norm(x[b] - x[a]) for a, b in ((0, 1), (1, 2), (0, 2))])

    def test_triangle_qui_s_effondre_sur_son_centre(self):
        """Les trois finissent tangents deux a deux, a 1e-5 m pres (issue #10).

        Le jeu de 1,7e-3 m mesure a la tolerance 1e-6 m n'etait pas un defaut de
        position : c'est une VITESSE residuelle de l'ordre de tolerance / dt, que
        rien n'amortit dans ce choc sans frottement (voir le test suivant). A la
        tolerance 1e-8 m, le jeu tombe a 4,1e-6 m.
        """
        etat, energie_initiale, _ = self._choquer(
            self.TRIANGLE, self.VERS_LE_CENTRE, tolerance=1e-8
        )

        energie = 0.5 * float(np.sum(etat.v**2))
        assert energie / energie_initiale < self.RESTITUTION_MAX
        cotes = self._cotes(etat.x)
        assert np.all(cotes >= 0.2 - 1e-8)  # jamais d'interpenetration
        np.testing.assert_allclose(cotes, 0.2, atol=1e-5)

    def test_jeu_du_triangle_et_vitesse_residuelle_selon_la_tolerance(self):
        """Diagnostic de l'issue #10, chiffre.

        La projection s'arrete des que le recouvrement passe sous la tolerance. Le
        pas suivant, une infime poussee le fait repasser au-dessus, et un balayage
        le divise par quatre : les disques s'ecartent de quelques 1e-7 m de plus que
        necessaire, ce que la relecture v = dx/dt transforme en vitesse sortante.
        Mesures (v0 = 1 m/s, 2000 pas) : vitesse radiale residuelle 3,7e-4 m/s a
        dt = 1e-3 s, 7,1e-4 m/s a dt = 5e-4 s, soit 0,15 a 0,37 tolerance / dt ;
        le jeu croit ensuite LINEAIREMENT avec la duree. Au protocole de 2000 pas,
        les deux effets de dt se compensent : c'est la fausse « saturation ».
        """
        dt = 1e-3
        jeux, vitesses = [], []
        for tolerance in (1e-6, 1e-8):
            etat, _, _ = self._choquer(self.TRIANGLE, self.VERS_LE_CENTRE, tolerance=tolerance)
            jeux.append(self._cotes(etat.x).mean() - 0.2)
            radiale = np.sum(etat.v * etat.x, axis=1) / np.linalg.norm(etat.x, axis=1)
            vitesses.append(radiale)
            # Vitesse sortante, identique pour les trois, bornee par la tolerance.
            assert np.all(radiale > 0.0)
            assert np.all(radiale < 0.5 * tolerance / dt)
        assert jeux[0] / jeux[1] > 100  # mesure : 1,045e-3 / 4,1e-6 = 256

        # Le jeu croit lineairement apres le choc (contact vers t = 0,385 s).
        etat_court, _, _ = self._choquer(self.TRIANGLE, self.VERS_LE_CENTRE, pas=1000)
        jeu_court = self._cotes(etat_court.x).mean() - 0.2
        np.testing.assert_allclose(jeux[0] / (2.0 - 0.385), jeu_court / (1.0 - 0.385), rtol=0.02)

    def test_une_foule_qui_pousse_reste_au_contact(self):
        """Avec une vitesse desiree vers le centre, aucune vitesse parasite ne survit."""

        def vers_le_centre(etat, dt):
            u = -etat.x / np.linalg.norm(etat.x, axis=1, keepdims=True)
            return etat.v + dt * (u - etat.v) / 0.5  # relaxation, tau = 0,5 s

        etat = State(x=self.TRIANGLE, v=self.VERS_LE_CENTRE, r=np.full(3, 0.1))
        projection = ProjectionExclusion(tolerance=TOLERANCE)
        for _ in range(2000):
            etat = pas_semi_implicite(etat, 1e-3, vers_le_centre, projection)
        # Mesure : recouvrement residuel 8,1e-7 m, dans la tolerance : aucun jeu.
        np.testing.assert_allclose(self._cotes(etat.x), 0.2, atol=TOLERANCE)

    def test_chaine_de_sept_disques(self):
        """Le cas defavorable : la chaine depasse le rang d'extrapolation.

        Sept disques en file, de vitesses degradees, forment une chaine de
        contacts qui demande plus de 40 balayages : elle EST donc extrapolee.
        C'est la configuration ou l'artefact subsiste, et ce test en fixe la
        borne mesuree pour que personne ne la depasse sans s'en apercevoir.
        """
        x0 = [[-0.9 + 0.3 * k, 0.0] for k in range(7)]
        v0 = [[1.0 - k / 3.0, 0.0] for k in range(7)]

        etat, energie_initiale, projection = self._choquer(x0, v0)

        energie = 0.5 * float(np.sum(etat.v**2))
        assert energie / energie_initiale < self.RESTITUTION_MAX
        assert projection.iterations_max > _RANG_EXTRAPOLATION, (
            "ce cas doit declencher l'extrapolation, sinon il ne teste plus rien"
        )
        assert recouvrement_max(etat.x, etat.r) <= TOLERANCE

    def test_la_remontee_d_energie_par_pas_reste_negligeable(self):
        """Choc mou : aucun pas de temps ne doit creer d'energie de facon sensible.

        La correction de recouvrement est relue comme une vitesse v = dx/dt, ce
        qui laisse passer une remontee du niveau de la tolerance de projection.
        Mesure sur trois configurations a contacts multiples : au plus 6,0e-8 de
        l'energie d'arrivee en un pas. On borne a 1e-6, deux ordres de grandeur
        au-dessus du mesure, pour ne pas transformer ce test en detecteur de
        bruit d'arrondi.
        """
        etat = State(
            x=np.array([[-0.5, 0.0], [0.0, 0.0], [0.5, 0.0]]),
            v=np.array([[1.0, 0.0], [0.0, 0.0], [-1.0, 0.0]]),
            r=np.full(3, 0.1),
        )
        projection = ProjectionExclusion(tolerance=TOLERANCE)

        energies = [0.5 * float(np.sum(etat.v**2))]
        for _ in range(2000):
            etat = pas_semi_implicite(etat, 1e-3, lambda e, _dt: e.v, projection)
            energies.append(0.5 * float(np.sum(etat.v**2)))

        remontee = np.diff(np.array(energies)).max()
        assert remontee < 1e-6 * energies[0], (
            f"remontee de {remontee:.3e} J sur un pas, pour {energies[0]:.3f} J d'arrivee"
        )


class TestJeuDeContact:
    """Issue #10 : caracterisation locale du jeu, avant la validation de densite.

    Une foule de 60 agents (rayons 0,18 a 0,22 m) est poussee contre une paroi a
    1,5 m/s, puis s'arrete, avec les parametres du sec du banc de couloir. On
    mesure le jeu des paires proches et l'indicateur 2 x jeu moyen / diametre.
    Ce dernier n'est une variation de densite que sous une hypothese de
    dilatation isotrope homogene. Ce banc ne mesure aucune densite de reference
    et ne borne pas le biais au goulot ; les paires eloignees sont exclues.

    La decroissance en dt^2 annoncee initialement est REFUTEE, pas assouplie.
    La revue mesurait 7,576e-6 puis 4,272e-5 m a dt = 0,01 puis 0,005 s (macOS
    arm64), contre 8,2e-6 puis 2,2e-6 m sur x86-64, avec les memes versions.
    Une forte sensibilite est mesuree : deplacer UN agent de 1e-12 m au
    depart ecarte les trajectoires de plus de 1e-6 m des les premiers chocs, et
    de 9e-5 m a la fin (amplification 1e8) ; des arrondis differents entre
    processeurs sont une explication plausible, pas une cause isolee ici. Les paires
    proches reste stable (101 et 102), mais leur partage entre contacts effectifs
    (jeu de l'ordre de la tolerance) et quasi-contacts (1e-5 a 1e-3 m) change :
    jeu moyen 2,2e-6 m sans perturbation, 3,85e-5 m avec -1e-12 m. Le jeu moyen
    n'est donc pas une observable de convergence ; le biais de densite devra etre
    estime sur plusieurs graines avec la densite elle-meme (M1, issue #10).
    """

    @staticmethod
    def _foule_arretee(dt, perturbation=0.0):
        from viscocrowd.model.milieu import Milieu, ParametresMilieu, pas_libre_milieux

        n = 60
        rng = generateur(1)
        x = np.array([[-2.0 + 0.5 * (k % 8), -2.0 + 0.5 * (k // 8)] for k in range(n)])
        x += rng.uniform(-0.02, 0.02, size=x.shape)
        x[0, 0] += perturbation
        etat = State(x=x, v=np.zeros_like(x), r=rng.uniform(0.18, 0.22, size=n))
        sec = {Milieu.SEC: ParametresMilieu(relaxation=0.3, acceleration_max=3.0, vitesse=1.5)}

        def partout(points):
            return np.full(points.shape[0], Milieu.SEC, dtype=np.int64)

        pousse = pas_libre_milieux(lambda e: np.tile([1.0, 0.0], (e.n, 1)), partout, sec)
        arret = pas_libre_milieux(lambda e: np.zeros((e.n, 2)), partout, sec)
        projection = ProjectionExclusion(BoiteTournante(2.5).projeter, tolerance=TOLERANCE)
        for libre, duree in ((pousse, 8.0), (arret, 4.0)):
            for _ in range(round(duree / dt)):
                etat = pas_semi_implicite(etat, dt, libre, projection)
        assert projection.non_convergences == 0
        return etat

    @classmethod
    def _jeux_en_contact(cls, dt, perturbation=0.0):
        """Jeux (m) des paires a moins de 1 mm du contact, et diametre moyen (m)."""
        etat = cls._foule_arretee(dt, perturbation)
        paires = paires_candidates(etat.x, etat.r, 1e-3)
        i, j = paires[:, 0], paires[:, 1]
        jeux = np.linalg.norm(etat.x[j] - etat.x[i], axis=1) - etat.r[i] - etat.r[j]
        return jeux, 2 * etat.r.mean()

    def test_foule_comprimee_puis_arretee(self):
        jeux, diametre = self._jeux_en_contact(0.01)
        assert jeux.size > 80  # une vraie foule au contact : mesure 101 paires
        assert jeux.min() >= -TOLERANCE  # jamais d'interpenetration
        indicateur = 2 * jeux.mean() / diametre
        assert 0.0 <= indicateur < 1e-4  # mesure : 4,1e-5 ; pas une borne de densite
        assert jeux.max() < 5e-4  # mesure : 1,5e-4 m, soit 0,07 % du diametre

    @pytest.mark.slow
    def test_l_arrangement_final_est_sensible_aux_arrondis(self):
        """Pourquoi le jeu moyen differait entre deux machines (revue de la PR #48).

        Une perturbation de 1e-12 m, de l'ordre d'un arrondi, change l'arrangement
        final de bien plus que la tolerance, tout en gardant une population dense de paires proches.
        """
        reference = self._foule_arretee(0.005)
        perturbee = self._foule_arretee(0.005, perturbation=1e-12)
        ecart = np.max(np.abs(perturbee.x - reference.x))
        assert ecart > 1e-6  # mesure : 9,1e-5 m, soit une amplification de 9e7
        for etat in (reference, perturbee):
            assert recouvrement_max(etat.x, etat.r) <= TOLERANCE
            assert paires_candidates(etat.x, etat.r, 1e-3).shape[0] > 80  # mesure : 101 et 102


class TestCentreDeGravite:
    """L'etape de contact conserve le centre de gravite, exactement.

    La ponderation des corrections est symetrique en (i, j) : chaque paire recoit
    deux corrections opposees de meme norme. Moyenner par AGENT, comme la premiere
    version de la PR #6, le brisait des que deux voisins n'avaient pas le meme
    nombre de contacts — la foule entiere derivait alors de 2,2e-3 m sur un amas
    de 12 disques. Sans domaine, aucune force exterieure : la derive mesuree ici
    ne peut venir que de l'algorithme.
    """

    @pytest.mark.parametrize(("n", "rayon", "etendue"), [(12, 0.05, 0.2), (100, 0.04, 0.9)])
    def test_aucune_derive_sur_un_amas_recouvrant(self, n, rayon, etendue):
        x = generateur(n).uniform(-etendue, etendue, size=(n, 2))
        r = np.full(n, rayon)
        assert recouvrement_max(x, r) > 0.0  # le depart est bien fautif

        y = ProjectionExclusion(tolerance=TOLERANCE, iterations=500)(x, r, 0.0)

        derive = np.linalg.norm(y.mean(axis=0) - x.mean(axis=0))
        assert derive < 1e-14, f"le centre de gravite a derive de {derive:.3e} m"

    def test_contacts_asymetriques_sans_derive(self):
        """Le cas minimal qui piegeait la moyenne par agent.

        Le disque central a deux contacts, les deux autres un seul. Moyenner par
        agent divisait sa correction par 2 et celle des voisins par 1 : les
        reactions cessaient d'etre opposees.
        """
        r = np.full(3, 0.05)
        x = np.array([[-0.09, 0.0], [0.0, 0.0], [0.09, 0.0]])

        y = ProjectionExclusion(tolerance=TOLERANCE, iterations=500)(x, r, 0.0)

        np.testing.assert_allclose(y.mean(axis=0), x.mean(axis=0), atol=1e-15)


class TestModeStrict:
    """Une configuration non convergee ne doit pas pouvoir passer pour un resultat.

    Repond a la relecture de la PR #6 : `non_convergences` etait incremente mais
    les positions etaient rendues telles quelles, donc exploitables sans le
    savoir. Deux garde-fous, selon qu'on veuille interrompre le calcul ou le
    verifier apres coup.
    """

    @pytest.fixture
    def surcharge(self):
        """Plus de disques que la boite ne peut en contenir : la projection ECHOUE."""
        boite = BoiteTournante(demi_largeur=1.0)
        n = 100
        r = np.full(n, 0.17)  # ~ 91 % de la surface de la boite : impossible
        x = generateur(0).uniform(-0.8, 0.8, size=(n, 2))
        return boite, x, r

    def test_mode_strict_leve_des_le_premier_echec(self, surcharge):
        boite, x, r = surcharge
        proj = ProjectionExclusion(boite.projeter, tolerance=TOLERANCE, iterations=50, strict=True)

        with pytest.raises(ProjectionNonConvergee) as echec:
            proj(x, r, 0.0)

        assert echec.value.residu > TOLERANCE
        assert echec.value.tolerance == TOLERANCE
        assert echec.value.iterations == 50
        # Le compteur est renseigne meme quand on leve : la mesure reste disponible.
        assert proj.non_convergences == 1

    def test_verifier_convergence_apres_coup(self, surcharge):
        """Le mode permissif reste utilisable, mais la verification est explicite."""
        boite, x, r = surcharge
        proj = ProjectionExclusion(boite.projeter, tolerance=TOLERANCE, iterations=50)

        proj(x, r, 0.0)  # ne leve pas : on veut MESURER l'echec

        with pytest.raises(ProjectionNonConvergee, match="non convergee"):
            proj.verifier_convergence()

    def test_verifier_convergence_ne_leve_rien_quand_tout_va_bien(self):
        r = np.array([0.1, 0.1])
        proj = ProjectionExclusion(tolerance=TOLERANCE)

        proj(np.array([[0.0, 0.0], [0.15, 0.0]]), r, 0.0)

        proj.verifier_convergence()  # ne doit rien lever

    def test_le_mode_strict_ne_gene_pas_une_projection_qui_converge(self):
        r = np.array([0.1, 0.1])
        proj = ProjectionExclusion(tolerance=TOLERANCE, strict=True)

        y = proj(np.array([[0.0, 0.0], [0.15, 0.0]]), r, 0.0)

        np.testing.assert_allclose(y, [[-0.025, 0.0], [0.175, 0.0]], atol=1e-15)
        assert proj.non_convergences == 0


class TestEntreesNonFinies:
    """Une entree non finie est une erreur, jamais une projection « convergee » (issue #16).

    Avant correction, un NaN rendait toutes les distances incomparables : aucune paire
    detectee, residu nul, 0 non-convergence, et l'agent ressortait avec ses deux
    coordonnees a NaN. Une simulation corrompue affichait ainsi exactement les chiffres
    publies comme preuve de justesse.
    """

    @pytest.mark.parametrize("strict", [True, False], ids=["strict", "permissif"])
    @pytest.mark.parametrize("valeur", [np.nan, np.inf, -np.inf], ids=["nan", "+inf", "-inf"])
    def test_position_non_finie_rejetee_dans_les_deux_modes(self, strict, valeur):
        x = np.array([[0.0, 0.0], [valeur, 0.0], [0.5, 0.5]])
        proj = ProjectionExclusion(BoiteTournante(demi_largeur=1.0).projeter, strict=strict)

        with pytest.raises(ValueError, match="non finies"):
            proj(x, np.full(3, 0.1), 0.0)

    def test_cas_de_l_issue_16_ne_compte_plus_comme_converge(self):
        """La reproduction exacte de #16 : l'appel echoue sans polluer les mesures."""
        x = np.array([[0.0, 0.0], [np.nan, 0.0], [0.5, 0.5]])
        proj = ProjectionExclusion(BoiteTournante(demi_largeur=1.0).projeter, strict=True)

        with pytest.raises(ValueError):
            proj(x, np.full(3, 0.1), 0.0)

        assert proj.n_appels == 0
        assert proj.non_convergences == 0
        assert proj.recouvrement_max == 0.0

    def test_rayon_non_fini_rejete(self):
        x = np.array([[0.0, 0.0], [1.0, 0.0]])
        with pytest.raises(ValueError, match="non finies"):
            ProjectionExclusion()(x, np.array([0.1, np.nan]), 0.0)

    def test_agent_seul_non_fini_rejete(self):
        """Avec moins de deux agents, la recherche de paires est sautee : le controle doit
        avoir lieu avant, sinon un agent seul a NaN passerait par la seule projection du
        domaine."""
        proj = ProjectionExclusion(BoiteTournante(demi_largeur=1.0).projeter)
        with pytest.raises(ValueError, match="non finies"):
            proj(np.array([[np.nan, 0.0]]), np.array([0.1]), 0.0)

    def test_vitesse_libre_qui_produit_un_nan_interrompt_le_pas(self):
        """Source realiste a venir : un champ de guidage mal initialise rend NaN."""
        etat = State(x=np.array([[0.0, 0.0], [1.0, 0.0]]), v=np.zeros((2, 2)), r=np.full(2, 0.1))
        projection = ProjectionExclusion(BoiteTournante(demi_largeur=2.0).projeter, strict=True)

        with pytest.raises(ValueError, match="non finies"):
            pas_semi_implicite(etat, 1e-3, lambda e, _dt: np.full_like(e.v, np.nan), projection)
