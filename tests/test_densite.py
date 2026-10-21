"""Densite de Voronoi (M1) : valeurs exactes sur des reseaux, identites de pavage, repli."""

import numpy as np
import pytest

from viscocrowd.core.rng import generateur
from viscocrowd.observables.densite import (
    Rectangle,
    aire_polygone,
    cellules,
    decouper,
    densite_comptage,
    densite_voronoi,
    vitesse_voronoi,
)

SALLE = Rectangle(0.0, 10.0, 0.0, 6.0)


def reseau_carre(a, salle=SALLE):
    xs = np.arange(salle.x_min + a / 2, salle.x_max, a)
    ys = np.arange(salle.y_min + a / 2, salle.y_max, a)
    return np.array([[x, y] for x in xs for y in ys])


def reseau_hexagonal(a, salle=SALLE):
    h = a * np.sqrt(3) / 2
    points = []
    for k, y in enumerate(np.arange(salle.y_min + h / 2, salle.y_max - 1e-9, h)):
        decalage = a / 2 if k % 2 else 0.0
        for x in np.arange(salle.x_min + a / 4 + decalage, salle.x_max - 1e-9, a):
            points.append([x, y])
    return np.array(points)


class TestGeometrie:
    @pytest.mark.parametrize("decalage", [0.0, 1e-14])
    def test_centres_confondus_ou_fusionnes_par_qhull_refuses(self, decalage):
        x = np.array([[2.0, 3.0], [2.0 + decalage, 3.0], [8.0, 3.0]])
        with pytest.raises(ValueError, match=r"distinct|degenere"):
            cellules(x, SALLE)
        with pytest.raises(ValueError, match=r"distinct|degenere"):
            vitesse_voronoi(x, np.tile([1.0, 0.0], (3, 1)), SALLE, SALLE)

    def test_aire_et_decoupage(self):
        carre = np.array([[0.0, 0.0], [2.0, 0.0], [2.0, 2.0], [0.0, 2.0]])
        assert aire_polygone(carre) == 4.0
        moitie = decouper(carre, Rectangle(1.0, 5.0, -1.0, 5.0))
        assert aire_polygone(moitie) == pytest.approx(2.0)
        assert decouper(carre, Rectangle(3.0, 4.0, 3.0, 4.0)).shape[0] == 0

    def test_les_cellules_pavent_la_salle(self):
        x = generateur(1).uniform([0.1, 0.1], [9.9, 5.9], size=(200, 2))
        aires = [aire_polygone(c) for c in cellules(x, SALLE)]
        assert sum(aires) == pytest.approx(SALLE.aire, rel=1e-12)
        assert min(aires) > 0.0


class TestDensite:
    def test_reseau_carre_exact(self):
        """Cellules carrees de cote a : rho = 1/a^2 dans toute zone interieure."""
        a = 0.5
        zone = Rectangle(2.0, 7.0, 1.0, 5.0)
        assert densite_voronoi(reseau_carre(a), SALLE, zone) == pytest.approx(1 / a**2, rel=1e-12)

    def test_reseau_hexagonal_exact(self):
        """Empilement compact de pas a : rho = 2 / (sqrt(3) a^2), loin des bords."""
        a = 0.4
        zone = Rectangle(3.0, 7.0, 2.0, 4.0)
        attendu = 2 / (np.sqrt(3) * a**2)
        assert densite_voronoi(reseau_hexagonal(a), SALLE, zone) == pytest.approx(attendu, rel=1e-9)

    def test_salle_entiere_donne_n_sur_aire_exactement(self):
        """Toutes les cellules sont dans la zone : chaque agent compte exactement 1."""
        x = generateur(2).uniform([0.1, 0.1], [9.9, 5.9], size=(137, 2))
        assert densite_voronoi(x, SALLE, SALLE) == pytest.approx(137 / SALLE.aire, rel=1e-12)

    def test_sans_biais_par_rapport_au_comptage(self):
        """En moyenne sur des nuages uniformes, Voronoi et comptage s'accordent ; Voronoi varie moins."""
        zone = Rectangle(3.0, 6.0, 2.0, 4.0)
        rng = generateur(3)
        voronoi, comptage = [], []
        for _ in range(300):
            x = rng.uniform([0.01, 0.01], [9.99, 5.99], size=(120, 2))
            voronoi.append(densite_voronoi(x, SALLE, zone))
            comptage.append(densite_comptage(x, zone))
        attendu = 120 / SALLE.aire
        assert np.mean(voronoi) == pytest.approx(attendu, rel=0.02)
        assert np.mean(comptage) == pytest.approx(attendu, rel=0.03)
        assert np.std(voronoi) < np.std(comptage)  # mesure : 1,34 fois moins disperse

    def test_continuite_quand_un_agent_entre(self):
        """Le comptage saute de 1/|M| ; Voronoi varie peu pour un deplacement de 2 cm."""
        zone = Rectangle(4.0, 6.0, 2.0, 4.0)
        x = reseau_carre(1.0)
        avant, apres = x.copy(), x.copy()
        k = int(np.argmin(np.hypot(x[:, 0] - 3.5, x[:, 1] - 2.5)))  # juste hors de la zone
        avant[k] = [3.99, 2.5]
        apres[k] = [4.01, 2.5]
        saut_comptage = densite_comptage(apres, zone) - densite_comptage(avant, zone)
        saut_voronoi = densite_voronoi(apres, SALLE, zone) - densite_voronoi(avant, SALLE, zone)
        assert saut_comptage == pytest.approx(1 / zone.aire)
        assert abs(saut_voronoi) < 0.05 * saut_comptage


class TestVitesse:
    def test_vitesse_uniforme_restituee(self):
        x = generateur(4).uniform([0.1, 0.1], [9.9, 5.9], size=(80, 2))
        v = np.tile([1.2, -0.5], (80, 1))
        zone = Rectangle(2.0, 8.0, 1.0, 5.0)
        assert vitesse_voronoi(x, v, SALLE, zone) == pytest.approx(1.3, rel=1e-12)
        assert vitesse_voronoi(x, v, SALLE, zone, direction=[1.0, 0.0]) == pytest.approx(1.2)

    def test_direction_non_unitaire_refusee(self):
        x = reseau_carre(1.0)
        with pytest.raises(ValueError, match="unitaire"):
            vitesse_voronoi(x, np.zeros_like(x), SALLE, SALLE, direction=[2.0, 0.0])


@pytest.mark.parametrize(
    ("x", "zone", "message"),
    [
        (np.array([[0.0, 1.0]]), SALLE, "interieur"),  # sur le mur
        (np.array([[11.0, 1.0]]), SALLE, "interieur"),
        (np.array([[np.nan, 1.0]]), SALLE, "non finies"),
        (np.empty((0, 2)), SALLE, "forme"),
        (np.array([[5.0, 3.0]]), Rectangle(5.0, 12.0, 0.0, 1.0), "incluse"),
    ],
)
def test_entrees_invalides(x, zone, message):
    with pytest.raises(ValueError, match=message):
        densite_voronoi(x, SALLE, zone)


@pytest.mark.slow
def test_biais_de_densite_de_la_tolerance_indiscernable_sur_huit_graines():
    """Issue #10 : la tolerance de projection biaise-t-elle la densite MESUREE ?

    60 agents (rayons 0,18 a 0,22 m) pousses contre une paroi a 1,5 m/s puis
    arretes ; densite de Voronoi contre la paroi. Comparaison appariee, graine par
    graine, tolerance 1e-6 contre 1e-9 m. Les arrangements sont sensibles aux
    perturbations (PR #48), ce qui ne constitue pas une preuve de chaos.

    Mesure : difference moyenne +0,0146 pers/m^2 (+0,22 %), erreur standard
    0,034 ; dispersion entre graines 2,1 %. Revue macOS arm64 : moyenne 0,035154,
    erreur standard 0,059588 ; le second critere ECHOUE. Ces statistiques ne
    demontrent ni absence d'effet ni borne universelle. Test conserve sans seuil
    releve : protocole et critere restent a justifier avant fusion de la PR #53.
    """
    from viscocrowd.core.integrator import pas_semi_implicite
    from viscocrowd.core.state import State
    from viscocrowd.geometry.boite import BoiteTournante
    from viscocrowd.geometry.projection import ProjectionExclusion
    from viscocrowd.model.milieu import Milieu, ParametresMilieu, pas_libre_milieux

    boite, zone = Rectangle(-2.5, 2.5, -2.5, 2.5), Rectangle(1.0, 2.5, -1.5, 1.5)
    sec = {Milieu.SEC: ParametresMilieu(relaxation=0.3, acceleration_max=3.0, vitesse=1.5)}

    def partout(points):
        return np.full(points.shape[0], Milieu.SEC, dtype=np.int64)

    pousse = pas_libre_milieux(lambda e: np.tile([1.0, 0.0], (e.n, 1)), partout, sec)
    arret = pas_libre_milieux(lambda e: np.zeros((e.n, 2)), partout, sec)

    def densite(tolerance, graine):
        rng = generateur(graine)
        x = np.array([[-2.0 + 0.5 * (k % 8), -2.0 + 0.5 * (k // 8)] for k in range(60)])
        x += rng.uniform(-0.02, 0.02, size=x.shape)
        etat = State(x=x, v=np.zeros_like(x), r=rng.uniform(0.18, 0.22, size=60))
        projection = ProjectionExclusion(
            BoiteTournante(2.5).projeter, tolerance=tolerance, iterations=3000
        )
        for libre, duree in ((pousse, 8.0), (arret, 4.0)):
            for _ in range(round(duree / 0.01)):
                etat = pas_semi_implicite(etat, 0.01, libre, projection)
        assert projection.non_convergences == 0
        return densite_voronoi(etat.x, boite, zone)

    graines = range(1, 9)
    ecarts = np.array([densite(1e-6, g) - densite(1e-9, g) for g in graines])
    erreur_standard = ecarts.std(ddof=1) / np.sqrt(len(ecarts))
    # Criteres initiaux conserves pour rendre l'echec visible, sans preuve d'absence d'effet.
    assert abs(ecarts.mean()) < 2 * erreur_standard
    assert abs(ecarts.mean()) + 2 * erreur_standard < 0.02 * 6.5


def test_rectangle_degenere_refuse():
    with pytest.raises(ValueError):
        Rectangle(1.0, 1.0, 0.0, 1.0)
