"""Rejouer toute la campagne finale depuis une liste de commandes, sans toucher au code.

#59 demande qu'on puisse « rejouer un cas, puis toute la campagne, sans toucher au
code ». Les commandes existent (comparer-piscine, balayer-piscine, diagramme-goulot...),
mais elles sont dispersees dans les documents de mesure, chacune avec ses graines et
sa sortie. `experiments/campagne-finale.yaml` les reunit ; cette commande les execute
dans l'ordre :

    viscocrowd rejouer-campagne experiments/campagne-finale.yaml --sortie data/finale
    viscocrowd rejouer-campagne ... --graines 11 12 13 14 15 16 17 18 19 20   # confirmation
    viscocrowd rejouer-campagne ... --seulement e1-e2 m9-dt                      # une partie
    viscocrowd rejouer-campagne ... --lister                                     # rien lancer

Chaque calcul ecrit sa sortie console dans `<sortie>/<identifiant>.txt` ; `{sortie}`
dans une commande devient `<sortie>/<identifiant>.json`, et `{graines}` la liste des
graines. Le journal n'est renomme qu'une fois le calcul reussi : relancer la meme
commande reprend la ou elle s'est arretee, sans refaire ce qui est fini, et un calcul
interrompu ou en echec est refait en entier.

Les calculs tournent dans ce processus, l'un apres l'autre. Pour aller plus vite, lancer
plusieurs `--seulement` dans des terminaux differents vers la meme sortie : chacun ne
touche qu'aux fichiers de ses identifiants.
"""

from __future__ import annotations

import contextlib
import io
import shlex
import sys
import time
from pathlib import Path

import yaml


def lire_plan(chemin: Path) -> dict:
    """Le YAML de campagne, controle : identifiants uniques, commandes non vides."""
    with Path(chemin).open(encoding="utf-8") as fichier:
        plan = yaml.safe_load(fichier)
    if not isinstance(plan, dict) or set(plan) != {"version", "graines", "calculs"}:
        raise ValueError("campagne attendue : version, graines, calculs")
    if plan["version"] != 1:
        raise ValueError("version de campagne non prise en charge (attendu : 1)")
    graines = plan["graines"]
    if not graines or not all(type(g) is int and g >= 0 for g in graines):
        raise ValueError("graines doit etre une liste d'entiers positifs ou nuls")
    vus = set()
    for calcul in plan["calculs"]:
        if not isinstance(calcul, dict) or set(calcul) != {"identifiant", "mesure", "commande"}:
            raise ValueError("chaque calcul attend identifiant, mesure, commande")
        identifiant = calcul["identifiant"]
        if not isinstance(identifiant, str) or not identifiant or "/" in identifiant:
            raise ValueError(f"identifiant invalide : {identifiant!r}")
        if identifiant in vus:
            raise ValueError(f"identifiant en double : {identifiant}")
        vus.add(identifiant)
    return plan


def arguments(commande: str, graines: list[int], sortie: Path) -> list[str]:
    """La ligne de commande d'un calcul, placeholders remplaces, prete pour `cli.main`."""
    argv = []
    for mot in shlex.split(commande):
        if mot == "{graines}":
            argv += [str(g) for g in graines]
        else:
            argv.append(mot.replace("{sortie}", sortie.as_posix()))
    return argv


def rejouer(
    plan: dict,
    sortie: Path,
    *,
    graines: list[int] | None = None,
    seulement: list[str] | None = None,
    progression=print,
) -> list[str]:
    """Execute les calculs non encore faits ; rend les identifiants en echec."""
    from viscocrowd.cli import main
    from viscocrowd.scenarios.campagne import verifier_sortie

    verifier_sortie(sortie)
    graines = list(graines or plan["graines"])
    calculs = plan["calculs"]
    if seulement:
        inconnus = set(seulement) - {c["identifiant"] for c in calculs}
        if inconnus:
            raise ValueError(f"identifiants inconnus : {', '.join(sorted(inconnus))}")
        calculs = [c for c in calculs if c["identifiant"] in seulement]
    sortie.mkdir(parents=True, exist_ok=True)
    echecs = []
    for calcul in calculs:
        identifiant = calcul["identifiant"]
        journal = sortie / f"{identifiant}.txt"
        if journal.exists():
            progression(f"{identifiant} : deja fait, {journal}")
            continue
        bilan = sortie / f"{identifiant}.json"
        # Un balayage ecrit son bilan apres chaque valeur : interrompu, il laisse un JSON
        # partiel sans journal, que la commande refuserait ensuite d'ecraser (revue de
        # Shaleena sur #148). On le met de cote, et le calcul est refait en entier.
        if bilan.exists():
            bilan.replace(bilan.with_name(bilan.name + ".precedent"))
            progression(f"{identifiant} : bilan partiel mis de cote ({bilan.name}.precedent)")
        argv = arguments(calcul["commande"], graines, bilan)
        progression(f"{identifiant} : viscocrowd {shlex.join(argv)}")
        tampon, debut = io.StringIO(), time.perf_counter()
        with contextlib.redirect_stdout(tampon), contextlib.redirect_stderr(tampon):
            try:
                code = main(argv)
            except SystemExit as erreur:  # argparse refuse une commande mal ecrite
                code = erreur.code if isinstance(erreur.code, int) else 1
        duree = time.perf_counter() - debut
        texte = (
            f"$ viscocrowd {shlex.join(argv)}\n{tampon.getvalue()}\n# {duree:.1f} s, code {code}\n"
        )
        if code == 0:
            partiel = journal.with_suffix(".partiel")
            partiel.write_text(texte, encoding="utf-8")
            partiel.replace(journal)
            progression(f"{identifiant} : fait en {duree:.0f} s")
        else:
            (sortie / f"{identifiant}.echec.txt").write_text(texte, encoding="utf-8")
            echecs.append(identifiant)
            progression(f"{identifiant} : ECHEC (code {code}), voir {identifiant}.echec.txt")
    return echecs


def ajouter_commande(sous) -> None:
    commande = sous.add_parser(
        "rejouer-campagne", help="rejoue la campagne finale depuis sa liste YAML, avec reprise"
    )
    commande.add_argument("plan", type=Path, help="experiments/campagne-finale.yaml")
    commande.add_argument("--sortie", type=Path, help="dossier des resultats, sous data/")
    commande.add_argument("--graines", type=int, nargs="+", help="remplace celles du plan")
    commande.add_argument("--seulement", nargs="+", help="identifiants a executer")
    commande.add_argument("--lister", action="store_true", help="affiche le plan sans calculer")
    commande.set_defaults(fonction=commande_rejouer)


def commande_rejouer(args) -> int:
    try:
        plan = lire_plan(args.plan)
        if args.lister:
            graines = args.graines or plan["graines"]
            for c in plan["calculs"]:
                ligne = shlex.join(
                    arguments(c["commande"], graines, Path(f"{c['identifiant']}.json"))
                )
                print(f"{c['identifiant']:<24} {c['mesure']}\n{'':<24} viscocrowd {ligne}")
            return 0
        if args.sortie is None:
            raise ValueError("--sortie est requis pour calculer")
        echecs = rejouer(plan, args.sortie, graines=args.graines, seulement=args.seulement)
    except (OSError, ValueError, yaml.YAMLError) as erreur:
        print(f"Campagne refusee : {erreur}", file=sys.stderr)
        return 1
    if echecs:
        print(f"{len(echecs)} calcul(s) en echec : {', '.join(echecs)}", file=sys.stderr)
        return 1
    print(f"Campagne complete dans {args.sortie}")
    return 0
