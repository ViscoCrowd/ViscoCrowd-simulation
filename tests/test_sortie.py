"""Evacuation definitive (#11) : une sortie n'est pas un passage."""

from pathlib import Path

import numpy as np
import pytest

from viscocrowd.io.configuration import lire_configuration
from viscocrowd.observables.debit import debit_specifique, franchissements
from viscocrowd.observables.sortie import Sorties, sorties_definitives
from viscocrowd.scenarios.couloir import ParametresCouloir, simuler_couloir

# Porte verticale en x = 0, de (0, -1) a (0, 1) : en marchant de a vers b (vers
# le haut), la gauche est x < 0 (l'interieur) et la droite x > 0 (l'exterieur).
A = np.array([0.0, -1.0])
B = np.array([0.0, 1.0])


def trajectoire(*abscisses, ordonnee=0.0, dt=0.1):
    """Un agent par liste d'abscisses successives, tous a la meme ordonnee."""
    x = np.zeros((len(abscisses[0]), len(abscisses), 2))
    x[..., 0] = np.array(abscisses).T
    x[..., 1] = ordonnee
    return dt * np.arange(x.shape[0]), x


def test_traverse_revient_retraverse_compte_une_seule_sortie():
    """Le cas qui distingue les deux observables : 3 passages, flux net 1, 1 sortie."""
    t, x = trajectoire([-1.0, 1.0, -1.0, 1.0, 2.0])
    passages = franchissements(t, x, A, B)
    sorties = sorties_definitives(t, x, A, B)

    assert passages.nombre == 3
    assert debit_specifique(passages, 2.0, 0.0, 1.0) * 1.0 * 2.0 == pytest.approx(1.0)
    assert sorties.nombre_sortis(t[-1]) == 1
    assert sorties.instant[0] == pytest.approx(0.25)  # le troisieme passage, interpole


def test_ressorti_puis_rentre_n_est_pas_sorti():
    t, x = trajectoire([-1.0, 1.0, -1.0, -2.0])
    assert sorties_definitives(t, x, A, B).nombre_sortis(t[-1]) == 0


def test_passer_a_cote_de_la_porte_n_est_pas_sortir():
    t, x = trajectoire([-1.0, 1.0, 2.0], ordonnee=3.0)
    assert np.isnan(sorties_definitives(t, x, A, B).instant[0])


def test_retour_hors_porte_annule_la_sortie_anterieure():
    x = np.array([[[-1.0, 0.0]], [[1.0, 0.0]], [[1.0, 3.0]], [[-1.0, 3.0]], [[1.0, 3.0]]])
    sorties = sorties_definitives(np.arange(5.0), x, A, B)
    assert not sorties.sortis.any()


def test_retour_hors_porte_puis_vraie_sortie_retenue():
    x = np.array(
        [[[-1.0, 0.0]], [[1.0, 0.0]], [[1.0, 3.0]], [[-1.0, 3.0]], [[-1.0, 0.0]], [[1.0, 0.0]]]
    )
    sorties = sorties_definitives(np.arange(6.0), x, A, B)
    assert sorties.instant[0] == pytest.approx(4.5)


@pytest.mark.parametrize(
    "instants", [[2.0, 1.0, 0.0], [0.0, 0.0, 1.0], [0.0, np.nan, 2.0], [0.0, 1.0, np.inf]]
)
def test_instants_invalides_refuses(instants):
    _, x = trajectoire([-1.0, 1.0, 2.0])
    with pytest.raises(ValueError):
        sorties_definitives(np.array(instants), x, A, B)


def test_position_non_finie_refusee():
    t, x = trajectoire([-1.0, np.nan, 2.0])
    with pytest.raises(ValueError):
        sorties_definitives(t, x, A, B)


def test_requete_de_compte_non_finie_refusee():
    with pytest.raises(ValueError):
        Sorties(np.array([1.0, 2.0])).nombre_sortis(np.nan)


def test_fraction_juste_superieure_exige_bien_un_agent_de_plus():
    assert Sorties(np.arange(1.0, 11.0)).temps_evacuation(0.5 + 1e-11) == 6.0


def test_jamais_sorti_et_deja_dehors():
    """Rester dedans ou demarrer dehors sans franchir la porte : aucune sortie."""
    t, x = trajectoire([-2.0, -1.0, -0.5], [1.0, 2.0, 3.0])
    sorties = sorties_definitives(t, x, A, B)
    assert not sorties.sortis.any()
    assert sorties.temps_evacuation() == np.inf


@pytest.mark.invariant
def test_compte_monotone_borne_et_conservatif():
    """Agents aleatoires qui oscillent autour de la porte : invariants a chaque instant."""
    rng = np.random.default_rng(11)
    pas = rng.normal(0.05, 0.3, size=(400, 50))
    x = np.zeros((400, 50, 2))
    x[..., 0] = -1.0 + np.cumsum(pas, axis=0)
    x[..., 1] = rng.uniform(-0.9, 0.9, size=50)
    t = 0.1 * np.arange(400)
    sorties = sorties_definitives(t, x, A, B)
    n = sorties.nombre_sortis(t)

    assert np.all(np.diff(n) >= 0)
    assert n[-1] <= 50
    assert n[-1] == sorties.sortis.sum()
    non_classes_sortis = np.array([np.sum(~(sorties.instant <= ti)) for ti in t])
    np.testing.assert_array_equal(non_classes_sortis + n, 50)
    # Un agent compte sorti a un instant est dehors a tous les instants suivants
    # (ou exactement sur la droite) : sinon il serait revenu.
    for i in np.flatnonzero(sorties.sortis):
        apres = t > sorties.instant[i]
        assert np.all(x[apres, i, 0] >= 0.0)
    # Il y a eu des refoulements : plus de passages que de sortants.
    assert franchissements(t, x, A, B).nombre > n[-1]


def test_non_sortis_definitivement_ne_signifie_pas_dedans():
    t, x = trajectoire([-1.0, 1.0, -1.0, 1.0])
    sorties = sorties_definitives(t, x, A, B)
    assert x[1, 0, 0] > 0.0  # dehors geometriquement, mais il reviendra
    assert sorties.nombre_sortis(t[1]) == 0


def test_temps_d_evacuation_et_quantiles():
    sorties = Sorties(np.array([3.0, 1.0, np.nan, 2.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0]))
    assert sorties.temps_evacuation(0.5) == 5.0  # 5 agents sur 10
    assert sorties.temps_evacuation(0.9) == 9.0  # 9 sur 10, sans erreur d'arrondi
    assert sorties.temps_evacuation(1.0) == np.inf  # un agent n'est jamais sorti
    assert sorties.temps_evacuation(0.1) == 1.0
    np.testing.assert_array_equal(sorties.nombre_sortis([0.0, 1.0, 2.5, 100.0]), [0, 1, 2, 9])


@pytest.mark.parametrize("fraction", [0.0, -0.1, 1.5, np.nan])
def test_fraction_invalide(fraction):
    with pytest.raises(ValueError):
        Sorties(np.array([1.0])).temps_evacuation(fraction)


def test_formes_invalides():
    with pytest.raises(ValueError):
        sorties_definitives(np.arange(3.0), np.zeros((3, 2)), A, B)
    with pytest.raises(ValueError):
        sorties_definitives(np.arange(2.0), np.zeros((3, 1, 2)), A, B)


def test_couloir_sans_blocage_tous_sortis_une_fois():
    """Banc G1/G5 : 24 agents, aucun refoulement, donc sorties = passages."""
    config = lire_configuration(Path(__file__).parents[1] / "experiments/couloir.yaml")
    r = simuler_couloir(ParametresCouloir(**config["parametres"], graine=config["graine"]))
    a, b = r.domaine.section_sortie  # deja orientee : sortie vers +x, de gauche a droite
    sorties = sorties_definitives(r.t, r.x, a, b)
    passages = franchissements(r.t, r.x, a, b)

    assert sorties.nombre_sortis(r.t[-1]) == 24
    np.testing.assert_allclose(np.sort(sorties.instant), np.sort(passages.instant))
    assert sorties.temps_evacuation() == pytest.approx(9.228, abs=1e-3)  # journal du 21/10
