"""Mesure du biais de densite lie a la tolerance et aux contacts multiples au goulot (M2, #10).

Protocole de mesure sur la geometrie cible (experiments/goulot.yaml, Seyfried et al. 2009) :
  - Compare la configuration de reference (tolerance 1e-6 m, dt = 0.01 s) a :
      1. une tolerance resserree (1e-7 m) ;
      2. une tolerance relachee (1e-5 m) ;
      3. un pas de temps affine (dt = 0.005 s).
  - Mesure appariee graine par graine (graines 1 a 10) dans l'entonnoir amont du goulot
    (x in [6.0, 7.8] m, y in [1.5, 3.5] m) pendant la phase d'ecoulement dense (t in [3.0, 15.0] s).
  - Calcule l'ecart moyen, l'erreur standard et la valeur p du test de permutation exact (2^n).

Usage:
    python docs/mesures/biais-densite-goulot-2026-11-03/mesurer.py experiments/goulot.yaml \\
        docs/mesures/biais-densite-goulot-2026-11-03/resultats.json
"""

import json
import sys
from pathlib import Path

import numpy as np

from viscocrowd.io.configuration import lire_configuration
from viscocrowd.io.provenance import provenance_code
from viscocrowd.observables.densite import Rectangle, densite_comptage
from viscocrowd.scenarios.goulot import ParametresGoulot, simuler_goulot


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
    resultat, zone: Rectangle, t_min: float = 3.0, t_max: float = 15.0
) -> float:
    """Densite moyenne dans la zone pendant l'intervalle de temps specifie."""
    masque = (resultat.t >= t_min) & (resultat.t <= t_max)
    densites = [densite_comptage(x, zone) for x in resultat.x[masque]]
    return float(np.mean(densites))


def main() -> None:
    source = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("experiments/goulot.yaml")
    cible = (
        Path(sys.argv[2])
        if len(sys.argv) > 2
        else Path("docs/mesures/biais-densite-goulot-2026-11-03/resultats.json")
    )
    cible.parent.mkdir(parents=True, exist_ok=True)

    config = lire_configuration(source)
    parametres_base = dict(config["parametres"])
    parametres_base["duree"] = 20.0
    zone_entonnoir = Rectangle(6.0, 7.8, 1.5, 3.5)
    graines = list(range(1, 11))

    variantes = [
        ("ref_tol_1e-6_dt_0.01", 1e-6, 0.01),
        ("serree_tol_1e-7_dt_0.01", 1e-7, 0.01),
        ("large_tol_1e-5_dt_0.01", 1e-5, 0.01),
        ("pas_fin_tol_1e-6_dt_0.005", 1e-6, 0.005),
    ]

    donnees_brutes: dict[str, list[dict]] = {nom: [] for nom, _, _ in variantes}
    for nom, tol, dt in variantes:
        p_dict = dict(parametres_base)
        p_dict["tolerance"] = tol
        p_dict["dt"] = dt
        for g in graines:
            p = ParametresGoulot(**p_dict, graine=g)
            res = simuler_goulot(p)
            rho = densite_phase_dense(res, zone_entonnoir)
            donnees_brutes[nom].append(
                {
                    "graine": g,
                    "densite": rho,
                    "statut": res.statut,
                    "non_convergences": res.projection.non_convergences,
                    "violation_max": float(res.violation_paroi_max()),
                }
            )

    densites_ref = np.array([item["densite"] for item in donnees_brutes["ref_tol_1e-6_dt_0.01"]])
    densite_moyenne_ref = float(np.mean(densites_ref))

    comparaisons = {}
    for nom, _, _ in variantes[1:]:
        densites_var = np.array([item["densite"] for item in donnees_brutes[nom]])
        ecarts = densites_var - densites_ref
        m = float(np.mean(ecarts))
        s = float(np.std(ecarts, ddof=1))
        se = float(s / np.sqrt(len(ecarts)))
        p_val = valeur_p_permutation_appariee(ecarts)
        comparaisons[nom] = {
            "difference_moyenne": m,
            "difference_relative": m / densite_moyenne_ref if densite_moyenne_ref > 0 else 0.0,
            "ecart_type": s,
            "erreur_standard": se,
            "valeur_p_permutation": p_val,
            "ecart_absolu_max": float(np.max(np.abs(ecarts))),
        }

    sortie = {
        "provenance": provenance_code(),
        "graines": graines,
        "zone_mesure": {
            "x_min": zone_entonnoir.x_min,
            "x_max": zone_entonnoir.x_max,
            "y_min": zone_entonnoir.y_min,
            "y_max": zone_entonnoir.y_max,
        },
        "densite_moyenne_reference": densite_moyenne_ref,
        "comparaisons": comparaisons,
        "simulations": donnees_brutes,
    }

    cible.write_text(json.dumps(sortie, indent=2), encoding="utf-8")
    print(f"Resultats ecrits dans {cible}")


if __name__ == "__main__":
    main()
