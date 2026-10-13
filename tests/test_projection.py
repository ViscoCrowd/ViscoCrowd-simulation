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
        [({"tolerance": 0.0}, "tolerance"), ({"iterations": 0}, "iteration")],
    )
    def test_parametres_invalides(self, kwargs, message):
        with pytest.raises(ValueError, match=message):
            ProjectionExclusion(**kwargs)


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
    def _choquer(x0, v0, rayon=0.1, dt=1e-3, pas=2000):
        """Lache des disques les uns contre les autres, sans force exterieure."""
        etat = State(
            x=np.array(x0, dtype=float),
            v=np.array(v0, dtype=float),
            r=np.full(len(x0), rayon),
        )
        projection = ProjectionExclusion(tolerance=TOLERANCE)
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

    def test_triangle_qui_s_effondre_sur_son_centre(self):
        """Trois disques convergent vers le centre : chacun touche les deux autres."""
        angles = np.array([90.0, 210.0, 330.0]) * np.pi / 180.0
        x0 = 0.5 * np.stack([np.cos(angles), np.sin(angles)], axis=1)
        v0 = -x0 / np.linalg.norm(x0, axis=1, keepdims=True)  # 1 m/s vers le centre

        etat, energie_initiale, _ = self._choquer(x0, v0)

        energie = 0.5 * float(np.sum(etat.v**2))
        assert energie / energie_initiale < self.RESTITUTION_MAX
        # Triangle equilateral de cote 0,2 m : les trois sont tangents deux a deux,
        # a 1,7e-3 m pres. Ce jeu residuel est le defaut de POSITION propre aux
        # trois contacts mutuels corriges dans le meme balayage : il sature vers
        # 1,69e-3 m (mesure pour v0 de 0,5 a 2 m/s et dt de 5e-4 a 1e-3 s) et ne
        # se traduit par aucun mouvement, l'energie residuelle restant sous
        # RESTITUTION_MAX.
        for a, b in ((0, 1), (1, 2), (0, 2)):
            distance = np.linalg.norm(etat.x[b] - etat.x[a])
            assert distance >= 0.2 - TOLERANCE  # jamais d'interpenetration
            assert distance == pytest.approx(0.2, abs=3e-3)

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
