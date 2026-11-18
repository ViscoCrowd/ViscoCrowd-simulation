"""Temps de reaction dans la piscine : personne ne bouge ni ne franchit avant le sien."""

import numpy as np
import pytest

from utilitaires import parametres_reduits
from viscocrowd.scenarios.piscine import EAU, FRANCHISSEMENT, positions_initiales, simuler_piscine

SIMULTANE_TARDIF = {"mediane": 20.0, "dispersion": 0.0}  # personne ne part avant 20 s


def test_sans_reaction_identique_au_bit_pres():
    a = simuler_piscine(parametres_reduits())
    b = simuler_piscine(parametres_reduits(reaction=None))
    np.testing.assert_array_equal(a.x, b.x)
    np.testing.assert_array_equal(a.etats, b.etats)
    assert a.reactions is None


def test_personne_ne_bouge_avant_sa_reaction():
    r = simuler_piscine(parametres_reduits(reaction={"mediane": 3.0, "dispersion": 0.0}, duree=2.5))
    assert np.max(np.abs(r.x - r.x[0])) < 1e-12
    np.testing.assert_array_equal(r.reactions, np.full(6, 3.0))


def test_personne_ne_franchit_ni_n_est_debloque_avant_sa_reaction():
    """Bassin plein : sans reaction, des nageurs poses pres du bord franchissent tout de suite."""
    temoin = simuler_piscine(parametres_reduits(n_agents=300, duree=5.0))
    assert np.any(temoin.etats == FRANCHISSEMENT)  # le cas teste existe bien
    r = simuler_piscine(parametres_reduits(n_agents=300, duree=5.0, reaction=SIMULTANE_TARDIF))
    assert np.all(r.etats == EAU)
    assert r.deblocages == 0 and len(r.franchissements) == 0


def test_les_agents_partent_apres_leur_reaction():
    r = simuler_piscine(parametres_reduits(reaction={"mediane": 1.0, "dispersion": 0.0}, duree=3.0))
    assert np.max(np.hypot(*(r.x[-1] - r.x[0]).T)) > 0.1


def test_positions_initiales_inchangees_par_la_reaction():
    np.testing.assert_array_equal(
        positions_initiales(parametres_reduits()),
        positions_initiales(parametres_reduits(reaction={"mediane": 5.0, "dispersion": 0.5})),
    )


@pytest.mark.parametrize(
    "reaction",
    [{"mediane": 5.0}, {"mediane": 0.0, "dispersion": 0.5}, {"mediane": 5.0, "dispersion": -1}],
)
def test_reaction_mal_formee_refusee(reaction):
    with pytest.raises(ValueError, match="reaction"):
        parametres_reduits(reaction=reaction)


def test_reaction_ecrite_dans_le_dictionnaire():
    p = parametres_reduits(reaction={"mediane": 5.0, "dispersion": 0.5})
    assert p.en_dictionnaire()["reaction"] == {"mediane": 5.0, "dispersion": 0.5}
