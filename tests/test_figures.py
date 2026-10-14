"""Ce que les figures AFFIRMENT, teste independamment de leur trace.

Une figure peut etre jolie et fausse. Les tests ci-dessous portent sur les
grandeurs qu'elle publie, pas sur le fichier PNG : si le schema perd son ordre
de convergence, c'est ici que ca doit casser, pas a la relecture d'une image.

La production des fichiers est exercee de bout en bout par le job
« Reproductibilite des figures » de la CI, et par le test marque `slow`.
"""

from itertools import pairwise

import numpy as np
import pytest

from viscocrowd.core.state import GRAVITE
from viscocrowd.viz.figures import (
    CONVERGENCE_DT,
    TOUTES_LES_FIGURES,
    _erreur_chute_libre,
    figure_convergence_dt,
    figure_tassement,
)


class TestOrdreDuSchema:
    """L'affirmation portee par le panneau gauche de la figure 6.

    Le schema semi-implicite a sa propre solution fermee, exacte au bit pres :
    c'est ce que verifie `test_integrator`. Ici on mesure autre chose, l'ecart a
    la solution du probleme CONTINU, c'est-a-dire l'erreur de discretisation.

    Elle vaut analytiquement |g| t dt / 2 : la position discrete apres n pas vaut
    x0 + n dt v0 + dt^2 g n(n+1)/2, la continue x0 + v0 t + g t^2/2, et leur
    difference se reduit a g t dt / 2 avec t = n dt. Donc l'ordre 1, et une
    erreur PREDITE, pas seulement bornee.
    """

    @pytest.mark.parametrize("dt", CONVERGENCE_DT)
    def test_l_erreur_vaut_exactement_la_prediction_analytique(self, dt):
        attendu = abs(GRAVITE[1]) * 1.0 * dt / 2.0

        mesure = _erreur_chute_libre(dt, duree=1.0)

        assert mesure == pytest.approx(attendu, rel=1e-9), (
            f"dt = {dt:.1e} s : mesure {mesure:.6e} m, analytique {attendu:.6e} m"
        )

    def test_l_ordre_mesure_vaut_un(self):
        """Halver le pas de temps doit halver l'erreur, pas autre chose."""
        dts = np.array(CONVERGENCE_DT)
        erreurs = np.array([_erreur_chute_libre(float(dt)) for dt in dts])

        pente = float(np.polyfit(np.log(dts), np.log(erreurs), 1)[0])

        assert pente == pytest.approx(1.0, abs=1e-6), f"ordre mesure {pente:.4f}"

    @pytest.mark.parametrize("dt", [3e-3, 7e-4, 1.1e-3])
    def test_un_pas_qui_ne_divise_pas_la_duree_reste_juste(self, dt):
        """`simuler` fait `ceil(duree / dt)` pas : la trajectoire depasse la duree.

        La solution exacte doit donc etre evaluee a l'instant REELLEMENT atteint.
        Comparer a la duree demandee mesurait le decalage de dates et non
        l'erreur du schema : a dt = 3 ms, 3,4e-2 m au lieu de 1,5e-2 m.
        """
        n_pas = int(np.ceil(1.0 / dt))
        t_reel = n_pas * dt
        attendu = abs(GRAVITE[1]) * t_reel * dt / 2.0

        assert _erreur_chute_libre(dt, duree=1.0) == pytest.approx(attendu, rel=1e-9)

    def test_l_erreur_decroit_strictement_avec_le_pas(self):
        """Garde-fou : une erreur qui stagnerait signalerait un plancher numerique."""
        erreurs = [_erreur_chute_libre(float(dt)) for dt in sorted(CONVERGENCE_DT)]

        assert all(a < b for a, b in pairwise(erreurs))


class TestCatalogue:
    def test_les_deux_figures_du_jalon_2_sont_enregistrees(self):
        """Une figure absente du catalogue ne serait jamais produite par la CI."""
        assert figure_tassement in TOUTES_LES_FIGURES
        assert figure_convergence_dt in TOUTES_LES_FIGURES

    def test_chaque_figure_porte_un_identifiant_distinct(self):
        noms = [fabrique.__name__ for fabrique in TOUTES_LES_FIGURES]

        assert len(noms) == len(set(noms))


@pytest.mark.slow
class TestProduction:
    """Trop lent pour la CI des PR : les deux figures rejouent des simulations."""

    @pytest.mark.parametrize("fabrique", [figure_tassement, figure_convergence_dt])
    def test_la_figure_est_produite_et_non_vide(self, fabrique, tmp_path):
        chemin = fabrique(tmp_path)

        assert chemin.exists()
        assert chemin.suffix == ".png"
        assert chemin.stat().st_size > 10_000  # une image vide pese quelques centaines d'octets
