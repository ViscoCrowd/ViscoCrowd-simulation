"""Provenance du code qui a produit un resultat : commit Git et modifications locales.

Les archives enregistrent deja les parametres, la graine et les versions des
bibliotheques. Il manquait le CODE : deux executions de la meme configuration,
avant et apres une correction du moteur, produisent deux archives que rien ne
distinguait. On enregistre donc le commit, et on signale si le code ou les
configurations differaient de ce commit au moment du calcul.

Seuls comptent les chemins qui determinent un resultat : le code (`src`), les
configurations (`experiments`) et les versions declarees ou figees. Une
modification des tests, de la documentation ou du rapport ne change aucun
chiffre et ne marque pas l'archive.

Dans l'image Docker, il n'y a ni depot ni git : le commit est alors lu dans la
variable d'environnement VISCOCROWD_COMMIT, fixee a la construction de l'image
(`docker build --build-arg VISCOCROWD_COMMIT=$(git rev-parse HEAD) .`). Les
modifications locales sont alors inconnues, et notees comme telles.
"""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

# Racine du depot quand le paquet est installe en mode editable : src/viscocrowd/io/.
RACINE = Path(__file__).resolve().parents[3]

# Ce qui determine un resultat : code, configurations, versions declarees et figees.
CHEMINS_SUIVIS = ("src", "experiments", "pyproject.toml", "requirements.lock.txt")

VARIABLE_COMMIT = "VISCOCROWD_COMMIT"

_SHA = re.compile(r"[0-9a-f]{40}")


def _git(racine: Path, *arguments: str) -> str:
    resultat = subprocess.run(
        ["git", "-C", str(racine), *arguments],
        capture_output=True,
        text=True,
        check=True,
        timeout=10,
    )
    return resultat.stdout.strip()


def provenance_code(racine: str | Path = RACINE) -> dict:
    """Commit et etat du code, a enregistrer dans les metadonnees d'une archive.

    Args:
        racine: racine du depot dont on veut le commit.

    Returns:
        Un dictionnaire JSON :
          - commit : SHA complet (40 caracteres), ou None s'il est inconnu ;
          - modifications_locales : vrai si un chemin suivi differe du commit
            (fichier modifie, ajoute ou non suivi), None si on ne peut pas le savoir ;
          - source : "git", "environnement" ou "indisponible".
    """
    racine = Path(racine).resolve()
    try:
        # Le paquet peut etre installe ailleurs que dans un depot, mais sous un depot
        # parent (un environnement virtuel dans le projet) : on exige que la racine
        # attendue soit elle-meme le depot, pour ne pas attribuer un commit etranger.
        if Path(_git(racine, "rev-parse", "--show-toplevel")).resolve() != racine:
            raise FileNotFoundError(racine)
        commit = _git(racine, "rev-parse", "HEAD")
        etat = _git(racine, "status", "--porcelain", "--untracked-files=all", "--", *CHEMINS_SUIVIS)
    except (OSError, subprocess.SubprocessError):
        pass  # pas de git, pas de depot, ou depot refuse (proprietaire different)
    else:
        if _SHA.fullmatch(commit):
            return {"commit": commit, "modifications_locales": bool(etat), "source": "git"}

    commit = os.environ.get(VARIABLE_COMMIT, "").strip().lower()
    if _SHA.fullmatch(commit):
        return {"commit": commit, "modifications_locales": None, "source": "environnement"}
    return {"commit": None, "modifications_locales": None, "source": "indisponible"}
