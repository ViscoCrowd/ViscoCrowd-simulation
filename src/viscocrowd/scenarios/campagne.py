"""Campagnes reprenables entre simulations ; jamais au milieu d'une trajectoire."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import sys
import tempfile
from importlib.metadata import version
from pathlib import Path

import yaml

import viscocrowd
from viscocrowd.io.configuration import lire_configuration
from viscocrowd.io.provenance import provenance_code
from viscocrowd.io.trajectoires import lire_trajectoire
from viscocrowd.scenarios.experience import _parametres, executer_configuration


def _empreinte(chemin: Path) -> str:
    with chemin.open("rb") as fichier:
        return hashlib.file_digest(fichier, "sha256").hexdigest()


def contexte() -> dict:
    """Le SHA seul ne distingue pas deux contenus differents d'un arbre modifie."""
    racine = Path(viscocrowd.__file__).parent
    code = hashlib.sha256()
    for fichier in sorted(racine.rglob("*.py")):
        code.update(fichier.relative_to(racine).as_posix().encode())
        code.update(b"\0")
        code.update(fichier.read_bytes())
        code.update(b"\0")
    return {
        "code": provenance_code(),
        "sources_sha256": code.hexdigest(),
        "python": platform.python_version(),
        "plateforme": platform.platform(),
        "machine": platform.machine(),
        "versions": {nom: version(nom) for nom in ("numpy", "scipy", "matplotlib", "pyyaml")},
    }


def _ecrire_json(chemin: Path, contenu: dict) -> None:
    """Remplacement atomique : une interruption laisse l'ancien suivi lisible."""
    temporaire = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=chemin.parent, prefix=".suivi-", delete=False
        ) as fichier:
            temporaire = Path(fichier.name)
            json.dump(contenu, fichier, ensure_ascii=False, indent=2, allow_nan=False)
            fichier.flush()
            os.fsync(fichier.fileno())
        os.replace(temporaire, chemin)
    finally:
        if temporaire is not None:
            temporaire.unlink(missing_ok=True)


def _plan(configurations: list[Path], graines: list[int] | None) -> list[dict]:
    if not configurations:
        raise ValueError("au moins une configuration est necessaire")
    if graines is not None and (
        not graines
        or len(set(graines)) != len(graines)
        or any(type(g) is not int or g < 0 for g in graines)
    ):
        raise ValueError("graines distinctes, entieres et positives ou nulles attendues")
    plan, vus = [], set()
    for chemin in configurations:
        config = lire_configuration(chemin)
        if config["scenario"] == "bille_boite" and graines is not None:
            raise ValueError("bille_boite est deterministe : omettre --graines")
        for graine in graines if graines is not None else [config["graine"]]:
            cas = config | {"graine": graine}
            _parametres(cas)  # toute erreur de configuration est detectee avant le premier calcul
            cle = json.dumps(cas, sort_keys=True, allow_nan=False)
            if cle in vus:
                raise ValueError("deux cas identiques dans la campagne")
            vus.add(cle)
            plan.append(cas)
    return plan


def executer_campagne(configurations, sortie, *, graines=None, reprendre=False, progression=print):
    """Execute tous les cas ; les echecs restent explicites et rendent le bilan incomplet."""
    plan = _plan([Path(c) for c in configurations], graines)
    sortie = Path(sortie)
    attendu = {"version": 1, "contexte": contexte(), "plan": plan}
    sortie.mkdir(parents=True, exist_ok=True)
    verrou = sortie / ".verrou"
    try:
        fichier_verrou = verrou.open("x", encoding="utf-8")
    except FileExistsError as erreur:
        raise ValueError(
            "campagne verrouillee ; verifier le processus avant de retirer .verrou"
        ) from erreur
    try:
        with fichier_verrou:
            json.dump({"pid": os.getpid(), "hote": platform.node()}, fichier_verrou)
        return _executer(sortie, attendu, reprendre, progression)
    finally:
        verrou.unlink()


def _executer(sortie: Path, attendu: dict, reprendre: bool, progression) -> dict:
    manifeste = sortie / "campagne.json"
    if manifeste.exists():
        if not reprendre:
            raise ValueError("campagne existante : utiliser --reprendre")
        suivi = json.loads(manifeste.read_text(encoding="utf-8"))
        if not isinstance(suivi, dict) or any(suivi.get(k) != v for k, v in attendu.items()):
            raise ValueError("reprise refusee : plan, code ou environnement different")
        resultats = suivi.get("resultats")
        if (
            not isinstance(resultats, list)
            or len(resultats) != len(attendu["plan"])
            or any(not isinstance(r, dict) for r in resultats)
        ):
            raise ValueError("suivi de campagne invalide")
    else:
        if reprendre:
            raise ValueError("aucune campagne a reprendre")
        if any(p.name != ".verrou" for p in sortie.iterdir()):
            raise ValueError("choisir un repertoire de campagne vide")
        suivi = attendu | {"resultats": [{"statut": "attente"} for _ in attendu["plan"]]}
        _ecrire_json(manifeste, suivi)
    for index, config in enumerate(suivi["plan"]):
        if contexte() != attendu["contexte"]:
            raise ValueError("code ou environnement modifie pendant la campagne")
        prefixe = f"{index + 1:04d}"
        archive = sortie / f"{prefixe}.npz"
        resultat = suivi["resultats"][index]
        termine = resultat.get("statut") == "termine"
        if termine and archive.exists() and _empreinte(archive) == resultat.get("sha256"):
            lire_trajectoire(archive)
            progression(f"[{index + 1}/{len(suivi['plan'])}] {prefixe} conserve")
            continue
        # Une archive incomplete/corrompue reste disponible pour le diagnostic.
        if archive.exists():
            suffixe = 1
            while (sortie / f"{prefixe}.invalide-{suffixe}.npz").exists():
                suffixe += 1
            archive.rename(sortie / f"{prefixe}.invalide-{suffixe}.npz")
        configuration = sortie / f"{prefixe}.yaml"
        configuration.write_text(yaml.safe_dump(config, sort_keys=True), encoding="utf-8")
        suivi["resultats"][index] = {"statut": "en_cours"}
        _ecrire_json(manifeste, suivi)
        progression(
            f"[{index + 1}/{len(suivi['plan'])}] {prefixe} calcul "
            f"({config['scenario']}, graine {config['graine']})"
        )
        try:
            donnees = executer_configuration(configuration, archive)
            if contexte() != attendu["contexte"]:
                raise ValueError("code ou environnement modifie pendant le calcul")
            suivi["resultats"][index] = {
                "statut": "termine",
                "sha256": _empreinte(archive),
                "instants": len(donnees.t),
                "t_final_s": float(donnees.t[-1]),
                "validation": donnees.metadonnees.get("validation", {}),
            }
        except KeyboardInterrupt:
            suivi["resultats"][index] = {"statut": "interrompu"}
            _ecrire_json(manifeste, suivi)
            raise
        except (OSError, ValueError, RuntimeError) as erreur:
            suivi["resultats"][index] = {"statut": "echec", "erreur": str(erreur)}
            progression(f"  echec : {erreur}")
        _ecrire_json(manifeste, suivi)
    return suivi


def ajouter_commande(sous) -> None:
    commande = sous.add_parser("campagne", help="execute plusieurs configurations avec reprise")
    commande.add_argument("configurations", nargs="+", type=Path)
    commande.add_argument("--graines", nargs="+", type=int)
    commande.add_argument("--sortie", required=True, type=Path)
    commande.add_argument("--reprendre", action="store_true")
    commande.set_defaults(fonction=commande_campagne)


def commande_campagne(args) -> int:
    try:
        suivi = executer_campagne(
            args.configurations, args.sortie, graines=args.graines, reprendre=args.reprendre
        )
    except KeyboardInterrupt:
        print("Campagne interrompue ; reprendre avec --reprendre.", file=sys.stderr)
        return 130
    except (OSError, ValueError) as erreur:
        print(f"Campagne refusee : {erreur}", file=sys.stderr)
        return 1
    termines = sum(r["statut"] == "termine" for r in suivi["resultats"])
    print(f"Campagne : {termines}/{len(suivi['plan'])} calculs termines ; suivi dans {args.sortie}")
    return 0 if termines == len(suivi["plan"]) else 1
