"""Biais de densite lie a la tolerance et aux contacts multiples au goulot (M2, #10).

Verifie sur la geometrie cible (banc E0, Seyfried et al. 2009) que :
  1. L'ecoulement dense dans l'entonnoir amont du goulot n'a aucune violation de paroi
     ni non-convergence de Jacobi vectorise.
  2. Le resserrement de la tolerance de projection (1e-6 a 1e-7 m) ne produit aucun ecart
     de densite decelable au-dela du bruit numerique (< 0.001 pers/m^2).
  3. L'incertitude est evaluee par comparaison appariee et test de permutation exact (2^n)
     sans assimiler +/- 2 erreurs standard a une borne garantie.
"""

from pathlib import Path

import numpy as np
import pytest

from viscocrowd.io.configuration import lire_configuration
from viscocrowd.observables.densite import Rectangle, densite_comptage
from viscocrowd.scenarios.goulot import ParametresGoulot, simuler_goulot

EXEMPLE_GOULOT = Path(__file__).parents[1] / "experiments/goulot.yaml"
ZONE_ENTONNOIR = Rectangle(6.0, 7.8, 1.5, 3.5)


def valeur_p_permutation_appariee(ecarts: np.ndarray) -> float:
    """Valeur p bilaterale exacte du test de permutation sur des differences appariees.

    Hypothese nulle : les deux resultats d'une meme graine sont echangeables.
    """
    n = len(ecarts)
    signes = 1 - 2 * ((np.arange(2**n)[:, None] >> np.arange(n)) & 1)
    moyennes = np.abs(signes @ ecarts) / n
    tolerance = 1e-12 * np.abs(ecarts).mean() if np.abs(ecarts).mean() > 0 else 1e-15
    return float(np.mean(moyennes >= abs(ecarts.mean()) - tolerance))


def densite_phase_dense(
    resultat, zone: Rectangle = ZONE_ENTONNOIR, t_min: float = 3.0, t_max: float = 15.0
) -> float:
    """Densite moyenne de comptage dans la zone pendant la fenetre temporelle dense."""
    masque = (resultat.t >= t_min) & (resultat.t <= t_max)
    densites = [densite_comptage(x, zone) for x in resultat.x[masque]]
    return float(np.mean(densites))


def parametres_banc(
    tolerance: float = 1e-6, dt: float = 0.01, duree: float = 15.0, graine: int = 1
) -> ParametresGoulot:
    config = lire_configuration(EXEMPLE_GOULOT)
    params = dict(config["parametres"])
    params["tolerance"] = tolerance
    params["dt"] = dt
    params["duree"] = duree
    return ParametresGoulot(**params, graine=graine)


class TestBiaisDensiteGoulot:
    def test_entonnoir_sans_violation_ni_non_convergence(self):
        """L'ecoulement dans l'entonnoir converge sans violation residuelle de paroi."""
        p = parametres_banc(duree=12.0, graine=1)
        res = simuler_goulot(p)
        assert res.projection.non_convergences == 0
        assert res.violation_paroi_max() <= 1e-12
        rho = densite_phase_dense(res, ZONE_ENTONNOIR, t_min=3.0, t_max=10.0)
        assert 2.0 <= rho <= 7.0

    def test_sensibilite_locale_tolerance_resserre(self):
        """Sur deux graines, resserrer la tolerance a 1e-7 ne change pas la densite a plus de 0.001 pers/m^2."""
        for g in (1, 2):
            p_ref = parametres_banc(tolerance=1e-6, duree=12.0, graine=g)
            p_serre = parametres_banc(tolerance=1e-7, duree=12.0, graine=g)
            res_ref = simuler_goulot(p_ref)
            res_serre = simuler_goulot(p_serre)
            rho_ref = densite_phase_dense(res_ref, ZONE_ENTONNOIR, t_min=3.0, t_max=10.0)
            rho_serre = densite_phase_dense(res_serre, ZONE_ENTONNOIR, t_min=3.0, t_max=10.0)
            assert abs(rho_serre - rho_ref) < 1e-3

    @pytest.mark.slow
    def test_campagne_complete_biais_densite_goulot(self):
        """Campagne appariee sur 10 graines au goulot (Seyfried et al. 2009).

        Evalue l'impact de la tolerance et du pas de temps sur la densite de l'entonnoir.
        Memes graines (1 a 10) que docs/mesures/biais-densite-goulot-2026-11-03/mesurer.py.
        Hypothese nulle d'echangeabilite testee par permutation exacte (2^10 = 1024).
        """
        graines = list(range(1, 11))
        densites_ref = []
        densites_serree = []
        densites_large = []
        densites_pas_fin = []

        for g in graines:
            res_ref = simuler_goulot(parametres_banc(tolerance=1e-6, dt=0.01, duree=20.0, graine=g))
            assert res_ref.projection.non_convergences == 0
            assert res_ref.violation_paroi_max() <= 1e-12
            densites_ref.append(densite_phase_dense(res_ref, ZONE_ENTONNOIR))

            res_serree = simuler_goulot(
                parametres_banc(tolerance=1e-7, dt=0.01, duree=20.0, graine=g)
            )
            assert res_serree.projection.non_convergences == 0
            densites_serree.append(densite_phase_dense(res_serree, ZONE_ENTONNOIR))

            res_large = simuler_goulot(
                parametres_banc(tolerance=1e-5, dt=0.01, duree=20.0, graine=g)
            )
            densites_large.append(densite_phase_dense(res_large, ZONE_ENTONNOIR))

            res_pas_fin = simuler_goulot(
                parametres_banc(tolerance=1e-6, dt=0.005, duree=20.0, graine=g)
            )
            assert res_pas_fin.projection.non_convergences == 0
            densites_pas_fin.append(densite_phase_dense(res_pas_fin, ZONE_ENTONNOIR))

        ref = np.array(densites_ref)
        serree = np.array(densites_serree)
        large = np.array(densites_large)
        pas_fin = np.array(densites_pas_fin)

        ecarts_serree = serree - ref
        ecarts_large = large - ref
        ecarts_pas_fin = pas_fin - ref

        # 1. Tolérance resserrée (1e-7 vs 1e-6) : pas d'effet discernable
        assert abs(float(np.mean(ecarts_serree))) < 1e-3
        assert valeur_p_permutation_appariee(ecarts_serree) > 0.05

        # 2. Tolérance relâchée (1e-5 vs 1e-6) : décalage borné à moins de 0.03 pers/m^2 (< 1 %)
        assert abs(float(np.mean(ecarts_large))) < 0.03

        # 3. Pas de temps raffiné (0.005 vs 0.01 s) : décalage borné à moins de 0.05 pers/m^2 (< 1.5 %)
        assert abs(float(np.mean(ecarts_pas_fin))) < 0.05
        assert valeur_p_permutation_appariee(ecarts_pas_fin) > 0.05
