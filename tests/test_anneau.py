"""Banc M8 en ecoulement libre : geometrie de l'anneau, meneur le long du cercle, vitesse."""

from pathlib import Path

import numpy as np
import pytest

from viscocrowd.geometry.anneau import Anneau
from viscocrowd.io.configuration import lire_configuration
from viscocrowd.scenarios.anneau import (
    jeu_au_meneur_anneau,
    parametres_anneau,
    positions_de_depart,
    simuler_anneau,
    vitesses_individuelles,
)

CONFIG = lire_configuration(Path(__file__).parents[1] / "experiments/anneau.yaml")


def test_projection_ramene_chaque_disque_entre_les_murs():
    anneau = Anneau(5.0, 7.0)
    x = np.array([[4.0, 0.0], [0.0, 7.5], [-6.0, 0.0]])
    r = np.full(3, 0.2)
    y = anneau.projeter(x, r, 0.0)
    np.testing.assert_allclose(np.hypot(*y.T), [5.2, 6.8, 6.0])
    # Projection radiale : l'angle ne change pas.
    np.testing.assert_allclose(np.arctan2(y[:, 1], y[:, 0]), np.arctan2(x[:, 1], x[:, 0]))
    assert anneau.violation(x, r, 0.0) == pytest.approx(1.2)
    assert anneau.violation(y, r, 0.0) == 0.0


def test_meneur_cherche_le_long_du_cercle_et_non_de_la_tangente():
    # Cas mesure le 16/11 : voisin 0,42 m plus loin du centre, 0,7 m devant. Le long de la
    # tangente, il passait a 0,376 m de l'axe (< 0,4 m) et freinait l'agent a tort.
    r = np.full(2, 0.2)
    voisin = np.array([[5.36, 0.0], [5.78 * np.cos(0.13), 5.78 * np.sin(0.13)]])
    assert np.all(np.isinf(jeu_au_meneur_anneau(voisin, r, 0.5)))
    # Sur la meme voie, 0,6 m devant : il mene, jeu = distance - 2 r ; l'autre n'a personne.
    a = 0.6 / 6.0
    file = np.array([[6.0, 0.0], [6.0 * np.cos(a), 6.0 * np.sin(a)]])
    jeux = jeu_au_meneur_anneau(file, r, 0.5)
    assert jeux[0] == pytest.approx(np.hypot(*(file[1] - file[0])) - 0.4)
    assert np.isinf(jeux[1])
    # Le sens direct est respecte de part et d'autre de theta = pi.
    couture = np.array([[-6.0, 0.3], [-6.0, -0.3]])
    jeux = jeu_au_meneur_anneau(couture, r, 0.5)
    assert np.isfinite(jeux[0]) and np.isinf(jeux[1])


def test_depart_sans_recouvrement_et_population_trop_grande_refusee():
    p = parametres_anneau(CONFIG, n_agents=300)
    x = positions_de_depart(p)
    assert x.shape == (300, 2)
    distances = np.hypot(*(x[:, None] - x[None]).transpose(2, 0, 1))
    np.fill_diagonal(distances, np.inf)
    assert distances.min() >= 2 * p.rayon
    assert p.anneau.violation(x, np.full(300, p.rayon), 0.0) == 0.0
    with pytest.raises(ValueError, match="population trop grande"):
        parametres_anneau(CONFIG, n_agents=2000)


@pytest.mark.invariant
def test_densite_faible_marche_a_la_vitesse_souhaitee():
    """Sans meneur a portee, l'ecoulement libre va a v0, sur toute la largeur."""
    p = parametres_anneau(CONFIG, n_agents=12, duree=8.0, debut_mesure=5.0)
    res = simuler_anneau(p)
    assert res.vitesse_moyenne == pytest.approx(1.34, rel=1e-3)
    assert res.violation_paroi_max <= p.tolerance
    assert res.recouvrement_max <= p.tolerance


@pytest.mark.invariant
def test_file_indienne_retrouve_la_vitesse_de_tordeux():
    """Une seule voie a pas uniforme : regime etabli V = (s - 2 r) / T, exactement.

    30 agents sur le cercle de rayon 3,25 m : corde s = 2 R sin(pi / 30) = 0,6795 m,
    jeu 0,2795 m, V = 0,7986 m/s pour T = 0,35 s, sous v0 = 1,34 m/s.
    """
    p = parametres_anneau(
        CONFIG,
        rayon_interieur=3.0,
        rayon_exterieur=3.5,
        n_agents=30,
        bruit=0.0,
        duree=10.0,
        debut_mesure=6.0,
    )
    res = simuler_anneau(p)
    corde = 2 * 3.25 * np.sin(np.pi / 30)
    attendu = (corde - 0.4) / 0.35
    assert res.vitesse_moyenne == pytest.approx(attendu, rel=1e-3)
    assert res.derive < 1e-3
    assert res.violation_paroi_max <= p.tolerance


def test_le_simulateur_refuse_l_anneau_sans_archive():
    from viscocrowd.scenarios.experience import _parametres

    with pytest.raises(ValueError, match="diagramme-anneau"):
        _parametres(CONFIG)


class TestNavigation:
    """Heuristiques de Moussaid et al. (2011) sur l'anneau (#158)."""

    def test_ne_se_cumule_pas_avec_temps_espacement(self):
        with pytest.raises(ValueError, match="ne se cumulent pas"):
            parametres_anneau(CONFIG, navigation={})  # l'exemple fixe temps_espacement
        p = parametres_anneau(CONFIG, navigation={"horizon": 8.0}, temps_espacement=None)
        assert p.navigation.horizon == 8.0

    def test_le_plus_rapide_borne_le_pas_de_temps(self):
        # 1,34 m/s x 0,0285 s = 0,038 m, sous r/5 = 0,04 m ; x 1,45 (3 sigma) : refuse.
        parametres_anneau(CONFIG, temps_espacement=None, dt=0.0285)
        with pytest.raises(ValueError, match="dt trop grand"):
            parametres_anneau(CONFIG, temps_espacement=None, dt=0.0285, navigation={})

    @pytest.mark.invariant
    def test_tient_les_murs_et_ralentit_sous_v0(self):
        p = parametres_anneau(
            CONFIG, n_agents=38, temps_espacement=None, navigation={}, duree=4.0, debut_mesure=2.0
        )
        res = simuler_anneau(p)
        assert res.violation_paroi_max <= p.tolerance
        assert res.recouvrement_max <= p.tolerance
        assert 0.5 < res.vitesse_moyenne < 1.34

    @pytest.mark.slow
    def test_reproduit_le_bilan_du_17_novembre(self):
        """Premier point de docs/mesures/navigation-2026-11-17/anneau.json, au bit pres.

        Ce bilan avait ete calcule sur une branche locale (f186b33) avant la fusion de
        #149 ; ce test etablit que le code du depot est le meme.
        """
        p = parametres_anneau(
            CONFIG,
            n_agents=19,
            graine=1,
            temps_espacement=None,
            navigation={},
            duree=40.0,
            debut_mesure=20.0,
        )
        assert simuler_anneau(p).vitesse_moyenne == 1.2257776328072303


class TestDepartEtPopulation:
    """#167 : casser la symetrie du banc (voies concentriques, vitesses identiques)."""

    def test_depart_desordonne_sans_recouvrement_entre_les_murs(self):
        p = parametres_anneau(CONFIG, n_agents=188, depart="desordonne")
        x = positions_de_depart(p)
        assert x.shape == (188, 2)
        distances = np.hypot(*(x[:, None] - x[None]).transpose(2, 0, 1))
        np.fill_diagonal(distances, np.inf)
        assert distances.min() > 2 * p.rayon
        assert p.anneau.violation(x, np.full(188, p.rayon), 0.0) == 0.0
        np.testing.assert_array_equal(x, positions_de_depart(p))  # meme graine, meme depart

    def test_depart_desordonne_n_a_pas_de_voies(self):
        """Les distances au centre couvrent la largeur au lieu de quatre valeurs."""
        voies = positions_de_depart(parametres_anneau(CONFIG, n_agents=113, bruit=0.0))
        desordre = positions_de_depart(parametres_anneau(CONFIG, n_agents=113, depart="desordonne"))
        assert np.unique(np.round(np.hypot(*voies.T), 6)).size <= 5
        assert np.unique(np.round(np.hypot(*desordre.T), 2)).size > 50

    def test_depart_desordonne_trop_dense_refuse(self):
        with pytest.raises(ValueError, match="trop grande pour un depart desordonne"):
            parametres_anneau(CONFIG, n_agents=600, depart="desordonne")

    def test_vitesses_dispersees_bornees_et_reproductibles(self):
        p = parametres_anneau(
            CONFIG,
            n_agents=2000,
            dispersion_vitesse=0.26,
            duree=1.0,
            debut_mesure=0.5,
            depart="voies",
            rayon_exterieur=40.0,
        )
        v = vitesses_individuelles(p)
        assert v.min() >= 1.34 - 2 * 0.26 - 1e-12 and v.max() <= 1.34 + 2 * 0.26 + 1e-12
        assert v.mean() == pytest.approx(1.34, abs=0.02)
        assert v.std() == pytest.approx(0.26, rel=0.15)  # loi bornee a deux ecarts-types
        np.testing.assert_array_equal(v, vitesses_individuelles(p))

    def test_sans_option_le_banc_est_inchange_au_bit_pres(self):
        a = simuler_anneau(parametres_anneau(CONFIG, n_agents=40, duree=2.0, debut_mesure=1.0))
        b = simuler_anneau(
            parametres_anneau(
                CONFIG,
                n_agents=40,
                duree=2.0,
                debut_mesure=1.0,
                depart="voies",
                dispersion_vitesse=0.0,
            )
        )
        np.testing.assert_array_equal(a.vitesse, b.vitesse)

    def test_les_vitesses_ne_changent_pas_le_depart(self):
        a = positions_de_depart(parametres_anneau(CONFIG, n_agents=75))
        b = positions_de_depart(parametres_anneau(CONFIG, n_agents=75, dispersion_vitesse=0.26))
        np.testing.assert_array_equal(a, b)

    def test_distances_au_centre_relevees_chaque_seconde_dans_la_fenetre(self):
        r = simuler_anneau(parametres_anneau(CONFIG, n_agents=20, duree=4.0, debut_mesure=1.0))
        assert r.distances_centre.shape == (3, 20)
        assert np.all((r.distances_centre > 5.0) & (r.distances_centre < 7.0))

    @pytest.mark.parametrize(
        "changements, motif",
        [
            ({"depart": "spirale"}, "depart doit valoir"),
            ({"dispersion_vitesse": -0.1}, "positive ou nulle"),
            ({"dispersion_vitesse": 0.7}, "deux ecarts-types"),
            (
                {"dispersion_vitesse": 0.1, "navigation": {}, "temps_espacement": None},
                "propre dispersion",
            ),
        ],
    )
    def test_options_mal_formees_refusees(self, changements, motif):
        with pytest.raises(ValueError, match=motif):
            parametres_anneau(CONFIG, **changements)
