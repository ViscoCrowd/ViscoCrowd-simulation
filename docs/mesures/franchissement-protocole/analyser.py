"""Resume des durees de franchissement chronometrees (protocole.md du meme dossier).

Usage : python docs/mesures/franchissement-protocole/analyser.py CHEMIN/chronos.csv

Affiche, par nature (rebord, echelle) et par allure (normale, pressee), le nombre d'essais
valides, la mediane et l'ecart interquartile des durees, en secondes, en tableau Markdown.
Les essais notes NA (interrompus) sont comptes a part.
"""

import csv
import statistics
import sys
from collections import defaultdict
from pathlib import Path


def quartiles(valeurs: list[float]) -> tuple[float, float]:
    """Premier et troisieme quartiles (methode inclusive), en s."""
    if len(valeurs) < 2:
        return valeurs[0], valeurs[0]
    q = statistics.quantiles(valeurs, n=4, method="inclusive")
    return q[0], q[2]


def main(chemin: Path) -> None:
    durees: dict[tuple[str, str], list[float]] = defaultdict(list)
    interrompus: dict[tuple[str, str], int] = defaultdict(int)
    with chemin.open(encoding="utf-8", newline="") as fichier:
        for ligne in csv.DictReader(fichier):
            cle = (ligne["nature"].strip(), ligne["allure"].strip())
            texte = ligne["duree_s"].strip()
            if texte.upper() == "NA" or not texte:
                interrompus[cle] += 1
            else:
                durees[cle].append(float(texte.replace(",", ".")))
    print("| Nature | Allure | Essais | Médiane (s) | Écart interquartile (s) | Interrompus |")
    print("|---|---|---|---|---|---|")
    for cle in sorted(set(durees) | set(interrompus)):
        valeurs = sorted(durees[cle])
        if valeurs:
            q1, q3 = quartiles(valeurs)
            mediane = f"{statistics.median(valeurs):.1f}"
            ecart = f"{q1:.1f} à {q3:.1f}"
        else:
            mediane, ecart = "-", "-"
        nature, allure = cle
        n, arrets = len(valeurs), interrompus[cle]
        print(f"| {nature} | {allure} | {n} | {mediane} | {ecart} | {arrets} |")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage : analyser.py CHEMIN/chronos.csv")
    main(Path(sys.argv[1]))
