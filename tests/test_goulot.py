"""Banc E0 : salle et goulot, etat initial du protocole de Seyfried et al. (2009), debit."""

from pathlib import Path

import numpy as np
import pytest
import yaml

from viscocrowd.cli import main
from viscocrowd.geometry.salle import SalleGoulot
from viscocrowd.io.configuration import lire_configuration
from viscocrowd.scenarios.goulot import (
    ParametresGoulot,
    debit_central,
    simuler_goulot,
    tirages_initiaux,
)

EXEMPLE = Path(__file__).parents[1] / "experiments/goulot.yaml"
SALLE = SalleGoulot(longueur=8.0, largeur=5.0, largeur_goulot=1.0, longueur_goulot=2.8)
R = 0.2


def parametres(**changements):
    config = lire_configuration(EXEMPLE)
    return ParametresGoulot(**(config["parametres"] | changements), graine=config["graine"])


class TestSalleGoulot:
    def test_goulot_plus_large_que_la_salle_refuse(self):
        with pytest.raises(ValueError, match="goulot"):
            SalleGoulot(8.0, 1.0, 1.2, 2.8)

    def test_disque_trop_large_pour_le_goulot_refuse(self):
        with pytest.raises(ValueError, match="rayon"):
            SALLE.projeter(np.array([[4.0, 2.5]]), np.array([0.5]))

    def test_ligne_de_mesure_en_travers_du_goulot(self):
        a, b = SALLE.entree(0.4)
        np.testing.assert_allclose(a, [8.4, 2.0])
        np.testing.assert_allclose(b, [8.4, 3.0])

    @pytest.mark.parametrize(
        ("dehors", "attendu"),
        [
            ([0.1, 2.5], [R, 2.5]),  # mur du fond
            ([4.0, 4.9], [4.0, 5.0 - R]),  # mur lateral
            ([7.9, 1.0], [8.0 - R, 1.0]),  # mur perce, sous le goulot
            ([9.0, 2.1], [9.0, 2.0 + R]),  # paroi basse du goulot
            ([9.0, 2.9], [9.0, 3.0 - R]),  # paroi haute du goulot
        ],
    )
    def test_centre_ramene_a_un_rayon_du_mur_le_plus_proche(self, dehors, attendu):
        np.testing.assert_allclose(SALLE.projeter(np.array([dehors]), np.array([R])), [attendu])

    def test_angle_d_entree_arrondi(self):
        """Un disque glisse autour de l'angle du goulot : il n'y est pas cale par deux murs."""
        x = SALLE.projeter(np.array([[7.95, 2.05]]), np.array([R]))
        np.testing.assert_allclose(np.linalg.norm(x[0] - [8.0, 2.0]), R, atol=1e-15)
        np.testing.assert_allclose((x[0] - [8.0, 2.0]) / R, [-np.sqrt(0.5), np.sqrt(0.5)])

    def test_le_goulot_debouche_sur_l_exterieur(self):
        x = np.array([[10.9, 2.5], [11.5, 2.5]])
        np.testing.assert_array_equal(SALLE.projeter(x, np.full(2, R)), x)

    def test_projection_idempotente_et_sans_violation(self):
        x = np.random.default_rng(3).uniform([-0.5, -0.5], [11.0, 5.5], size=(4000, 2))
        r = np.full(x.shape[0], R)
        une_fois = SALLE.projeter(x, r)
        assert SALLE.violation(une_fois, r) <= 1e-15
        np.testing.assert_allclose(SALLE.projeter(une_fois, r), une_fois, atol=1e-14)
        admis = SALLE.admissible(x, R)
        np.testing.assert_array_equal(une_fois[admis], x[admis])
        assert SALLE.violation(x[~admis], r[~admis]) > 0.0

    def test_violation_mesure_le_depassement(self):
        assert SALLE.violation(np.array([[0.1, 2.5]]), np.array([R])) == pytest.approx(0.1)
        assert SALLE.violation(np.array([[9.0, 2.1]]), np.array([R])) == pytest.approx(0.1)


class TestEtatInitial:
    def test_densite_et_distance_du_protocole(self):
        p = parametres()
        x, r, _ = tirages_initiaux(p)
        assert x.shape == (60, 2)
        np.testing.assert_array_equal(r, 0.2)
        # Reseau hexagonal : une maille de surface a^2 sqrt(3)/2 par agent.
        assert 1 / (p.pas_reseau**2 * np.sqrt(3) / 2) == pytest.approx(3.3)
        assert np.mean(x[:, 0]) == pytest.approx(p.longueur - p.distance_attente, abs=0.3)
        i, j = np.triu_indices(60, 1)
        assert np.min(np.linalg.norm(x[i] - x[j], axis=1)) >= 2 * p.rayon

    def test_meme_graine_memes_tirages(self):
        p = parametres(dispersion_rayon=0.1)
        x1, r1, rng1 = tirages_initiaux(p)
        x2, r2, rng2 = tirages_initiaux(p)
        np.testing.assert_array_equal(x1, x2)
        np.testing.assert_array_equal(r1, r2)
        assert rng1.normal() == rng2.normal()
        assert np.all((r1 >= 0.18) & (r1 <= 0.22)) and np.ptp(r1) > 0.0


@pytest.mark.parametrize(
    "changement",
    [
        {"rayon": 0.6},  # ne passe pas le goulot
        {"dispersion_rayon": 1.0},
        {"position_mesure": 2.8},  # hors du goulot
        {"densite_initiale": 8.0},  # disques recouverts au depart
        {"n_agents": 200},  # zone d'attente trop petite
        {"dt": 0.1},  # deplacement par pas > r/5
        {"pas_guidage": 0.3},
        {"bruit_direction": -0.1},
        {"correlation_bruit": 0.0},
        {"n_agents": 1.5},
        {"duree": np.nan},
    ],
)
def test_parametres_invalides(changement):
    with pytest.raises(ValueError):
        parametres(**changement)


def test_debit_central_d_un_flux_regulier():
    """Un passage toutes les 0,5 s par un goulot de 1 m : 2 pers/(m.s)."""
    passages = np.concatenate((np.arange(20) * 0.5, [np.nan]))
    assert debit_central(passages, 1.0) == pytest.approx(2.0)
    assert np.isnan(debit_central(np.array([1.0, np.nan]), 1.0))


@pytest.fixture(scope="module")
def petit_groupe():
    return simuler_goulot(parametres(n_agents=12, duree=20.0))


@pytest.mark.invariant
def test_petit_groupe_sans_recouvrement_ni_violation(petit_groupe):
    r = petit_groupe
    assert r.projection.non_convergences == 0
    assert r.violation_paroi_max() <= 1e-14
    i, j = np.triu_indices(r.parametres.n_agents, 1)
    distances = np.linalg.norm(r.x[:, i] - r.x[:, j], axis=2)
    recouvrement = r.rayons[i] + r.rayons[j] - distances
    # Les sortis sont absorbes, figes au dela du goulot : seules les paires encore dedans
    # sont soumises a l'exclusion.
    sortie = r.parametres.longueur + r.parametres.longueur_goulot
    dedans = (r.x[:, i, 0] < sortie) & (r.x[:, j, 0] < sortie)
    assert np.max(recouvrement[dedans]) <= r.parametres.tolerance * (1 + 1e-8)
    assert np.min(distances[dedans]) < 0.4 + 1e-6  # de vrais contacts ont eu lieu


def test_petit_groupe_passe_le_goulot_une_fois_chacun(petit_groupe):
    r = petit_groupe
    assert np.all(np.isfinite(r.passages))
    assert np.all(r.x[-1, :, 0] >= r.parametres.longueur + r.parametres.longueur_goulot)
    assert r.t[-1] < r.parametres.duree  # arret des que tous sont sortis
    assert np.isfinite(r.debit_specifique) and r.debit_specifique > 0.0


def test_meme_graine_meme_simulation():
    p = parametres(n_agents=6, duree=3.0, bruit_direction=0.2)
    a, b = simuler_goulot(p), simuler_goulot(p)
    np.testing.assert_array_equal(a.x, b.x)


def test_commande_etalonner_affiche_le_debit_et_la_reference(tmp_path, capsys):
    config = yaml.safe_load(EXEMPLE.read_text(encoding="utf-8"))
    config["parametres"] |= {"n_agents": 8, "duree": 15.0}
    fichier = tmp_path / "goulot.yaml"
    fichier.write_text(yaml.safe_dump(config), encoding="utf-8")
    assert main(["etalonner-goulot", str(fichier), "--largeurs", "1.2", "--graines", "1"]) == 0
    ligne = next(ligne for ligne in capsys.readouterr().out.splitlines() if "1.20" in ligne)
    assert ligne.split()[1] == "0/1" and ligne.split()[-1] == "1.97"


def test_commande_etalonner_refuse_un_autre_scenario(capsys):
    racine = Path(__file__).parents[1]
    assert main(["etalonner-goulot", str(racine / "experiments/couloir.yaml")]) == 1
    assert "goulot" in capsys.readouterr().err


def test_simuler_refuse_le_banc_goulot_sans_archive(tmp_path, capsys):
    assert main(["simuler", str(EXEMPLE), "--sortie", str(tmp_path / "e0.npz")]) == 1
    assert "etalonner-goulot" in capsys.readouterr().err
    assert not (tmp_path / "e0.npz").exists()
