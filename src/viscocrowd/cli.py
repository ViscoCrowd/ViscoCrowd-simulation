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
from viscocrowd.scenarios.tassement import ParametresTassement, simuler_tassement

RACINE = Path(__file__).resolve().parents[2]

# Les contraintes de domaine sont reprojetees en dernier a chaque balayage :
# elles tiennent a la precision machine, seuls les arrondis subsistent.
PRECISION_PAROI = 1e-14  # m


def hors_seuil(nom: str, valeur: float, seuil: float, unite: str = "m") -> str | None:
    """Message d'echec si `valeur` depasse `seuil`, None si le critere tient.

    La comparaison est volontairement ecrite `not valeur <= seuil` : un NaN
    echoue toutes les comparaisons, il doit donc compter comme un ECHEC plutot
    que passer inapercu.
    """
    if not valeur <= seuil:
        return f"{nom} : {valeur:.3e} {unite} > seuil {seuil:.1e} {unite}"
    return None


def conclure(echecs: list[str]) -> int:
    """Affiche le verdict et rend le code de retour du processus.

    0 quand tous les criteres tiennent, 1 des qu'un seul deborde. C'est ce code
    que la CI regarde : sans lui, une regression du moteur afficherait un mauvais
    chiffre en laissant le job vert.
    """
    if echecs:
        print(f"\nVALIDATION EN ECHEC - {len(echecs)} critere(s) hors seuil :")
        for echec in echecs:
            print(f"   - {echec}")
        return 1

    print("\nValidation reussie : tous les criteres chiffres tiennent leur seuil.")
    return 0


def commande_valider_moteur(args: argparse.Namespace) -> int:
    """Rejoue les criteres de validation du moteur et affiche les NOMBRES.

    Une simulation qui tourne n'est pas une simulation juste : chaque critere
    produit ici une valeur mesuree, pas une appreciation.

    Returns:
        0 si tous les criteres chiffres tiennent leur seuil, 1 sinon. Le code de
        retour fait partie du contrat : la CI appelle cette commande, et une
        regression du moteur doit la faire ECHOUER, pas seulement afficher un
        mauvais chiffre que personne ne relit.
    """
    debut = time.perf_counter()
    echecs: list[str] = []

    def exiger(nom: str, valeur: float, seuil: float, unite: str = "m") -> None:
        """Enregistre un echec si la grandeur mesuree depasse son seuil."""
        message = hors_seuil(nom, valeur, seuil, unite)
        if message is not None:
            echecs.append(message)

    print("Validation du moteur — bille dans une boite en rotation")
    print("=" * 62)

    # Critere 1 — respect de la contrainte, pour plusieurs pas de temps.
    print("\n1. Respect de la contrainte de confinement")
    print(f"   {'dt (s)':>10} {'violation max (m)':>20}")
    for dt in (1e-1, 1e-2, 1e-3):
        resultat = simuler_bille(ParametresBille(dt=dt, duree=10.0))
        violation = resultat.violation_max()
        print(f"   {dt:>10.0e} {violation:>20.3e}")
        # La projection sur le domaine est exacte : seuls les arrondis subsistent.
        exiger(f"confinement a dt = {dt:.0e} s", violation, PRECISION_PAROI)

    # Critere 2 — energie, en boite fixe.
    print("\n2. Energie mecanique (boite fixe, omega = 0)")
    resultat = simuler_bille(ParametresBille(omega=0.0, dt=1e-3, duree=10.0))
    energie = energie_mecanique(resultat.x, resultat.v, masse=resultat.parametres.masse)
    variations = np.diff(energie)
    print(f"   energie initiale        : {energie[0]:.6f} J")
    print(f"   energie finale          : {energie[-1]:.6f} J")
    print(f"   dissipation totale      : {energie[0] - energie[-1]:.6f} J")
    print(f"   plus forte remontee     : {np.max(variations):.3e} J  (doit etre <= 0)")
    # Choc mou : l'energie mecanique ne doit jamais croitre, a l'arrondi pres.
    exiger("remontee d'energie (boite fixe)", float(np.max(variations)), 1e-12, "J")

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

    # Critere 4 — exclusion entre agents : 36 disques qui tombent et s'empilent.
    tolerance = 1e-6
    print(f"\n4. Exclusion entre agents (36 disques qui s'empilent, tolerance {tolerance:.0e} m)")
    print(
        f"   {'dt (s)':>10} {'recouvrement (m)':>18} {'paroi (m)':>11} "
        f"{'balayages max':>14} {'non converge':>13}"
    )
    for dt in (4e-3, 2e-3):
        tassement = simuler_tassement(
            ParametresTassement(n_agents=36, duree=3.0, dt=dt, graine=1, tolerance=tolerance)
        )
        proj = tassement.projection
        recouvrement = tassement.recouvrement_max()
        paroi = max(tassement.violation_paroi_max(), 0.0)
        print(
            f"   {dt:>10.0e} {recouvrement:>18.2e} {paroi:>11.1e} "
            f"{proj.iterations_max:>14d} {proj.non_convergences:>7d}/{proj.n_appels}"
        )
        # Une projection qui n'a pas converge laisse des agents interpenetres :
        # la configuration n'est pas un etat physique, elle ne doit pas passer.
        exiger(f"recouvrement a dt = {dt:.0e} s", recouvrement, tolerance)
        exiger(f"paroi a dt = {dt:.0e} s", paroi, PRECISION_PAROI)
        if proj.non_convergences:
            echecs.append(
                f"projections non convergees a dt = {dt:.0e} s : "
                f"{proj.non_convergences} sur {proj.n_appels} "
                f"(recouvrement maximal {proj.recouvrement_max:.3e} m)"
            )

    if args.figures:
        from viscocrowd.viz.figures import produire_toutes

        destination = Path(args.sortie)
        print(f"\n5. Figures -> {destination}")
        for chemin in produire_toutes(destination):
            print(f"   {chemin.name}")

    print(f"\nTemps d'execution : {time.perf_counter() - debut:.1f} s")

    return conclure(echecs)


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

    interface = sous.add_parser(
        "interface", help="ouvre une maquette visuelle de la piscine, sans simulation"
    )
    interface.set_defaults(fonction=commande_interface)

    return analyseur


def commande_interface(_args: argparse.Namespace) -> int:
    """Charge l'affichage uniquement pour la commande graphique."""
    from viscocrowd.ui.piscine import ouvrir_interface

    return ouvrir_interface()


def main(argv: list[str] | None = None) -> int:
    args = construire_analyseur().parse_args(argv)
    return int(args.fonction(args))


if __name__ == "__main__":
    sys.exit(main())
