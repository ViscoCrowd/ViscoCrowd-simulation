"""Menu de parametrage : choisir la piscine au lancement, sans editer de YAML (`make menu`).

    viscocrowd menu [CONFIG] [--prereglage olympique] [--dossier data/menu] [--sans-relecture]

Le menu pose cinq questions (population, echelles, porte, panique, sol mouille), avec la
valeur de la configuration en defaut : Entree la garde. Les reponses deviennent des
surcharges `balayer-piscine` (`appliquer_fixes`), validees par `ParametresPiscine` avant tout
calcul. La configuration EFFECTIVE est ecrite a cote de l'archive, dans un dossier date :
un lancement reste reproductible. C'est un outil d'exploration et de demonstration ; les
resultats du rapport ne viennent que de YAML versionnes dans `experiments/`.
"""

from __future__ import annotations

import sys
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import yaml

from viscocrowd.scenarios.balayage_piscine import ENTIERS, PARAMETRES, appliquer_fixes


@dataclass(frozen=True)
class Question:
    """Une question du menu : un parametre de `PARAMETRES`, son libelle et son unite."""

    nom: str
    libelle: str
    unite: str


QUESTIONS = (
    Question("n_agents", "Baigneurs", "pers"),
    Question("echelles", "Échelles", "-"),
    Question("largeur_porte", "Largeur de la porte", "m"),
    Question("facteur_vitesse", "Panique (1 à 3)", "-"),
    Question("largeur_mouillee", "Bande mouillée", "m"),
)

# Dimensions reelles : bassin municipal de 25 m (la reference) et bassin olympique.
PREREGLAGES = {
    "bassin-25m": {},
    "olympique": {"longueur_bassin": 50.0, "largeur_bassin": 25.0, "n_agents": 200},
}


def valeur_actuelle(parametres: dict, nom: str):
    """Valeur de `nom` dans la table `parametres` ; nombre d'echelles pour une liste."""
    valeur = parametres
    for cle in PARAMETRES[nom].chemin:
        valeur = valeur[cle]
    return len(valeur) if nom == "echelles" and isinstance(valeur, list | tuple) else valeur


def _lire_nombre(texte: str, nom: str) -> float | int:
    nombre = float(texte.replace(",", "."))
    if nom in ENTIERS:
        if not nombre.is_integer():
            raise ValueError("entier attendu")
        return int(nombre)
    return nombre


def demander(
    parametres: dict,
    *,
    lire: Callable[[str], str] | None = None,
    ecrire: Callable[[str], None] | None = None,
    essais: int = 3,
) -> dict[str, float | int]:
    """Pose les `QUESTIONS` ; rend les seules surcharges saisies (Entree garde la valeur).

    Une saisie illisible est reposee ; `essais` saisies illisibles de suite abandonnent.
    Par defaut, `input` et `print`, resolus a l'appel (et non a la definition).
    """
    lire = lire or input
    ecrire = ecrire or print
    fixes: dict[str, float | int] = {}
    for question in QUESTIONS:
        defaut = valeur_actuelle(parametres, question.nom)
        unite = "" if question.unite == "-" else f" ({question.unite})"
        libelle = question.libelle
        if question.nom == "largeur_mouillee":  # la plage n'a pas toujours 20 m
            plage = parametres["geometrie"]["plage_sortie"]
            libelle += f", {plage:g} = jusqu'à la porte"
        ecrire(f"{libelle}{unite} [référence : {defaut}]")
        for _ in range(essais):
            texte = lire("> ").strip()
            if not texte:
                break
            try:
                nombre = _lire_nombre(texte, question.nom)
                # Retaper la reference ne cree pas de surcharge : « 2 » echelles
                # garde la liste de la reference au lieu de les repartir (#174).
                if nombre != defaut:
                    fixes[question.nom] = nombre
                break
            except ValueError:
                ecrire(f"  « {texte} » n'est pas un nombre valable, recommencer")
        else:
            raise ValueError(f"{question.libelle} : {essais} saisies invalides de suite")
    return fixes


def ajouter_commande(sous) -> None:
    commande = sous.add_parser(
        "menu", help="parametrer la piscine par questions, simuler, puis relire"
    )
    commande.add_argument(
        "configuration",
        type=Path,
        nargs="?",
        default=Path("experiments/piscine.yaml"),
        help="configuration de depart (defaut : experiments/piscine.yaml)",
    )
    commande.add_argument("--prereglage", choices=list(PREREGLAGES), help="dimensions reelles")
    commande.add_argument(
        "--dossier", type=Path, default=Path("data/menu"), help="ou ecrire les lancements"
    )
    commande.add_argument(
        "--sans-relecture", action="store_true", help="ne pas ouvrir la relecture a la fin"
    )
    commande.set_defaults(fonction=commande_menu)


def commande_menu(args) -> int:
    from viscocrowd.geometry.projection import ProjectionNonConvergee
    from viscocrowd.io.configuration import lire_configuration
    from viscocrowd.scenarios.experience import executer_configuration
    from viscocrowd.scenarios.piscine import ParametresPiscine

    try:
        base = lire_configuration(args.configuration)
        if base["scenario"] != "piscine":
            raise ValueError("le menu attend une configuration piscine")
        parametres = base["parametres"]
        if args.prereglage:
            parametres = appliquer_fixes(parametres, PREREGLAGES[args.prereglage])
        fixes = demander(parametres)
        effective = base | {"parametres": appliquer_fixes(parametres, fixes)}
        ParametresPiscine(**effective["parametres"], graine=base["graine"])  # refus avant calcul
        resume = ", ".join(
            f"{q.nom} = {valeur_actuelle(effective['parametres'], q.nom)}" for q in QUESTIONS
        )
        print(f"Lancement : {resume}")

        dossier = args.dossier / datetime.now().strftime("%Y%m%d-%H%M%S")
        suffixe = 1
        while dossier.exists():
            suffixe += 1
            dossier = dossier.with_name(f"{dossier.name.split('_')[0]}_{suffixe}")
        dossier.mkdir(parents=True)
        chemin_yaml = dossier / "configuration.yaml"
        chemin_yaml.write_text(yaml.safe_dump(effective, allow_unicode=True), encoding="utf-8")
        archive = dossier / "trajectoire.npz"
        donnees = executer_configuration(chemin_yaml, archive)
        print(f"Trajectoire : {archive} — t_final = {donnees.t[-1]:.2f} s")
        if args.sans_relecture:
            return 0
        from viscocrowd.cli import main

        return main(["rejouer", str(archive)])
    except (EOFError, KeyboardInterrupt):
        print("\nMenu abandonné", file=sys.stderr)
        return 1
    except (OSError, ValueError, ProjectionNonConvergee) as erreur:
        print(f"Menu refuse : {erreur}", file=sys.stderr)
        return 1
