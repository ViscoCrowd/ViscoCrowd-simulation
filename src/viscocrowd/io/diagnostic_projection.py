"""Un echec de projection est un diagnostic NPZ distinct d'une trajectoire valide."""

from __future__ import annotations

import json
import platform
import sys
from dataclasses import dataclass
from importlib.metadata import version
from pathlib import Path

import numpy as np

from viscocrowd.core.verifications import exiger_fini
from viscocrowd.geometry.grille import paires_candidates
from viscocrowd.geometry.projection import InstantaneProjection, ProjectionExclusion
from viscocrowd.io.provenance import provenance_code


@dataclass
class DiagnosticProjection:
    instantane: InstantaneProjection
    metadonnees: dict

    def __post_init__(self):
        s, m = self.instantane, self.metadonnees
        for nom in ("x_libre", "x_residu", "rayons"):
            valeur = np.asarray(getattr(s, nom))
            if valeur.dtype.kind not in "fiu":
                raise ValueError(f"{nom} doit contenir des nombres reels")
            setattr(s, nom, valeur.astype(float))
        if (
            s.x_libre.ndim != 2
            or s.x_libre.shape[1:] != (2,)
            or len(s.x_libre) < 2
            or s.x_residu.shape != s.x_libre.shape
            or s.rayons.shape != (len(s.x_libre),)
            or np.any(s.rayons <= 0)
        ):
            raise ValueError("formes ou rayons du diagnostic invalides")
        exiger_fini(x_libre=s.x_libre, x_residu=s.x_residu, rayons=s.rayons, t=s.instant)
        if not isinstance(m, dict) or m.get("format") != "projection-non-convergee-v1":
            raise ValueError("format de diagnostic inconnu")
        for nom in ("residu_m", "tolerance_m"):
            if type(m.get(nom)) not in (int, float) or not np.isfinite(m[nom]) or m[nom] <= 0:
                raise ValueError(f"{nom} invalide")
        if type(m.get("iterations")) is not int or m["iterations"] < 1:
            raise ValueError("budget d'iterations invalide")
        if m["residu_m"] <= m["tolerance_m"]:
            raise ValueError("le diagnostic ne decrit pas un echec")
        if not isinstance(m.get("configuration"), dict):
            raise ValueError("configuration absente du diagnostic")
        json.dumps(m, allow_nan=False)


def ecrire_diagnostic(chemin, erreur, configuration, code) -> None:
    """Sauve sans ecraser ; l'echec ne devient jamais une trajectoire exploitable."""
    if erreur.instantane is None:
        raise ValueError("l'exception ne contient pas d'instantane de projection")
    diagnostic = DiagnosticProjection(
        erreur.instantane,
        {
            "format": "projection-non-convergee-v1",
            "configuration": configuration,
            "code": code,
            "versions": {
                "python": platform.python_version(),
                "numpy": np.__version__,
                "scipy": version("scipy"),
            },
            "residu_m": erreur.residu,
            "tolerance_m": erreur.tolerance,
            "iterations": int(erreur.iterations),
            "indices_agents": "locaux a cet appel de projection ; pas les identifiants globaux",
            "unites": {"x_libre": "m", "x_residu": "m", "rayons": "m", "instant": "s"},
        },
    )
    chemin = Path(chemin)
    if chemin.suffix != ".npz":
        raise ValueError("le diagnostic doit porter l'extension .npz")
    chemin.parent.mkdir(parents=True, exist_ok=True)
    with chemin.open("xb") as fichier:
        try:
            np.savez_compressed(
                fichier,
                **vars(diagnostic.instantane),
                metadonnees=np.array(json.dumps(diagnostic.metadonnees, allow_nan=False)),
            )
        except BaseException:
            chemin.unlink(missing_ok=True)
            raise


def lire_diagnostic(chemin) -> DiagnosticProjection:
    with np.load(chemin, allow_pickle=False) as archive:
        if set(archive.files) != {"x_libre", "x_residu", "rayons", "instant", "metadonnees"}:
            raise ValueError("champs de diagnostic invalides")
        meta, t = archive["metadonnees"], archive["instant"]
        if meta.shape != () or meta.dtype.kind != "U" or t.shape != () or t.dtype.kind not in "fiu":
            raise ValueError("metadonnees ou instant invalides")
        return DiagnosticProjection(
            InstantaneProjection(
                archive["x_libre"], archive["x_residu"], archive["rayons"], float(t)
            ),
            json.loads(meta.item()),
        )


def rejouer_diagnostic(diagnostic: DiagnosticProjection, *, iterations=None) -> dict:
    """Rejoue uniquement la projection, avec le domaine et l'instant enregistres."""
    from viscocrowd.geometry.boite import BoiteTournante
    from viscocrowd.geometry.couloir import Couloir
    from viscocrowd.scenarios.experience import _parametres

    m, s = diagnostic.metadonnees, diagnostic.instantane
    config = m["configuration"]
    if config.get("scenario") not in ("tassement", "couloir", "piscine"):
        raise ValueError("scenario non pris en charge par le diagnostic")
    try:
        p = _parametres(config)
    except (KeyError, TypeError) as erreur:
        raise ValueError("configuration du diagnostic invalide") from erreur
    if config["scenario"] == "tassement":
        domaine = BoiteTournante(demi_largeur=p.demi_largeur).projeter
    elif config["scenario"] == "couloir":
        domaine = Couloir(p.longueur, p.largeur, p.rectangles).projeter
    else:
        domaine = p.piscine.projeter
    projection = ProjectionExclusion(
        domaine,
        tolerance=m["tolerance_m"],
        iterations=m["iterations"] if iterations is None else iterations,
    )
    x = projection(s.x_libre, s.rayons, s.instant)
    i, j = paires_candidates(s.x_residu, s.rayons).T
    penetrations = s.rayons[i] + s.rayons[j] - np.linalg.norm(s.x_residu[i] - s.x_residu[j], axis=1)
    contacts = [
        {"agents_locaux": [int(a), int(b)], "recouvrement_m": float(d)}
        for a, b, d in zip(i, j, penetrations, strict=True)
        if d > m["tolerance_m"]
    ]
    return {
        "instant_s": s.instant,
        "agents": len(s.rayons),
        "contacts_hors_tolerance_archives": contacts,
        "residu_archive_m": m["residu_m"],
        "residu_rejoue_m": projection.recouvrement_max,
        "tolerance_m": projection.tolerance,
        "balayages": projection.iterations_max,
        "converge": projection.non_convergences == 0,
        "ecart_positions_archive_m": float(np.max(np.linalg.norm(x - s.x_residu, axis=1))),
        "code_archive": m.get("code"),
        "code_relecture": provenance_code(),
    }


def ajouter_commande(sous):
    commande = sous.add_parser("diagnostiquer-projection", help="rejoue une projection en echec")
    commande.add_argument("archive", type=Path)
    commande.add_argument("--iterations", type=int, help="budget de balayages a comparer")
    commande.set_defaults(fonction=commande_diagnostic)


def commande_diagnostic(args) -> int:
    try:
        bilan = rejouer_diagnostic(lire_diagnostic(args.archive), iterations=args.iterations)
    except (OSError, ValueError) as erreur:
        print(f"Diagnostic refuse : {erreur}", file=sys.stderr)
        return 2
    print(json.dumps(bilan, ensure_ascii=False, indent=2, allow_nan=False))
    return 0 if bilan["converge"] else 1
