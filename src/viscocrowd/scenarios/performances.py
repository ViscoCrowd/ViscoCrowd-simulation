"""Mesures dans un processus neuf par cas : temps mural, pic RSS et taille des archives."""

from __future__ import annotations

import json
import os
import platform
import subprocess
import sys
import tempfile
import time
from importlib.metadata import version
from pathlib import Path

import yaml

from viscocrowd.io.configuration import lire_configuration
from viscocrowd.io.provenance import provenance_code
from viscocrowd.scenarios.experience import _parametres, executer_configuration


def mesurer_cas(configuration: Path, archiver_tous: int) -> dict:
    """Appelee dans un enfant neuf ; le pic RSS inclut Python et les bibliotheques."""
    with tempfile.TemporaryDirectory(prefix="viscocrowd-mesure-") as dossier:
        archive = Path(dossier) / "trajectoire.npz"
        debut = time.perf_counter()
        donnees = executer_configuration(configuration, archive, archiver_tous=archiver_tous)
        temps = time.perf_counter() - debut
        try:
            import resource

            pic = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            # Darwin fournit des octets ; Linux des Kio. Ne pas extrapoler aux autres OS.
            rss = int(pic * (1 if sys.platform == "darwin" else 1024))
            if sys.platform not in ("darwin", "linux"):
                rss = None
        except ImportError:
            rss = None
        tableaux = [donnees.t, donnees.x, donnees.v, donnees.rayons, donnees.etats]
        return {
            "statut": "termine",
            "temps_simulation_validation_archive_s": temps,
            "pic_rss_processus_octets": rss,
            "tableaux_conserves_octets": sum(t.nbytes for t in tableaux if t is not None),
            "archive_npz_octets": archive.stat().st_size,
            "instants_archives": len(donnees.t),
            "t_final_s": float(donnees.t[-1]),
            "configuration_effective": donnees.metadonnees["configuration"],
            "validation": donnees.metadonnees["validation"],
            "code": donnees.metadonnees["code"],
        }


def _pythonpath_enfant() -> str:
    """Les sources de ce depot en tete, sans retirer un PYTHONPATH deja defini."""
    existant = os.environ.get("PYTHONPATH")
    return os.pathsep.join(filter(None, [str(Path(__file__).resolve().parents[2]), existant]))


def _entiers_distincts(valeurs, nom):
    if (
        not valeurs
        or any(type(v) is not int or v < 1 for v in valeurs)
        or len(set(valeurs)) != len(valeurs)
    ):
        raise ValueError(f"{nom} : entiers strictement positifs, distincts attendus")


def mesurer_performances(configuration, sortie, *, effectifs, intervalles, repetitions=1) -> dict:
    _entiers_distincts(effectifs, "effectifs")
    _entiers_distincts(intervalles, "intervalles")
    _entiers_distincts([repetitions], "repetitions")
    config = lire_configuration(configuration)
    if config["scenario"] == "bille_boite":
        raise ValueError("le banc de performances attend un scenario a plusieurs agents")
    if config["scenario"] != "piscine" and intervalles != [1]:
        raise ValueError("l'archivage espace est disponible pour le scenario piscine")
    plan = [config | {"parametres": config["parametres"] | {"n_agents": n}} for n in effectifs]
    for cas in plan:
        _parametres(cas)  # les effectifs impossibles sont refuses, pas ajustes silencieusement
    sortie = Path(sortie)
    if sortie.suffix != ".json":
        raise ValueError("le bilan doit porter l'extension .json")
    code = provenance_code()
    bilan = {
        "version": 1,
        "configuration_source": config,
        "code": code,
        "environnement": {
            "python": platform.python_version(),
            "plateforme": platform.platform(),
            "machine": platform.machine(),
            "versions": {n: version(n) for n in ("numpy", "scipy", "matplotlib", "pyyaml")},
            "threads": {
                n: os.environ.get(n)
                for n in (
                    "OMP_NUM_THREADS",
                    "OPENBLAS_NUM_THREADS",
                    "MKL_NUM_THREADS",
                    "VECLIB_MAXIMUM_THREADS",
                )
            },
        },
        "mesures": [],
    }
    sortie.parent.mkdir(parents=True, exist_ok=True)
    # Reservation exclusive avant tout calcul : pas de campagne couteuse puis d'ecrasement.
    with sortie.open("x", encoding="utf-8") as fichier:

        def enregistrer():
            fichier.seek(0)
            json.dump(bilan, fichier, ensure_ascii=False, indent=2, allow_nan=False)
            fichier.truncate()
            fichier.flush()

        enregistrer()
        with tempfile.TemporaryDirectory(prefix="viscocrowd-banc-") as dossier:
            racine = Path(dossier)
            for cas in plan:
                entree = racine / "configuration.yaml"
                entree.write_text(yaml.safe_dump(cas), encoding="utf-8")
                for intervalle in intervalles:
                    for repetition in range(1, repetitions + 1):
                        resultat = racine / "mesure.json"
                        resultat.unlink(missing_ok=True)
                        processus = subprocess.run(
                            [
                                sys.executable,
                                "-m",
                                "viscocrowd.scenarios.performances",
                                str(entree),
                                str(intervalle),
                                str(resultat),
                            ],
                            env=os.environ | {"PYTHONPATH": _pythonpath_enfant()},
                            capture_output=True,
                            text=True,
                            check=False,
                        )
                        ligne = {
                            "n_agents": cas["parametres"]["n_agents"],
                            "archiver_tous": intervalle,
                            "repetition": repetition,
                        }
                        if processus.returncode:
                            ligne.update(statut="echec", erreur=processus.stderr.strip())
                        else:
                            ligne.update(json.loads(resultat.read_text(encoding="utf-8")))
                            if ligne["code"] != code or provenance_code() != code:
                                raise ValueError(
                                    "code modifie pendant les mesures ; relancer le banc"
                                )
                        bilan["mesures"].append(ligne)
                        enregistrer()
    return bilan


def ajouter_commande(sous):
    commande = sous.add_parser(
        "mesurer-performances", help="mesure temps et memoire selon l'effectif"
    )
    commande.add_argument("configuration", type=Path)
    commande.add_argument("--effectifs", nargs="+", type=int, required=True)
    commande.add_argument("--archiver-tous", nargs="+", type=int, default=[1])
    commande.add_argument("--repetitions", type=int, default=1)
    commande.add_argument("--sortie", type=Path, required=True)
    commande.set_defaults(fonction=commande_performances)


def commande_performances(args):
    try:
        bilan = mesurer_performances(
            args.configuration,
            args.sortie,
            effectifs=args.effectifs,
            intervalles=args.archiver_tous,
            repetitions=args.repetitions,
        )
    except (OSError, ValueError) as erreur:
        print(f"Mesures refusees : {erreur}", file=sys.stderr)
        return 1
    for mesure in bilan["mesures"]:
        etiquette = f"N={mesure['n_agents']} K={mesure['archiver_tous']} rep={mesure['repetition']}"
        if mesure["statut"] == "echec":
            print(f"{etiquette} : ECHEC (voir {args.sortie})")
        else:
            rss = mesure["pic_rss_processus_octets"]
            memoire = "indisponible" if rss is None else f"{rss / 2**20:.2f} Mio"
            print(
                f"{etiquette} : {mesure['temps_simulation_validation_archive_s']:.3f} s ; "
                f"pic RSS {memoire} ; {mesure['instants_archives']} instants"
            )
    print(f"Mesures detaillees : {args.sortie}")
    return int(any(m["statut"] != "termine" for m in bilan["mesures"]))


if __name__ == "__main__":
    try:
        mesure = mesurer_cas(Path(sys.argv[1]), int(sys.argv[2]))
        Path(sys.argv[3]).write_text(json.dumps(mesure, allow_nan=False), encoding="utf-8")
    except (OSError, ValueError, RuntimeError) as erreur:
        print(str(erreur), file=sys.stderr)
        sys.exit(1)
