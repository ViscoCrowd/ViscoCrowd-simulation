"""Regenere tests/donnees/reference_piscine.json, lu par tests/test_reference_piscine.py.

A lancer seulement quand une PR change VOLONTAIREMENT la simulation de reference, et a
signaler dans sa description (ce qui change, et pourquoi) :

    python tests/donnees/regenerer_reference.py
"""

import json
import subprocess
import sys
from pathlib import Path

DOSSIER = Path(__file__).resolve().parent
sys.path.insert(0, str(DOSSIER.parent))  # pour importer le module de test

from test_reference_piscine import FICHIER, N_AGENTS, mesurer_reference  # noqa: E402


def main() -> None:
    commit = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, check=False
    ).stdout.strip()
    contenu = {
        "description": f"experiments/piscine.yaml a {N_AGENTS} agents, graine du YAML",
        "commit": commit or None,
        "unites": {"sorties": "s", "t50": "s", "t100": "s"},
        **mesurer_reference(),
    }
    FICHIER.write_text(json.dumps(contenu, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"{FICHIER} : t50 = {contenu['t50']:.3f} s, t100 = {contenu['t100']:.3f} s")


if __name__ == "__main__":
    main()
