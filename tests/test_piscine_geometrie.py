"""C6 : geometrie commune de la piscine, carte des milieux et guidage jusqu'a la porte."""

from dataclasses import replace

import numpy as np
import pytest

from viscocrowd.core.rng import generateur
from viscocrowd.geometry.obstacle import ObstacleRectangle
from viscocrowd.geometry.piscine import Piscine
from viscocrowd.model.carte import CartePiscine
from viscocrowd.model.eikonal import ChampEikonal, GrilleReguliere, fast_marching
from viscocrowd.model.guidage_piscine import GuidagePiscine
from viscocrowd.model.milieu import Milieu, ParametresMilieu

R = 0.2
PISCINE = Piscine(
    longueur_bassin=25.0,
    largeur_bassin=12.5,
    plage_gauche=3.0,
    plage_verticale=4.0,
    plage_sortie=20.0,
    largeur_porte=1.2,
    profondeur_porte=1.0,
    largeur_mouillee=3.0,
    pas_rebord=0.6,
    largeur_echelle=0.5,
    echelles=(("haut", 0.9), ("bas", 0.9)),
)
MILIEUX = {
    Milieu.EAU: ParametresMilieu(relaxation=0.5, acceleration_max=1.6, vitesse=0.69),
    Milieu.MOUILLE: ParametresMilieu(relaxation=0.5, acceleration_max=3.3, vitesse=1.34),
    Milieu.SEC: ParametresMilieu(relaxation=0.5, acceleration_max=5.9, vitesse=1.34),
}
DUREES = {"rebord": 4.0, "echelle": 2.0}


@pytest.fixture(scope="module")
def guidage():
    return GuidagePiscine(PISCINE, MILIEUX, R, 0.1, DUREES)


class TestGeometrie:
    def test_dimensions_du_plan_commun(self):
        """Mêmes dimensions que la maquette `DimensionsPlan` : 48 x 20,5 m, porte de 1,2 m."""
        assert (PISCINE.longueur_emprise, PISCINE.largeur_emprise) == (48.0, 20.5)
        b = PISCINE.bassin
        assert (b.x_min, b.x_max, b.y_min, b.y_max) == (3.0, 28.0, 4.0, 16.5)
        a, c = PISCINE.porte
        np.testing.assert_allclose([a, c], [[48.0, 9.65], [48.0, 10.85]])

    def test_sites_de_franchissement(self):
        sites = PISCINE.sites()
        echelles = [s for s in sites if s.nature == "echelle"]
        rebords = [s for s in sites if s.nature == "rebord"]
        assert len(echelles) == 2 and len(rebords) == 118
        np.testing.assert_allclose(echelles[0].position, [25.5, 16.5])
        for s in sites:
            assert np.hypot(*s.normale) == pytest.approx(1.0)
            # Le point d'attente est dans l'eau, l'arrivee sur la plage, chacun a un rayon du bord.
            assert PISCINE.dans_bassin(s.attente(R)[None])[0]
            assert not PISCINE.dans_bassin(s.arrivee(R)[None])[0]
            assert PISCINE.bassin.distance(s.arrivee(R)[None])[0] == pytest.approx(R)
        for e in echelles:  # pas de rebord sur l'echelle
            assert min(np.hypot(*(r.position - e.position)) for r in rebords) >= 0.55 - 1e-9

    @pytest.mark.parametrize(
        "changement",
        [
            {"echelles": (("dessus", 0.5),)},
            {"echelles": (("haut", 1.0),)},
            {"largeur_porte": 30.0},
            {"pas_rebord": 0.0},
            {"largeur_mouillee": -1.0},
            {"longueur_bassin": np.nan},
        ],
    )
    def test_parametres_invalides(self, changement):
        with pytest.raises(ValueError):
            replace(PISCINE, **changement)


class TestProjection:
    @pytest.mark.parametrize(
        "dimension",
        ["plage_gauche", "plage_verticale", "plage_sortie", "longueur_bassin", "largeur_bassin"],
    )
    def test_geometrie_trop_etroite_pour_le_disque_refusee(self, dimension):
        piscine = replace(PISCINE, **{dimension: 0.1})
        x, r = np.array([[0.05, 10.0]]), np.array([R])
        with pytest.raises(ValueError, match="diametre"):
            piscine.projeter(x, r, 0.0)
        with pytest.raises(ValueError, match="diametre"):
            piscine.violation(x, r, 0.0)
        with pytest.raises(ValueError, match="diametre"):
            GuidagePiscine(piscine, MILIEUX, R, 0.1, DUREES)

    def test_chaque_centre_reste_de_son_cote_et_respecte_les_murs(self):
        x = generateur(1).uniform([-1.0, -1.0], [49.5, 21.5], size=(5000, 2))
        r = np.full(5000, R)
        eau_avant = PISCINE.dans_bassin(x)
        projete = PISCINE.projeter(x, r, 0.0)
        assert PISCINE.violation(projete, r, 0.0) <= 1e-12
        np.testing.assert_array_equal(PISCINE.dans_bassin(projete), eau_avant)

    def test_la_porte_laisse_passer_et_les_montants_retiennent(self):
        r = np.full(3, R)
        x = np.array([[48.5, 10.25], [48.5, 12.0], [47.95, 9.7]])
        projete = PISCINE.projeter(x, r, 0.0)
        np.testing.assert_allclose(projete[0], [48.5, 10.25])  # dans le couloir de la porte
        assert projete[1, 0] <= 48.0 - R + 1e-12  # contre le mur, hors de la porte
        assert PISCINE.violation(projete, r, 0.0) <= 1e-12


def test_carte_des_milieux():
    carte = CartePiscine(PISCINE)
    x = np.array([[15.0, 10.0], [28.5, 10.0], [31.0, 10.0], [31.5, 10.0], [40.0, 10.0]])
    np.testing.assert_array_equal(
        carte(x), [Milieu.EAU, Milieu.MOUILLE, Milieu.MOUILLE, Milieu.SEC, Milieu.SEC]
    )


def test_sources_a_temps_initial_differents():
    """Deux sources aux bouts d'une ligne, 0 et 5 s : phi = min(x/F, (L - x)/F + 5), exact."""
    g = GrilleReguliere.couvrant(0.0, 10.0, 0.0, 1.0, 0.1)
    F = np.full(g.forme, 2.0)
    S = np.zeros(g.forme, dtype=bool)
    S[0, :] = S[-1, :] = True
    T0 = np.zeros(g.forme)
    T0[-1, :] = 5.0
    phi = fast_marching(F, S, g.pas, T0)
    x = g.noeuds()[..., 0]
    np.testing.assert_allclose(phi, np.minimum(x / 2.0, (10.0 - x) / 2.0 + 5.0), atol=1e-12)
    with pytest.raises(ValueError, match="temps_initial"):
        fast_marching(F, S, g.pas, np.full(g.forme, -1.0))


class TestGuidage:
    @pytest.mark.parametrize("cote", ["haut", "bas", "gauche", "droite"])
    def test_site_trop_pres_du_coin_refuse(self, cote):
        piscine = replace(PISCINE, echelles=((cote, 0.001),))
        with pytest.raises(ValueError, match=r"site.*admissible"):
            GuidagePiscine(piscine, MILIEUX, R, 0.1, DUREES)

    def test_absence_de_site_refusee(self):
        piscine = replace(PISCINE, echelles=(), pas_rebord=100.0)
        with pytest.raises(ValueError, match="site"):
            GuidagePiscine(piscine, MILIEUX, R, 0.1, DUREES)

    def test_plage_vers_la_porte(self, guidage):
        porte = np.array([[48.0, 10.25]])
        assert guidage.plage.temps(porte)[0] == pytest.approx(0.0, abs=1e-9)
        e = guidage.direction(np.array([[45.0, 10.25], [40.0, 2.0]]))
        assert e[0, 0] > 0.99  # face a la porte : tout droit
        assert e[1, 0] > 0.5 and e[1, 1] > 0.0  # depuis le bas : vers la porte

    def test_temps_dans_l_eau_egal_au_meilleur_site(self, guidage):
        """Le bassin est convexe : depuis x, le meilleur site minimise nage en ligne droite + reste.

        phi_eau doit retrouver ce minimum exact, a l'erreur d'ordre 1 du schema pres.
        """
        s_eau = MILIEUX[Milieu.EAU].vitesse
        attentes = np.array([s.attente(R) for s in guidage.sites])
        x = generateur(2).uniform([3.5, 4.5], [27.5, 16.0], size=(200, 2))
        distances = np.hypot(
            x[:, None, 0] - attentes[None, :, 0], x[:, None, 1] - attentes[None, :, 1]
        )
        exact = np.min(distances / s_eau + guidage.temps_sites[None, :], axis=1)
        ecart = guidage.temps(x) - exact
        assert np.max(np.abs(ecart)) < 0.3  # mesure : 0,182 s (0,108 s a h = 0,05 m)
        assert np.min(ecart) > -0.05  # le schema surestime, aux arrondis pres

    def test_le_partage_rebord_echelle_emerge_des_durees(self):
        """Echelles tres lentes : plus personne n'y va ; echelles instantanees : leur bassin grandit."""
        b = PISCINE.bassin
        depart = np.array(
            [[x, y] for x in np.arange(b.x_min + 0.5, b.x_max, 1.0) for y in (5.0, 10.25, 15.5)]
        )

        def part_echelles(duree_echelle):
            g = GuidagePiscine(PISCINE, MILIEUX, R, 0.1, {"rebord": 4.0, "echelle": duree_echelle})
            attentes = np.array([s.attente(R) for s in g.sites])
            nature = np.array([s.nature for s in g.sites])
            dist = np.hypot(
                depart[:, None, 0] - attentes[None, :, 0], depart[:, None, 1] - attentes[None, :, 1]
            )
            choix = np.argmin(dist / MILIEUX[Milieu.EAU].vitesse + g.temps_sites[None, :], axis=1)
            return np.mean(nature[choix] == "echelle")

        lentes, nominales, instantanees = (
            part_echelles(100.0),
            part_echelles(2.0),
            part_echelles(0.0),
        )
        assert lentes == 0.0
        assert 0.0 < nominales < instantanees < 1.0  # mesure : 0,147 puis 0,360

    def test_parametres_invalides(self):
        with pytest.raises(ValueError, match="pas"):
            GuidagePiscine(PISCINE, MILIEUX, R, 0.3, DUREES)
        with pytest.raises(ValueError, match="durees"):
            GuidagePiscine(PISCINE, MILIEUX, R, 0.1, {"rebord": 4.0})
        with pytest.raises(ValueError, match="manquants"):
            GuidagePiscine(PISCINE, {Milieu.SEC: MILIEUX[Milieu.SEC]}, R, 0.1, DUREES)


@pytest.mark.parametrize("champ", ["vitesse", "sortie", "temps_initial", "tous"])
def test_tableaux_incompatibles_avec_la_grille_refuses(champ):
    grille = GrilleReguliere(0.0, 0.0, 1.0, 4, 2)
    tableaux = {
        "vitesse": np.ones(grille.forme),
        "sortie": np.ones(grille.forme, dtype=bool),
        "temps_initial": np.zeros(grille.forme),
    }
    for nom in tableaux:
        if champ in (nom, "tous"):
            tableaux[nom] = tableaux[nom][:2]
    with pytest.raises(ValueError, match="grille"):
        ChampEikonal.depuis_tableaux(grille, **tableaux)


class TestObstaclesPlage:
    def test_obstacle_chevauchant_bassin_refuse(self):
        """Un obstacle sur la plage ne doit pas chevaucher le bassin."""
        obs = ObstacleRectangle(10.0, 15.0, 5.0, 8.0)
        with pytest.raises(ValueError, match="bassin"):
            replace(PISCINE, obstacles=(obs,))

    def test_obstacle_sur_plage_repousse_et_contraint(self):
        """Un obstacle rectangulaire sur la plage repousse les centres et est reporte en violation."""
        obs = ObstacleRectangle(35.0, 37.0, 8.0, 12.0)
        p = replace(PISCINE, obstacles=(obs,))
        # Point au centre de l'obstacle
        x = np.array([[36.0, 10.0]])
        r = np.array([R])
        assert p.violation(x, r, 0.0) > 0.0
        x_proj = p.projeter(x, r, 0.0)
        # Apres projection, le point est hors de l'obstacle et n'a plus de violation
        assert obs.distance(x_proj)[0] >= R - 1e-12
        assert p.violation(x_proj, r, 0.0) <= 1e-12

    def test_guidage_piscine_contourne_obstacle_sur_plage(self):
        """Devant l'obstacle, le guidage tourne et le trajet s'allonge (revue de #103).

        Sans obstacle, en (34 ; 10) la direction vaut (1 ; 0) et le temps jusqu'a la porte
        10,45 s. Avec l'obstacle 35-37 x 8-12, mesure : direction (0,41 ; 0,91) et 11,81 s.
        """
        obs = ObstacleRectangle(35.0, 37.0, 8.0, 12.0)
        sans = GuidagePiscine(PISCINE, MILIEUX, R, 0.2, DUREES)
        avec = GuidagePiscine(replace(PISCINE, obstacles=(obs,)), MILIEUX, R, 0.2, DUREES)
        devant = np.array([[34.0, 10.0]])
        np.testing.assert_allclose(sans.direction(devant), [[1.0, 0.0]], atol=1e-6)
        (e,) = avec.direction(devant)
        assert np.hypot(*e) == pytest.approx(1.0, abs=1e-9)
        assert abs(e[1]) > 0.5  # il longe l'obstacle au lieu d'aller droit dessus
        assert avec.temps(devant)[0] > sans.temps(devant)[0] + 1.0  # le detour coute

    @pytest.mark.parametrize(
        ("obstacle", "voisin"),
        [
            (ObstacleRectangle(40.0, 41.0, 18.0, 20.3), "le mur du haut"),  # 0,2 m du mur
            (ObstacleRectangle(28.1, 29.0, 8.0, 10.0), "le bassin"),  # 0,1 m du bord
        ],
    )
    def test_passage_plus_etroit_qu_un_diametre_refuse(self, obstacle, voisin):
        """Un passage de moins de 2r ne peut pas etre respecte des deux cotes a la fois."""
        p = replace(PISCINE, obstacles=(obstacle,))
        with pytest.raises(ValueError, match=f"avec {voisin} un passage"):
            p.valider_obstacles(R)
        with pytest.raises(ValueError, match="passage"):
            GuidagePiscine(p, MILIEUX, R, 0.2, DUREES)

    def test_passage_entre_deux_obstacles_refuse(self):
        a = ObstacleRectangle(35.0, 36.0, 8.0, 10.0)
        b = ObstacleRectangle(36.3, 37.0, 8.0, 10.0)  # 0,3 m entre les deux
        with pytest.raises(ValueError, match="obstacle 1"):
            replace(PISCINE, obstacles=(a, b)).valider_obstacles(R)

    @pytest.mark.parametrize("ecart", [0.0, 2 * R, 1.0])
    def test_obstacle_colle_ou_a_un_diametre_admis(self, ecart):
        """Colle au mur, il ne laisse aucun passage ; a un diametre ou plus, il est praticable."""
        obs = ObstacleRectangle(40.0, 41.0, 18.0, PISCINE.largeur_emprise - ecart)
        replace(PISCINE, obstacles=(obs,)).valider_obstacles(R)

    def test_obstacle_hors_emprise_refuse(self):
        with pytest.raises(ValueError, match="emprise"):
            replace(PISCINE, obstacles=(ObstacleRectangle(46.0, 49.0, 8.0, 9.0),))

    def test_obstacle_sur_les_arrivees_d_un_rebord_refuse(self):
        """Un obstacle colle au bord recouvre des points d'arrivee : refuse des la lecture.

        Avant la revue de #112, `valider_obstacles` l'admettait et seul le guidage le
        refusait, avec un message qui ne nommait pas l'obstacle.
        """
        b = PISCINE.bassin
        obs = ObstacleRectangle(10.0, 11.0, b.y_max, b.y_max + 1.0)
        p = replace(PISCINE, obstacles=(obs,))
        with pytest.raises(ValueError, match="obstacle 0 recouvre l'arrivee du site"):
            p.valider_obstacles(R)
        with pytest.raises(ValueError, match="obstacle 0 recouvre"):
            GuidagePiscine(p, MILIEUX, R, 0.2, DUREES)

    def test_obstacle_colle_au_bassin_dans_un_coin_admis(self):
        """Colle au bassin sans recouvrir de site (les coins n'en ont pas), il reste admis."""
        b = PISCINE.bassin
        obs = ObstacleRectangle(b.x_min - 1.0, b.x_min, b.y_max, b.y_max + 1.0)
        replace(PISCINE, obstacles=(obs,)).valider_obstacles(R)

    def test_obstacle_a_un_diametre_du_bassin_admis(self):
        """A 2r du bord, le disque d'arrivee touche l'obstacle sans y entrer."""
        b = PISCINE.bassin
        obs = ObstacleRectangle(10.0, 11.0, b.y_max + 2 * R, b.y_max + 1.0)
        replace(PISCINE, obstacles=(obs,)).valider_obstacles(R)
