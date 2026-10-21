"""C6 : geometrie commune de la piscine, carte des milieux et guidage jusqu'a la porte."""

from dataclasses import replace

import numpy as np
import pytest

from viscocrowd.core.rng import generateur
from viscocrowd.geometry.piscine import Piscine
from viscocrowd.model.carte import CartePiscine
from viscocrowd.model.eikonal import GrilleReguliere, fast_marching
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
