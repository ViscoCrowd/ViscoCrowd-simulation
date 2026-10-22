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
    mesures_voronoi,
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

    def test_listes_acceptees_formes_invalides_refusees(self):
        assert aire_polygone([[0, 0], [1, 0], [1, 1]]) == 0.5
        assert aire_polygone(decouper([[0, 0], [2, 0], [2, 2]], Rectangle(0, 1, 0, 3))) == 0.5
        assert aire_polygone([]) == 0.0
        with pytest.raises(ValueError, match="forme"):
            aire_polygone([0.0, 1.0, 2.0])
        with pytest.raises(ValueError, match="non fini"):
            decouper([[0, 0], [np.nan, 0], [1, 1]], SALLE)

    def test_cellule_non_bornee_leve_value_error(self, monkeypatch):
        """Tous les cas degeneres levent ValueError, y compris une cellule infinie."""
        import viscocrowd.observables.densite as module

        class VoronoiInfini:
            def __init__(self, points):
                self.point_region = np.arange(points.shape[0])
                self.regions = [[-1, 0, 1]] * points.shape[0]
                self.vertices = np.zeros((2, 2))

        monkeypatch.setattr(module, "Voronoi", VoronoiInfini)
        with pytest.raises(ValueError, match="non bornee"):
            cellules(np.array([[2.0, 3.0], [8.0, 3.0]]), SALLE)

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

    @pytest.mark.parametrize("norme", [2.0, 1.000009, 1.0 + 1e-8])
    def test_direction_non_unitaire_refusee(self, norme):
        """Meme tolerance que le guidage (1e-9) : 1,000009 n'est pas unitaire."""
        x = reseau_carre(1.0)
        with pytest.raises(ValueError, match="unitaire"):
            vitesse_voronoi(x, np.zeros_like(x), SALLE, SALLE, direction=[norme, 0.0])

    def test_mesures_conjointes_identiques_aux_mesures_separees(self):
        rng = generateur(5)
        x = rng.uniform([0.1, 0.1], [9.9, 5.9], size=(90, 2))
        v = rng.normal(size=(90, 2))
        zone = Rectangle(2.5, 6.5, 1.5, 4.5)
        rho, vit = mesures_voronoi(x, v, SALLE, zone, direction=[0.0, 1.0])
        assert rho == densite_voronoi(x, SALLE, zone)
        assert vit == vitesse_voronoi(x, v, SALLE, zone, direction=[0.0, 1.0])


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
    erreur standard 0,059588.

    Critere (revue de la PR #53). L'ancienne borne « moins de 2 % » n'etait pas
    justifiee : avec huit graines, la demi-largeur d'un intervalle a 95 % (environ
    2,4 erreurs standard) vaut deja 1,2 a 2,2 % ; elle echouait sur macOS. Le test
    ne verifie plus qu'une chose, avec un critere sans hypothese de normalite : un
    test de permutation EXACT sur les huit differences appariees (les 2^8 signes
    possibles, exact sous l'hypothese d'echangeabilite des deux resultats d'une meme
    graine) ne detecte pas de difference au seuil de 5 %. Ce n'est pas une
    preuve d'absence d'effet, seulement l'absence de detection a cet effectif ;
    borner l'effet demanderait davantage de graines, sur la geometrie cible (#10).
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
    # Mesure : p = 0,633 (x86-64) et 0,539 (revue, macOS arm64).
    assert valeur_p_permutation_appariee(ecarts) > 0.05


def valeur_p_permutation_appariee(ecarts: np.ndarray) -> float:
    """Valeur p bilaterale exacte du test de permutation sur des differences appariees.

    Hypothese nulle : les deux resultats d'une meme graine sont ECHANGEABLES (les
    graines etant independantes), donc chaque difference est symetrique autour de
    zero. Ce n'est pas la seule egalite des moyennes. On enumere alors les 2^n signes
    et on compte la part des moyennes au moins aussi eloignees de zero que la moyenne
    observee. C'est le test de scipy.stats.permutation_test avec
    permutation_type="samples", ecrit ici pour rester lisible et exact.
    """
    n = len(ecarts)
    signes = 1 - 2 * ((np.arange(2**n)[:, None] >> np.arange(n)) & 1)
    moyennes = np.abs(signes @ ecarts) / n
    # Egalites a l'arrondi pres, relativement a l'echelle des ecarts : une tolerance
    # absolue fixe deviendrait trop stricte si les ecarts grandissaient.
    tolerance = 1e-12 * np.abs(ecarts).mean()
    return float(np.mean(moyennes >= abs(ecarts.mean()) - tolerance))


def test_permutation_appariee():
    """Le test de permutation retrouve des valeurs p connues."""
    assert valeur_p_permutation_appariee(np.full(8, 1.0)) == pytest.approx(2 / 256)
    assert valeur_p_permutation_appariee(np.array([1.0, -1.0] * 4)) == 1.0
    revue_macos = np.array(
        [
            0.000411737,
            -0.21777055,
            0.050258825,
            0.32141218,
            0.00001694,
            0.000009344,
            -0.090530954,
            0.217425845,
        ]
    )
    assert valeur_p_permutation_appariee(revue_macos) > 0.05
    # Invariante par changement d'echelle : la tolerance suit la taille des ecarts.
    for echelle in (1e-6, 1e6):
        assert valeur_p_permutation_appariee(echelle * revue_macos) == pytest.approx(
            valeur_p_permutation_appariee(revue_macos)
        )
        assert valeur_p_permutation_appariee(np.full(8, echelle)) == pytest.approx(2 / 256)


def test_rectangle_degenere_refuse():
    with pytest.raises(ValueError):
        Rectangle(1.0, 1.0, 0.0, 1.0)
