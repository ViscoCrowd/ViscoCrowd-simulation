"""Le script de l'annexe A1 range chaque ligne dans le bon domaine et chez le bon auteur."""

import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "contributions", Path(__file__).parents[1] / "report" / "contributions.py"
)
contributions = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(contributions)


def test_agreger_par_domaine_et_auteur():
    sortie = "\n".join(
        [
            "@Ada",
            "10\t2\tsrc/viscocrowd/geometry/projection.py",
            "5\t0\tsrc/viscocrowd/geometry/piscine.py",
            "-\t-\treport/figures/fig.png",
            "900\t0\tdocs/mesures/bilan.json",
            "@Bob",
            "3\t1\treport/sections/01-introduction.tex",
            "4\t0\tsrc/viscocrowd/{model => observables}/densite.py",
            "",
            "@Ada",
            "1\t1\treport/sections/07-conclusion.tex",
        ]
    )
    lignes = contributions.agreger(sortie)
    assert lignes["Moteur et projection"] == {"Ada": 12}
    assert lignes["Geometrie et scenarios"] == {"Ada": 5}
    assert lignes["Observables"] == {"Bob": 4}  # chemin d'arrivee du renommage
    assert lignes["Rapport"] == {"Bob": 4, "Ada": 2}
    assert "Documentation et planning" not in lignes  # JSON genere ignore
    parts = contributions.pourcentages(lignes, ["Ada", "Bob"])
    assert parts["Rapport"] == [33, 67]


def test_renommage_sans_partie_commune():
    """`git log --numstat` ecrit `x.md => docs/y.md` sans accolades : chemin d'arrivee."""
    lignes = contributions.agreger("@Ada\n3\t1\tplanning.md => docs/planning/README.md")
    assert lignes["Documentation et planning"] == {"Ada": 4}
