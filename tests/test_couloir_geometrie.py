"""Projection du couloir, frontieres des milieux et contrat du guidage G1."""

import numpy as np
import pytest

from viscocrowd.core.integrator import pas_semi_implicite
from viscocrowd.core.state import State
from viscocrowd.geometry.couloir import Couloir
from viscocrowd.model.carte import CarteBandes
from viscocrowd.model.guidage import direction_aval
from viscocrowd.model.milieu import Milieu
from viscocrowd.observables.debit import franchissements


@pytest.mark.invariant
def test_projection_corners_et_rayons_differents():
    domaine = Couloir(10.0, 2.0)
    x = np.array([[-2.0, -4.0], [-3.0, 2.0], [12.0, 0.0]])
    r = np.array([0.1, 0.4, 0.3])
    obtenu = domaine.projeter(x, r, 0.0)
    np.testing.assert_allclose(obtenu, [[0.1, -0.9], [0.4, 0.6], [12.0, 0.0]])
    np.testing.assert_array_equal(domaine.projeter(obtenu, r, 0.0), obtenu)
    assert domaine.violation(obtenu, r, 0.0) <= 1e-15
    assert x[0, 0] == -2.0  # aucune mutation de l'entree


@pytest.mark.invariant
def test_choc_mou_sur_paroi_laterale():
    domaine = Couloir(10.0, 2.0)
    etat = State.single((0.5, 0.8), vitesse=(1.0, 4.0), rayon=0.2)
    libre = lambda e, dt: e.v  # noqa: E731
    suivant = pas_semi_implicite(etat, 0.1, libre, domaine.projeter)
    np.testing.assert_allclose(suivant.v, [[1.0, 0.0]], atol=1e-14)
    assert domaine.violation(suivant.x, suivant.r, suivant.t) <= 1e-15


def test_sortie_ouverte_et_segment_oriente():
    domaine = Couloir(1.0, 2.0)
    x = np.array([[[0.8, 0.0]], [[1.2, 0.0]]])
    np.testing.assert_array_equal(domaine.projeter(x[-1], [0.1], 1.0), x[-1])
    passages = franchissements(np.array([0.0, 1.0]), x, *domaine.section_sortie)
    assert passages.nombre == 1
    assert passages.sens[0] == 1
    assert passages.instant[0] == pytest.approx(0.5)


@pytest.mark.parametrize("largeur", [0.0, -1.0, np.nan, np.inf])
def test_dimensions_invalides(largeur):
    with pytest.raises(ValueError):
        Couloir(1.0, largeur)


@pytest.mark.parametrize("r", [[0.0], [1.1], [np.nan], [0.1, 0.2]])
def test_disques_invalides(r):
    with pytest.raises(ValueError):
        Couloir(10.0, 2.0).projeter([[0.0, 0.0]], r, 0.0)


def test_frontieres_et_extremites_de_la_carte():
    carte = CarteBandes((2.0, 4.0), (Milieu.SEC, Milieu.MOUILLE, Milieu.EAU))
    obtenu = carte(
        np.array([[-1.0, 0.0], [2.0 - 1e-10, 3.0], [2.0, 0.0], [4.0, 0.0], [100.0, 0.0]])
    )
    np.testing.assert_array_equal(obtenu, [2, 2, 1, 0, 0])
    assert np.issubdtype(obtenu.dtype, np.integer)


def test_carte_uniforme_et_copie_des_parametres():
    frontieres, milieux = [], [Milieu.SEC]
    carte = CarteBandes(frontieres, milieux)
    milieux[0] = Milieu.EAU
    np.testing.assert_array_equal(carte([[3.0, 0.0]]), [Milieu.SEC])
    assert carte(np.empty((0, 2))).shape == (0,)


@pytest.mark.parametrize(
    ("frontieres", "milieux"),
    [
        ([2.0, 1.0], [0, 1, 2]),
        ([1.0, 1.0], [0, 1, 2]),
        ([np.nan], [0, 1]),
        ([1.0], [0]),
        ([], [42]),
    ],
)
def test_carte_invalide(frontieres, milieux):
    with pytest.raises(ValueError):
        CarteBandes(frontieres, milieux)


def test_direction_unitaire_avant_et_apres_sortie():
    etat = State(x=np.array([[1.0, 0.0], [15.0, 0.0]]), v=np.zeros((2, 2)), r=np.ones(2) * 0.2)
    np.testing.assert_array_equal(direction_aval(etat), [[1.0, 0.0], [1.0, 0.0]])
