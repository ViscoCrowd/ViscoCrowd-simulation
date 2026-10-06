"""Interface en ligne de commande.

Point d'entree unique du projet, pour que relancer les simulations et retrouver
les resultats tienne en une commande — exigence de reproductibilite des
consignes du module.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import numpy as np

from viscocrowd import __version__
from viscocrowd.observables.energie import ecart_entrainement, energie_mecanique
from viscocrowd.scenarios.bille_boite import ParametresBille, simuler_bille

RACINE = Path(__file__).resolve().parents[2]


def commande_valider_moteur(args: argparse.Namespace) -> int:
    """Rejoue les criteres de validation du moteur et affiche les NOMBRES.

    Une simulation qui tourne n'est pas une simulation juste : chaque critere
    produit ici une valeur mesuree, pas une appreciation.
    """
    debut = time.perf_counter()

    print("Validation du moteur — bille dans une boite en rotation")
    print("=" * 62)

    # Critere 1 — respect de la contrainte, pour plusieurs pas de temps.
    print("\n1. Respect de la contrainte de confinement")
    print(f"   {'dt (s)':>10} {'violation max (m)':>20}")
    for dt in (1e-1, 1e-2, 1e-3):
        resultat = simuler_bille(ParametresBille(dt=dt, duree=10.0))
        print(f"   {dt:>10.0e} {resultat.violation_max():>20.3e}")

    # Critere 2 — energie, en boite fixe.
    print("\n2. Energie mecanique (boite fixe, omega = 0)")
    resultat = simuler_bille(ParametresBille(omega=0.0, dt=1e-3, duree=10.0))
    energie = energie_mecanique(resultat.x, resultat.v, masse=resultat.parametres.masse)
    variations = np.diff(energie)
    print(f"   energie initiale        : {energie[0]:.6f} J")
    print(f"   energie finale          : {energie[-1]:.6f} J")
    print(f"   dissipation totale      : {energie[0] - energie[-1]:.6f} J")
    print(f"   plus forte remontee     : {np.max(variations):.3e} J  (doit etre <= 0)")

    # Critere 3 — comportement asymptotique, et son domaine de validite.
    print("\n3. Entrainement solide (moyenne sur la derniere seconde)")
    print(f"   {'omega (rad/s)':>14} {'w^2 R / g':>12} {'ecart (m/s)':>14}")
    for omega in (1.0, 3.0, 5.0, 10.0):
        resultat = simuler_bille(ParametresBille(omega=omega, dt=1e-3, duree=20.0))
        v_solide = np.stack(
            [resultat.boite.vitesse_entrainement(resultat.x[p]) for p in range(resultat.t.size)]
        )
        ecart = ecart_entrainement(resultat.v, v_solide)
        derniers = resultat.t >= resultat.t[-1] - 1.0
        rapport = omega**2 * resultat.parametres.demi_largeur / 9.81
        print(f"   {omega:>14.1f} {rapport:>12.2f} {np.mean(ecart[derniers]):>14.3e}")

    print(
        "\n   L'entrainement n'a lieu qu'en regime centrifuge (w^2 R / g >~ 1)."
        "\n   La valeur suggeree par le sujet, omega = 1 rad/s, n'y est pas."
    )

    if args.figures:
        from viscocrowd.viz.figures import produire_toutes

        destination = Path(args.sortie)
        print(f"\n4. Figures -> {destination}")
        for chemin in produire_toutes(destination):
            print(f"   {chemin.name}")

    print(f"\nTemps d'execution : {time.perf_counter() - debut:.1f} s")
    return 0


def construire_analyseur() -> argparse.ArgumentParser:
    analyseur = argparse.ArgumentParser(
        prog="viscocrowd",
        description=(
            "Simulation particulaire d'une evacuation de piscine en panique "
            "(module R5.12 — Modelisation mathematique)."
        ),
    )
    analyseur.add_argument("--version", action="version", version=f"viscocrowd {__version__}")

    sous = analyseur.add_subparsers(dest="commande", required=True)

    valider = sous.add_parser(
        "valider-moteur",
        help="rejoue les criteres de validation du moteur et affiche les mesures",
    )
    valider.add_argument(
        "--figures",
        action="store_true",
        help="produit aussi les figures de validation",
    )
    valider.add_argument(
        "--sortie",
        default=str(RACINE / "figures"),
        help="repertoire de destination des figures (defaut : figures/)",
    )
    valider.set_defaults(fonction=commande_valider_moteur)

    return analyseur


def main(argv: list[str] | None = None) -> int:
    args = construire_analyseur().parse_args(argv)
    return int(args.fonction(args))


if __name__ == "__main__":
    sys.exit(main())
