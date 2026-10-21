"""Archives NPZ v1 : tableaux SI et metadonnees JSON, lisibles sans pickle."""

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from viscocrowd.core.verifications import exiger_fini


@dataclass
class Trajectoire:
    """Population fixe : t (P,), x/v (P, N, 2), rayons (N,), en s, m et m/s."""

    t: np.ndarray
    x: np.ndarray
    v: np.ndarray
    rayons: np.ndarray
    metadonnees: dict

    def __post_init__(self) -> None:
        for nom in ("t", "x", "v", "rayons"):
            tableau = np.asarray(getattr(self, nom))
            if tableau.dtype.kind not in "fiu":
                raise ValueError(f"{nom} doit contenir des nombres reels")
            setattr(self, nom, np.asarray(tableau, dtype=float))
        if self.t.ndim != 1 or self.t.size == 0 or np.any(np.diff(self.t) <= 0):
            raise ValueError("t doit etre non vide et strictement croissant")
        if self.x.ndim != 3 or self.x.shape[0] != self.t.size or self.x.shape[2] != 2:
            raise ValueError("x doit etre de forme (P, N, 2), avec P = len(t)")
        if self.v.shape != self.x.shape or self.rayons.shape != (self.x.shape[1],):
            raise ValueError("formes de v ou rayons incompatibles avec x")
        exiger_fini(t=self.t, x=self.x, v=self.v, rayons=self.rayons)
        if np.any(self.rayons <= 0):
            raise ValueError("rayons doit etre strictement positif")
        if not isinstance(self.metadonnees, dict):
            raise ValueError("metadonnees doit etre un objet JSON")
        # Verifie aussi les valeurs non finies et les objets non serialisables.
        json.dumps(self.metadonnees, allow_nan=False)


def ecrire_trajectoire(chemin: str | Path, donnees: Trajectoire) -> None:
    """Cree une archive sans ecraser un resultat existant, apres validation."""
    donnees = Trajectoire(**vars(donnees))
    chemin = Path(chemin)
    if chemin.suffix != ".npz":
        raise ValueError("la trajectoire doit porter l'extension .npz")
    contenu = json.dumps(donnees.metadonnees, ensure_ascii=False, sort_keys=True, allow_nan=False)
    chemin.parent.mkdir(parents=True, exist_ok=True)
    # Un fichier ouvert evite que NumPy ajoute silencieusement une extension.
    with chemin.open("xb") as fichier:
        np.savez_compressed(
            fichier,
            version=np.array(1),
            t=donnees.t,
            x=donnees.x,
            v=donnees.v,
            rayons=donnees.rayons,
            metadonnees=np.array(contenu),
        )


def lire_trajectoire(chemin: str | Path) -> Trajectoire:
    """Relit et controle les formes, valeurs finies et version avant les observables."""
    with np.load(chemin, allow_pickle=False) as archive:
        if set(archive.files) != {"version", "t", "x", "v", "rayons", "metadonnees"}:
            raise ValueError("champs d'archive NPZ invalides")
        version = archive["version"]
        if version.shape != () or version.dtype.kind not in "iu" or version.item() != 1:
            raise ValueError("version d'archive non prise en charge (attendu : 1)")
        meta = archive["metadonnees"]
        if meta.shape != () or meta.dtype.kind != "U":
            raise ValueError("metadonnees doit etre une chaine JSON scalaire")
        return Trajectoire(
            t=archive["t"],
            x=archive["x"],
            v=archive["v"],
            rayons=archive["rayons"],
            metadonnees=json.loads(meta.item()),
        )
