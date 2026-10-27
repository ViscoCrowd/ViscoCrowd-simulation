"""Validation G2 : temps de parcours eikonal par Fast Marching, et detour d'un obstacle.

Les vitesses sont illustratives (couloir de `experiments/couloir.yaml`), pas une
calibration. Les references analytiques :

  - onde plane : phi = integrale de x a L de 1/F, exacte quand la sortie est une
    colonne de la grille ;
  - source ponctuelle en vitesse uniforme : phi = distance / F ;
  - obstacle rectangulaire : derriere lui, le plus court chemin passe par un coin.
"""

from itertools import pairwise

import numpy as np
import pytest

from viscocrowd.core.integrator import trajectoire
from viscocrowd.core.rng import generateur
from viscocrowd.core.state import State
from viscocrowd.geometry.couloir import Couloir
from viscocrowd.geometry.obstacle import ObstacleRectangle
from viscocrowd.geometry.projection import ProjectionExclusion
from viscocrowd.model.carte import CarteBandes
from viscocrowd.model.eikonal import (
    ChampEikonal,
    GrilleReguliere,
    fast_marching,
    vitesse_des_milieux,
)
from viscocrowd.model.guidage import direction_aval
from viscocrowd.model.milieu import Milieu, ParametresMilieu, pas_libre_milieux

SEC = ParametresMilieu(relaxation=0.3, acceleration_max=3.0, vitesse=1.5)
MOUILLE = ParametresMilieu(relaxation=0.6, acceleration_max=0.7, vitesse=1.0)
TOUT_SEC = CarteBandes((), (Milieu.SEC,))
L, W = 12.0, 3.0  # m, couloir du banc G1/G5
OBSTACLE = ObstacleRectangle(5.0, 6.0, -0.75, 0.75)


def sortie_en(x_sortie):
    return lambda p: p[:, 0] >= x_sortie - 1e-9


def couloir(pas, vitesse, obstacles=(), marge=0.0, longueur=L):
    grille = GrilleReguliere.couvrant(0.0, longueur, -W / 2, W / 2, pas)
    return ChampEikonal(
        grille, vitesse_des_milieux(*vitesse, obstacles, marge), sortie_en(longueur)
    )


def source_ponctuelle(pas):
    grille = GrilleReguliere.couvrant(-2.0, 2.0, -2.0, 2.0, pas)
    champ = ChampEikonal(
        grille, lambda p: np.ones(len(p)), lambda p: np.hypot(p[:, 0], p[:, 1]) < 1e-9
    )
    noeuds = grille.noeuds()
    return champ, np.hypot(noeuds[..., 0], noeuds[..., 1])


def detour_exact(noeuds):
    """Temps de parcours a vitesse 1 m/s autour d'OBSTACLE vers la sortie x = L."""
    x, y = noeuds[..., 0], noeuds[..., 1]
    o = OBSTACLE
    par_un_coin = np.minimum(np.hypot(o.x_min - x, o.y_max - y), np.hypot(o.x_min - x, o.y_min - y))
    dans_l_ombre = (x <= o.x_min) & (y > o.y_min) & (y < o.y_max)
    return np.where(dans_l_ombre, par_un_coin + L - o.x_min, L - x)


class TestFastMarching:
    def test_onde_plane_alignee_exacte(self):
        champ = couloir(0.05, (TOUT_SEC, {Milieu.SEC: SEC}))
        exact = (L - champ.grille.noeuds()[..., 0]) / SEC.vitesse
        np.testing.assert_allclose(champ.phi, exact, rtol=0, atol=1e-12)

    def test_bandes_de_milieux_donnent_l_integrale_de_1_sur_f(self):
        """Sec | mouille | sec : phi(x) = somme des longueurs restantes / vitesses."""
        bandes = CarteBandes((4.0, 8.0), (Milieu.SEC, Milieu.MOUILLE, Milieu.SEC))
        champ = couloir(0.05, (bandes, {Milieu.SEC: SEC, Milieu.MOUILLE: MOUILLE}))
        x = champ.grille.noeuds()[..., 0]

        def cumul(a):
            return (
                np.minimum(a, 4) / 1.5 + np.clip(a - 4, 0, 4) / 1.0 + np.clip(a - 8, 0, None) / 1.5
            )

        np.testing.assert_allclose(champ.phi, cumul(L) - cumul(x), rtol=0, atol=1e-12)

    def test_frontiere_entre_deux_noeuds_coute_au_plus_une_maille(self):
        """Une frontiere hors noeud est vue a h pres : erreur <= h |1/F1 - 1/F2| par frontiere."""
        h = 0.05
        bandes = CarteBandes((4.03, 8.03), (Milieu.SEC, Milieu.MOUILLE, Milieu.SEC))
        champ = couloir(h, (bandes, {Milieu.SEC: SEC, Milieu.MOUILLE: MOUILLE}))
        x = champ.grille.noeuds()[..., 0]

        def cumul(a):
            return (
                np.minimum(a, 4.03) / 1.5
                + np.clip(a - 4.03, 0, 4)
                + np.clip(a - 8.03, 0, None) / 1.5
            )

        erreur = np.abs(champ.phi - (cumul(L) - cumul(x)))
        assert erreur.max() <= 2 * h * (1 / MOUILLE.vitesse - 1 / SEC.vitesse) + 1e-12

    def test_source_ponctuelle_exacte_sur_les_axes_et_convergente(self):
        erreurs = []
        for h in (0.1, 0.05, 0.025):
            champ, distance = source_ponctuelle(h)
            centre = champ.grille.nx // 2
            np.testing.assert_allclose(champ.phi[centre], distance[centre], atol=1e-12)
            np.testing.assert_allclose(champ.phi[:, centre], distance[:, centre], atol=1e-12)
            erreurs.append(np.max(np.abs(champ.phi - distance)))
        # Mesure : 0,1025 ; 0,0621 ; 0,0368 m. Ordre 1, ralenti par la singularite de la source.
        assert erreurs[-1] < 0.04
        assert all(a / b > 1.5 for a, b in pairwise(erreurs))

    def test_phi_nul_sur_la_sortie_et_positif_ailleurs(self):
        champ = couloir(0.1, (TOUT_SEC, {Milieu.SEC: SEC}), [OBSTACLE])
        sortie = champ.grille.noeuds()[..., 0] >= L - 1e-9
        assert np.all(champ.phi[sortie] == 0.0)
        assert np.all(champ.phi[~sortie] > 0.0)

    def test_zone_coupee_de_la_sortie_reste_infinie(self):
        mur = ObstacleRectangle(5.0, 5.5, -2.0, 2.0)  # barre toute la largeur
        champ = couloir(0.1, (TOUT_SEC, {Milieu.SEC: SEC}), [mur])
        x = champ.grille.noeuds()[..., 0]
        assert np.all(np.isinf(champ.phi[x < 5.0]))
        assert np.all(np.isfinite(champ.phi[x > 5.5]))
        etat = State(x=np.array([[2.0, 0.0]]), v=np.zeros((1, 2)), r=np.array([0.2]))
        np.testing.assert_array_equal(champ(etat), 0.0)  # aucune direction : rien n'y mene

    @pytest.mark.parametrize(
        ("vitesse", "sortie", "pas", "message"),
        [
            (np.ones((3, 3)), np.zeros((3, 3), bool), 0.1, "aucun noeud de sortie"),
            (-np.ones((3, 3)), np.eye(3, dtype=bool), 0.1, "positive ou nulle"),
            (np.full((3, 3), np.nan), np.eye(3, dtype=bool), 0.1, "non finies"),
            (np.zeros((3, 3)), np.eye(3, dtype=bool), 0.1, "infranchissable"),
            (np.ones((3, 3)), np.eye(3), 0.1, "booleen"),
            (np.ones((3, 3)), np.eye(2, dtype=bool), 0.1, "booleen"),
            (np.ones(3), np.ones(3, bool), 0.1, "forme"),
            (np.ones((3, 3)), np.eye(3, dtype=bool), np.nan, "pas"),
            (np.ones((3, 3)), np.eye(3, dtype=bool), 0.0, "pas"),
        ],
    )
    def test_entrees_invalides(self, vitesse, sortie, pas, message):
        with pytest.raises(ValueError, match=message):
            fast_marching(vitesse, sortie, pas)

    @pytest.mark.parametrize(
        "arguments", [(0.0, 0.0, 0.1, 1, 5), (0.0, 0.0, -0.1, 5, 5), (0.0, np.inf, 0.1, 5, 5)]
    )
    def test_grille_invalide(self, arguments):
        with pytest.raises(ValueError):
            GrilleReguliere(*arguments)

    def test_grille_couvrante_sans_noeud_superflu(self):
        g = GrilleReguliere.couvrant(0.0, 12.0, -1.5, 1.5, 0.05)
        assert g.forme == (241, 61)
        assert g.noeuds()[-1, -1].tolist() == pytest.approx([12.0, 1.5])


class TestDirection:
    @pytest.mark.parametrize("axe", [0, 1])
    def test_deux_sorties_ne_creent_pas_un_arret_entre_les_noeuds(self, axe):
        """Une moyenne de directions opposees ne doit pas simuler une arrivee."""
        forme = (5, 2) if axe == 0 else (2, 5)
        grille = GrilleReguliere(0.0, 0.0, 1.0, *forme)
        champ = ChampEikonal(
            grille,
            lambda p: np.ones(len(p)),
            lambda p: (p[:, axe] == 0.0) | (p[:, axe] == 4.0),
        )
        # Le noeud x=2 choisit la sortie gauche, x=3 la droite. Leur moyenne
        # s'annulait a x=2,5 alors que la sortie droite est la plus proche.
        points = np.array([[2.5, 0.5], [2.5 - 1e-10, 0.5], [2.5 + 1e-10, 0.5]])
        sorties = np.array([[0.0, 0.5], [4.0, 0.5]])
        if axe == 1:
            points, sorties = points[:, ::-1], sorties[:, ::-1]
        attendu = np.zeros_like(points)
        attendu[:, axe] = 1.0
        np.testing.assert_array_equal(champ.direction(points), attendu)
        np.testing.assert_array_equal(champ.direction(sorties), 0.0)

    def test_couloir_redonne_la_direction_analytique_de_g1(self):
        """Sans obstacle, le champ calcule retrouve exactement direction_aval."""
        bandes = CarteBandes((4.0, 8.0), (Milieu.SEC, Milieu.MOUILLE, Milieu.SEC))
        champ = couloir(0.05, (bandes, {Milieu.SEC: SEC, Milieu.MOUILLE: MOUILLE}))
        x = np.column_stack(
            [np.linspace(0.2, L - 0.1, 300), np.linspace(-W / 2 + 0.2, W / 2 - 0.2, 300)]
        )
        etat = State(x=x, v=np.zeros_like(x), r=np.full(300, 0.2))
        np.testing.assert_array_equal(champ(etat), direction_aval(etat))

    def test_source_ponctuelle_direction_vers_la_source(self):
        x = generateur(0).uniform(-1.9, 1.9, size=(2000, 2))
        x = x[np.hypot(x[:, 0], x[:, 1]) > 0.5]
        exacte = -x / np.hypot(x[:, 0], x[:, 1])[:, None]
        ecarts = []
        for h in (0.1, 0.05, 0.025):
            champ, _ = source_ponctuelle(h)
            cosinus = np.clip(np.sum(champ.direction(x) * exacte, axis=1), -1.0, 1.0)
            ecarts.append(np.degrees(np.arccos(cosinus)).max())
        # Mesure : 7,07 ; 5,22 ; 3,60 degres au pire.
        assert ecarts[-1] < 4.0
        assert ecarts[0] > ecarts[1] > ecarts[2]

    def test_direction_unitaire_ou_nulle_et_nulle_dans_la_sortie(self):
        champ = couloir(0.1, (TOUT_SEC, {Milieu.SEC: SEC}), [OBSTACLE], 0.2, longueur=13.0)
        x = generateur(1).uniform([0, -W / 2], [13.5, W / 2], size=(2000, 2))
        normes = np.hypot(*champ.direction(x).T)
        assert np.all((normes == 0.0) | (np.abs(normes - 1.0) < 1e-12))
        assert np.all(champ.direction(np.array([[13.2, 0.0], [20.0, 1.0]])) == 0.0)

    def test_crete_derriere_l_obstacle_ne_bloque_pas(self):
        """Juste devant la face, sur l'axe de symetrie : on longe la face, on ne la pousse pas."""
        champ = couloir(0.05, (TOUT_SEC, {Milieu.SEC: SEC}), [OBSTACLE], 0.2)
        e = champ.direction(np.array([[OBSTACLE.x_min - 0.25, 0.0]]))[0]
        assert abs(e[1]) > 0.99

    def test_accepte_par_l_assemblage_des_milieux(self):
        champ = couloir(0.1, (TOUT_SEC, {Milieu.SEC: SEC}), [OBSTACLE], 0.2)
        etat = State(x=np.array([[1.0, 0.1], [7.0, -1.0]]), v=np.zeros((2, 2)), r=np.full(2, 0.2))
        libre = pas_libre_milieux(champ, TOUT_SEC, {Milieu.SEC: SEC})
        assert libre(etat, 0.01).shape == (2, 2)


class TestDetour:
    def test_depart_au_repos_entre_les_noeuds_devant_l_obstacle(self):
        """La crete interpolee doit choisir un detour, meme hors noeud de grille."""
        rayon = 0.2
        obstacle = ObstacleRectangle(5.0, 6.0, -0.5, 0.5)
        champ = couloir(0.25, (TOUT_SEC, {Milieu.SEC: SEC}), [obstacle], 0.25, longueur=L + 0.5)
        x0 = np.array([[4.5, 0.125]])
        initial = State(x=x0, v=np.zeros_like(x0), r=np.array([rayon]))
        libre = pas_libre_milieux(champ, TOUT_SEC, {Milieu.SEC: SEC})
        projection = ProjectionExclusion(Couloir(L, W).projeter, strict=True)
        _, x, _ = trajectoire(initial, 0.01, 10.0, libre, projection)

        assert x[-1, 0, 0] >= L  # avant correction, l'agent reste exactement en x0
        assert obstacle.distance(x[:, 0]).min() > rayon
        assert projection.non_convergences == 0

    def test_temps_de_parcours_derriere_l_obstacle_converge(self):
        un_metre_par_seconde = ParametresMilieu(relaxation=0.3, acceleration_max=3.0, vitesse=1.0)
        erreurs = []
        for h in (0.1, 0.05, 0.025):
            champ = couloir(h, (TOUT_SEC, {Milieu.SEC: un_metre_par_seconde}), [OBSTACLE])
            noeuds = champ.grille.noeuds()
            ombre = (noeuds[..., 0] <= 4.0) & (np.abs(noeuds[..., 1]) < 0.5)
            erreurs.append(np.max(np.abs(champ.phi - detour_exact(noeuds))[ombre]))
        # Mesure : 0,131 ; 0,090 ; 0,050 s sur un parcours d'environ 11 s.
        assert erreurs[-1] < 0.06
        assert erreurs[0] > erreurs[1] > erreurs[2]

    @pytest.mark.parametrize("y0", [0.0, 0.3, -0.45])
    def test_agent_contourne_l_obstacle_sans_le_toucher(self, y0):
        """Marge = rayon : le centre suit le champ, le disque ne touche jamais l'obstacle."""
        rayon = 0.2
        obstacle = ObstacleRectangle(5.0, 6.0, -0.5, 0.5)
        champ = couloir(0.05, (TOUT_SEC, {Milieu.SEC: SEC}), [obstacle], rayon, longueur=L + 0.5)
        initial = State(x=np.array([[1.0, y0]]), v=np.zeros((1, 2)), r=np.array([rayon]))
        projection = ProjectionExclusion(Couloir(L, W).projeter, strict=True)
        libre = pas_libre_milieux(champ, TOUT_SEC, {Milieu.SEC: SEC})
        t, x, _ = trajectoire(initial, 0.01, 10.0, libre, projection)

        assert obstacle.distance(x[:, 0]).min() > rayon  # mesure : marge de 1,9 a 6,4 cm
        arrivee = t[np.argmax(x[:, 0, 0] >= L)]
        assert x[-1, 0, 0] >= L

        def contour(coin):
            return (np.hypot(coin[0] - 1.0, coin[1] - abs(y0)) + L - coin[0]) / SEC.vitesse

        # Borne basse stricte : |v| <= s, et le centre reste hors de l'obstacle nu.
        borne_basse = contour((obstacle.x_min, obstacle.y_max))
        # Reference : obstacle gonfle du rayon, a coins vifs, parcouru a s sans phase d'acceleration.
        reference = contour((obstacle.x_min - rayon, obstacle.y_max + rayon))
        # Mesure : reference + 0,34 s, soit environ tau, le retard de la mise en vitesse.
        assert borne_basse < arrivee < reference + SEC.relaxation + 0.1

    def test_groupe_contourne_avec_l_exclusion(self):
        """12 agents en contact : la projection ne connait pas l'obstacle, le guidage suffit ici."""
        rayon, h = 0.2, 0.05
        obstacle = ObstacleRectangle(5.0, 6.0, -0.5, 0.5)
        champ = couloir(h, (TOUT_SEC, {Milieu.SEC: SEC}), [obstacle], rayon + h, longueur=L + 0.5)
        x0 = np.array([[0.5 + 0.5 * (k % 4), -0.6 + 0.6 * (k // 4)] for k in range(12)])
        initial = State(x=x0, v=np.zeros_like(x0), r=np.full(12, rayon))
        projection = ProjectionExclusion(Couloir(L, W).projeter, strict=True)
        libre = pas_libre_milieux(champ, TOUT_SEC, {Milieu.SEC: SEC})
        _, x, _ = trajectoire(initial, 0.01, 20.0, libre, projection)

        assert np.all(x[-1, :, 0] >= L)
        assert obstacle.distance(x.reshape(-1, 2)).min() > rayon  # mesure : 6,7 cm de marge
        assert projection.non_convergences == 0
        # Controle geometrique independant des diagnostics du projecteur : le
        # groupe rencontre bien des contacts, sans recouvrement hors tolerance.
        i, j = np.triu_indices(len(x0), 1)
        distances = np.linalg.norm(x[:, i] - x[:, j], axis=2)
        assert np.max(2 * rayon - distances) <= projection.tolerance * (1 + 1e-8)
        assert np.min(distances) < 2 * rayon + 1e-6
