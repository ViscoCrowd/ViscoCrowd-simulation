"""Preremplir l'annexe A1 : part de chaque membre, par domaine, d'apres l'historique git.

    python report/contributions.py            # tableau Markdown, sur HEAD
    python report/contributions.py --latex    # lignes du tableau de A1-repartition-taches.tex

Ce n'est qu'un point de depart. Les lignes ajoutees ou supprimees mesurent une trace dans
le depot, pas un effort : une relecture, une decision prise en seance ou une mesure longue
n'y apparaissent pas. Le tableau final reste a valider par les trois membres.

Les identites sont regroupees par `.mailmap` : un membre qui a commite sous deux adresses
y doit figurer, sinon il est compte deux fois. Les commits de fusion sont ecartes (sync,
publication de jalon) : leurs lignes sont deja comptees dans les commits qu'ils fusionnent.
"""

import argparse
import subprocess
from collections import defaultdict

# Premier prefixe qui correspond. L'ordre compte : la projection avant le reste de geometry.
DOMAINES = (
    ("Moteur et projection", ("src/viscocrowd/core/", "src/viscocrowd/geometry/projection.py")),
    ("Modele (milieux, guidage, chutes)", ("src/viscocrowd/model/",)),
    ("Geometrie et scenarios", ("src/viscocrowd/geometry/", "src/viscocrowd/scenarios/")),
    ("Observables", ("src/viscocrowd/observables/",)),
    ("Interface et figures", ("src/viscocrowd/ui/", "src/viscocrowd/viz/")),
    ("Tests", ("tests/",)),
    ("Configurations et campagnes", ("experiments/",)),
    ("Rapport", ("report/",)),
    ("Documentation et planning", ("docs/", "README.md", "CONTRIBUTING.md")),
)
AUTRE = "Outillage (CI, Docker, CLI)"
# Filtre par extension : les bilans JSON des campagnes sont generes, les compter
# donnerait tout au dernier qui a lance une mesure.
EXTENSIONS = (".py", ".tex", ".md", ".yaml", ".yml", ".toml", ".bib", ".ps1", "Makefile")


def domaine(chemin: str) -> str:
    for nom, prefixes in DOMAINES:
        if chemin.startswith(prefixes):
            return nom
    return AUTRE


def agreger(sortie_git: str) -> dict[str, dict[str, int]]:
    """{domaine: {auteur: lignes ajoutees + supprimees}} d'apres `git log --numstat`.

    Chaque commit commence par une ligne `@Auteur` ; les fichiers binaires (`-`) et les
    extensions hors liste sont ignores.
    """
    lignes: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    auteur = None
    for ligne in sortie_git.splitlines():
        if ligne.startswith("@"):
            auteur = ligne[1:]
            continue
        champs = ligne.split("\t")
        if len(champs) != 3 or "-" in champs[:2] or not champs[2].endswith(EXTENSIONS):
            continue
        # Un renommage s'ecrit `a/{x => y}.py`, ou `x.md => docs/y.md` quand les deux
        # chemins n'ont pas de partie commune : on garde le chemin d'arrivee.
        chemin = champs[2]
        if "{" in chemin and "=>" in chemin:
            avant, _, apres = chemin.partition("{")
            chemin = avant + apres.split("=> ", 1)[1].replace("}", "", 1)
        elif " => " in chemin:
            chemin = chemin.split(" => ", 1)[1]
        lignes[domaine(chemin)][auteur] += int(champs[0]) + int(champs[1])
    return lignes


def pourcentages(lignes: dict[str, dict[str, int]], auteurs: list[str]) -> dict[str, list[int]]:
    """Part de chaque auteur par domaine, en pourcentages arrondis (somme de 99 a 101)."""
    parts = {}
    for nom, par_auteur in lignes.items():
        total = sum(par_auteur.values())
        if total:
            parts[nom] = [round(100 * par_auteur.get(a, 0) / total) for a in auteurs]
    return parts


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("revision", nargs="?", default="HEAD")
    parser.add_argument("--latex", action="store_true", help="lignes LaTeX pour l'annexe A1")
    args = parser.parse_args()
    sortie = subprocess.run(
        ["git", "log", "--use-mailmap", "--no-merges", "--numstat", "--format=@%aN", args.revision],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    ).stdout
    lignes = agreger(sortie)
    auteurs = sorted({a for par_auteur in lignes.values() for a in par_auteur})
    parts = pourcentages(lignes, auteurs)
    ordre = [nom for nom, _ in DOMAINES] + [AUTRE]
    if args.latex:
        for nom in ordre:
            if nom in parts:
                print(f"{nom:<36} & " + " & ".join(f"{p}" for p in parts[nom]) + r" \\")
        return
    print("| Domaine | Lignes | " + " | ".join(auteurs) + " |")
    print("|---|---|" + "---|" * len(auteurs))
    for nom in ordre:
        if nom in parts:
            total = sum(lignes[nom].values())
            cellules = " | ".join(f"{p} %" for p in parts[nom])
            print(f"| {nom} | {total} | {cellules} |")


if __name__ == "__main__":
    main()
