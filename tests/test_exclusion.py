"""Invariants physiques de l'exclusion entre agents, sur le scenario de tassement.

36 disques tombent dans une boite fixe et s'empilent au fond. Comme pour la bille,
chaque test produit un NOMBRE compare a un seuil JUSTIFIE, pas une impression.
"""

import numpy as np
import pytest

from viscocrowd.geometry.grille import recouvrement_max
from viscocrowd.observables.energie import energie_mecanique
from viscocrowd.scenarios.tassement import (
    ParametresTassement,
    positions_initiales,
    simuler_tassement,
)

TOLERANCE = 1e-6  # recouvrement residuel accepte, m
PRECISION_PAROI = 1e-14  # m : seules les erreurs d'arrondi doivent subsister


def _simuler(dt):
    return simuler_tassement(
        ParametresTassement(n_agents=36, duree=3.0, dt=dt, graine=1, tolerance=TOLERANCE)
    )


@pytest.fixture(scope="module")
def resultat():
    return _simuler(2e-3)


@pytest.fixture(scope="module")
def resultat_pas_double():
    return _simuler(4e-3)


@pytest.mark.invariant
class TestNonInterpenetration:
    def test_etat_initial_admissible(self):
        """Le depart est sans recouvrement : tout recouvrement vient donc du schema."""

        p = ParametresTassement(n_agents=36, graine=1)
        assert recouvrement_max(positions_initiales(p), np.full(36, p.rayon)) == 0.0

    def test_recouvrement_residuel_sous_la_tolerance(self, resultat):
        """Indicateur de validation n_1 : un nombre, rapporte au rayon des agents."""
        recouvrement = resultat.recouvrement_max()
        assert recouvrement <= TOLERANCE, (
            f"recouvrement residuel {recouvrement:.3e} m "
            f"({recouvrement / resultat.parametres.rayon:.1e} rayon)"
        )

    def test_la_projection_converge_toujours(self, resultat):
        proj = resultat.projection
        assert proj.non_convergences == 0, (
            f"{proj.non_convergences} projections sur {proj.n_appels} n'ont pas converge "
            f"(recouvrement maximal {proj.recouvrement_max:.3e} m)"
        )


@pytest.mark.invariant
class TestParois:
    def test_aucun_disque_ne_sort_de_la_boite(self, resultat):
        """Le domaine est reprojete en dernier a chaque balayage : respect exact."""
        assert resultat.violation_paroi_max() < PRECISION_PAROI


@pytest.mark.invariant
class TestConservation:
    def test_aucun_agent_perdu_ni_valeur_aberrante(self, resultat):
        n = resultat.parametres.n_agents
        assert resultat.x.shape[1] == n
        assert np.all(np.isfinite(resultat.x))
        assert np.all(np.isfinite(resultat.v))


@pytest.mark.invariant
class TestEnergie:
    def test_pas_de_creation_d_energie(self, resultat):
        """Le choc mou dissipe : l'energie mecanique ne doit pas croitre.

        Une correction qui repousserait un disque de plus que le recouvrement
        (sur-relaxation) lui donnerait un rebond artificiel et ferait remonter
        l'energie. On tolere une remontee de 10^-4 de l'energie dissipee par pas,
        et 1 % cumule : ce sont les effets de la tolerance de projection, mesures
        a 3·10^-5 et 3·10^-3 sur ce scenario.
        """
        energie = energie_mecanique(resultat.x, resultat.v)
        dissipee = energie[0] - energie[-1]
        assert dissipee > 100.0, f"dissipation negligeable : {dissipee:.3e} J"

        variations = np.diff(energie)
        assert variations.max() < 1e-4 * dissipee, (
            f"remontee de {variations.max():.3e} J en un pas ({dissipee:.1f} J dissipes)"
        )
        assert variations[variations > 0].sum() < 1e-2 * dissipee

    def test_le_tas_finit_au_repos(self, resultat):
        """Sans ce test, une projection qui gelerait le systeme passerait les precedents."""
        assert resultat.energie_cinetique()[-1] < 1e-3, (
            f"energie cinetique finale {resultat.energie_cinetique()[-1]:.3e} J"
        )

    def test_les_disques_sont_tombes_au_fond(self, resultat):
        y0 = resultat.x[0, :, 1].mean()
        y_fin = resultat.x[-1, :, 1].mean()
        assert y0 - y_fin > 1.0, f"chute de {y0 - y_fin:.3f} m seulement"
        # Aucun disque ne reste en suspension dans la moitie haute.
        assert resultat.x[-1, :, 1].max() < 0.0


@pytest.mark.invariant
def test_stabilite_en_pas_de_temps(resultat, resultat_pas_double):
    """Sensibilite a dt (point 4 de la validation) : la hauteur du tas ne depend pas de dt.

    Les chocs sont discontinus : on ne compare pas les trajectoires disque a disque
    mais une grandeur d'ensemble, la hauteur moyenne finale du tas.
    """
    ecart = abs(resultat.x[-1, :, 1].mean() - resultat_pas_double.x[-1, :, 1].mean())
    assert ecart < 0.02, f"hauteur finale : ecart de {ecart:.4f} m entre dt et 2 dt"
