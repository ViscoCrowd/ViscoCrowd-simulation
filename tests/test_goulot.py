"""Banc E0 : salle et goulot, etat initial du protocole de Seyfried et al. (2009), debit."""

import types
from pathlib import Path

import numpy as np
import pytest
import yaml

from viscocrowd.cli import main
from viscocrowd.core.state import State
from viscocrowd.geometry.salle import SalleGoulot
from viscocrowd.io.configuration import lire_configuration
from viscocrowd.scenarios.goulot import (
    STATUTS,
    ParametresGoulot,
    ResultatGoulot,
    champ_goulot,
    debit_central,
    debit_seyfried,
    etalonner,
    reference_seyfried,
    simuler_goulot,
    tirages_initiaux,
)

EXEMPLE = Path(__file__).parents[1] / "experiments/goulot.yaml"
SALLE = SalleGoulot(longueur=8.0, largeur=5.0, largeur_goulot=1.0, longueur_goulot=2.8)
R = 0.2


def parametres(**changements):
    config = lire_configuration(EXEMPLE)
    graine = changements.pop("graine", config["graine"])
    return ParametresGoulot(**(config["parametres"] | changements), graine=graine)


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


@pytest.mark.parametrize(("n_agents", "reference"), [(8, "-"), (20, "2.31")])
def test_commande_etalonner_affiche_regimes_et_reference_du_meme_n(
    tmp_path, capsys, n_agents, reference
):
    """La reference de Seyfried n'est affichee que pour le N qu'il a mesure."""
    config = yaml.safe_load(EXEMPLE.read_text(encoding="utf-8"))
    config["parametres"] |= {"n_agents": n_agents, "duree": 25.0}
    fichier = tmp_path / "goulot.yaml"
    fichier.write_text(yaml.safe_dump(config), encoding="utf-8")
    assert main(["etalonner-goulot", str(fichier), "--largeurs", "1.2", "--graines", "1"]) == 0
    sortie = capsys.readouterr().out
    ligne = next(ligne for ligne in sortie.splitlines() if ligne.split()[:1] == ["1.20"])
    assert ligne.split()[1] == "1/0/0/0" and ligne.split()[-1] == reference
    assert f"Seyfried N={n_agents}" in sortie


def test_commande_etalonner_refuse_un_autre_scenario(capsys):
    racine = Path(__file__).parents[1]
    assert main(["etalonner-goulot", str(racine / "experiments/couloir.yaml")]) == 1
    assert "goulot" in capsys.readouterr().err


def test_simuler_refuse_le_banc_goulot_sans_archive(tmp_path, capsys):
    assert main(["simuler", str(EXEMPLE), "--sortie", str(tmp_path / "e0.npz")]) == 1
    assert "etalonner-goulot" in capsys.readouterr().err
    assert not (tmp_path / "e0.npz").exists()


@pytest.mark.parametrize("doublon", [{"largeurs": [1.0, 1.0]}, {"graines": [4, 4]}])
def test_etalonner_refuse_les_doublons(doublon):
    """Une meme simulation comptee deux fois fausserait moyenne et ecart-type."""
    arguments = {"largeurs": [1.0], "graines": [1]} | doublon
    with pytest.raises(ValueError, match="distinctes"):
        etalonner(lire_configuration(EXEMPLE), **arguments)


def test_etalonner_calcule_le_guidage_une_fois_par_largeur(monkeypatch):
    import viscocrowd.scenarios.goulot as module

    appels = []
    vrai = module.champ_goulot
    monkeypatch.setattr(module, "champ_goulot", lambda p: appels.append(p) or vrai(p))
    config = lire_configuration(EXEMPLE)
    config["parametres"] |= {"n_agents": 4, "duree": 2.0}
    resultats = etalonner(config, [1.0, 1.2], [1, 2, 3])
    assert len(appels) == 2
    assert [m.graine for m in resultats[1.2]] == [1, 2, 3]


class TestStatut:
    """Chaque regime est classe a part ; seul l'ecoulement donne un debit."""

    def resultat(self, passages, non_convergences=0):
        projection = types.SimpleNamespace(non_convergences=non_convergences)
        passages = np.array(passages, dtype=float)
        return ResultatGoulot(
            t=np.zeros(1),
            x=np.zeros((1, passages.size, 2)),
            rayons=np.full(passages.size, 0.2),
            passages=passages,
            debit_specifique=debit_seyfried(passages, 1.0),
            debit_central=debit_central(passages, 1.0),
            projection=projection,
            parametres=None,
        )

    def test_regimes(self):
        assert self.resultat(np.arange(10) * 0.5).statut == "ecoulement"
        assert self.resultat([*range(9), np.nan]).statut == "bouchage"
        assert self.resultat([1.0]).statut == "insuffisant"  # tous passes, un seul passage
        assert self.resultat([2.0, 2.0]).statut == "insuffisant"  # aucun intervalle
        assert self.resultat(np.arange(10) * 0.5, 1).statut == "non_convergence"
        assert set(STATUTS) == {"ecoulement", "bouchage", "insuffisant", "non_convergence"}

    def test_non_convergence_ne_leve_plus(self):
        """Projection permissive : la campagne continue et classe la simulation a part."""
        p = parametres(n_agents=12, duree=3.0, tolerance=1e-15)
        r = simuler_goulot(p)
        assert r.projection.non_convergences > 0
        assert r.statut == "non_convergence"


def test_references_de_seyfried_par_nombre_de_personnes():
    assert reference_seyfried(40, 1.0) == 2.08
    assert reference_seyfried(60, 1.2) == 1.97
    assert reference_seyfried(50, 1.0) is None
    assert reference_seyfried(60, 0.85) is None


def test_foule_initiale_symetrique_par_rapport_a_l_axe():
    """Un tri stable sur x seul prenait toujours les rangees basses en premier."""
    for n in (59, 60, 61):
        p = parametres(n_agents=n, bruit=0.0)
        x, _, _ = tirages_initiaux(p)
        miroir = x * [1.0, -1.0] + [0.0, p.largeur]
        cles = {tuple(np.round(point, 9)) for point in x}
        sans_image = sum(tuple(np.round(point, 9)) not in cles for point in miroir)
        assert sans_image <= 1, f"N = {n}"


def test_petit_agent_contre_un_mur_a_une_direction():
    """Masque du guidage au plus petit rayon : un agent de 0,18 m colle au mur avance."""
    p = parametres(dispersion_rayon=0.1)
    etat = State(
        x=np.array([[2.0, 0.181], [4.0, 4.819]]), v=np.zeros((2, 2)), r=np.full(2, 0.18), t=0.0
    )
    e = champ_goulot(p)(etat)
    assert np.all(np.isfinite(e)) and np.all(np.hypot(*e.T) > 0.99)


class TestEstimateurSeyfried:
    """La comparaison E0 utilise l'estimateur du tableau 2 de Seyfried et al. (2009)."""

    def test_premier_au_dernier_passage_et_delta_n_egal_a_n(self):
        """Delta N = N (colonnes du tableau 2), Delta t du premier au dernier passage."""
        passages = np.arange(20) * 0.5  # 20 personnes, 19 intervalles de 0,5 s
        assert debit_seyfried(passages, 1.0) == pytest.approx(20 / 9.5)
        assert debit_seyfried(passages, 0.8) == pytest.approx(20 / 9.5 / 0.8)

    def test_differe_du_debit_central_quand_la_cadence_varie(self):
        """Dix passages reguliers puis un retardataire : les deux mesures divergent."""
        passages = np.append(np.arange(10) * 0.5, 20.0)
        assert debit_seyfried(passages, 1.0) == pytest.approx(11 / 20.0)
        assert debit_central(passages, 1.0) == pytest.approx(8 / 4.0)

    def test_trop_peu_de_passages(self):
        assert np.isnan(debit_seyfried(np.array([1.0, np.nan]), 1.0))
        assert np.isnan(debit_seyfried(np.array([2.0, 2.0]), 1.0))


class TestBruitInitial:
    """Le bruit est tire en 2D : la borne doit valoir pour des voisins obliques."""

    def test_cas_de_la_revue_refuse(self):
        """Graine 5, bruit 0,09 m : 3,3 cm de recouvrement initial avec l'ancienne borne."""
        with pytest.raises(ValueError, match="recouvrent"):
            parametres(bruit=0.09, graine=5)

    def test_bruit_admis_jamais_de_recouvrement(self):
        p = parametres()
        limite = (p.pas_reseau - 2 * p.rayon_max) / (2 * np.sqrt(2))
        for graine in range(30):
            q = parametres(bruit=float(round(limite - 1e-3, 6)), graine=graine)
            x, r, _ = tirages_initiaux(q)
            i, j = np.triu_indices(x.shape[0], 1)
            jeu = np.linalg.norm(x[i] - x[j], axis=1) - r[i] - r[j]
            assert np.min(jeu) >= 0.0, f"graine {graine}"
