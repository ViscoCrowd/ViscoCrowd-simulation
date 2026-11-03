"""Archives NPZ v1 : tableaux SI et metadonnees JSON, lisibles sans pickle.

Un scenario a etats (piscine) ajoute un tableau `etats` (P, N) d'entiers. Sans lui,
un agent sorti ou en franchissement, pose hors de la foule active, serait relu comme
un disque actif ; sa legende est dans les metadonnees, cle `etats`.
"""

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from viscocrowd.core.verifications import exiger_fini

_CHAMPS = {"version", "t", "x", "v", "rayons", "metadonnees"}


@dataclass
class Trajectoire:
    """Population fixe : t (P,), x/v (P, N, 2), rayons (N,), en s, m et m/s.

    `etats` (P, N), facultatif : code entier de l'etat de chaque agent a chaque instant.
    """

    t: np.ndarray
    x: np.ndarray
    v: np.ndarray
    rayons: np.ndarray
    metadonnees: dict
    etats: np.ndarray | None = None

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
        if self.etats is not None:
            etats = np.asarray(self.etats)
            if etats.dtype.kind not in "iu" or etats.shape != self.x.shape[:2]:
                raise ValueError("etats doit etre un tableau d'entiers de forme (P, N)")
            if np.any(etats < 0):
                raise ValueError("etats doit contenir des codes positifs ou nuls")
            self.etats = etats.astype(np.int64)
        if not isinstance(self.metadonnees, dict):
            raise ValueError("metadonnees doit etre un objet JSON")
        _ = self.pas_archivage
        _ = self.dt_simulation
        # Verifie aussi les valeurs non finies et les objets non serialisables.
        json.dumps(self.metadonnees, allow_nan=False)

    @property
    def pas_archivage(self) -> int:
        """Facteur d'espacement K : 1 si tous les pas physiques sont archives."""
        archivage = self.metadonnees.get("archivage")
        if archivage is None:
            return 1
        if not isinstance(archivage, dict):
            raise ValueError("metadonnees['archivage'] doit etre un objet JSON")
        valeur = archivage.get("tous_les_pas", 1)
        if type(valeur) is not int or valeur < 1:
            raise ValueError("archivage.tous_les_pas doit etre un entier strictement positif")
        return valeur

    @property
    def dt_simulation(self) -> float | None:
        """Pas de temps physique de la simulation (en s) inscrit dans metadonnees['archivage']."""
        archivage = self.metadonnees.get("archivage")
        if not isinstance(archivage, dict) or "dt_simulation_s" not in archivage:
            return None
        dt = archivage["dt_simulation_s"]
        if (
            isinstance(dt, bool)
            or not isinstance(dt, (int, float))
            or not np.isfinite(dt)
            or dt <= 0
        ):
            raise ValueError(
                "archivage.dt_simulation_s doit etre un nombre reel strictement positif"
            )
        return float(dt)

    @property
    def est_complete(self) -> bool:
        """Vrai si chaque pas de temps physique de la simulation est conserve."""
        if self.pas_archivage != 1:
            return False
        dt = self.dt_simulation
        if dt is None:
            return False
        return not (self.t.size >= 2 and float(np.max(np.diff(self.t))) > dt * (1.0 + 1e-6))

    def exiger_complete(self, observable: str = "le calcul d'observable") -> None:
        """Refuse une archive dont les positions intermediaires sont perdues (K > 1).

        Args:
            observable: nom ou description de la mesure appelante.

        Raises:
            ValueError: si l'archive est espacee (tous_les_pas > 1), si dt_simulation_s
                est absent, ou si les instants t presentent un ecart superieur au pas dt.
        """
        if self.pas_archivage > 1:
            raise ValueError(
                f"{observable} refuse une archive espacee (tous les {self.pas_archivage} pas) : "
                "les positions intermediaires sont perdues et faussent la mesure physique "
                "(issue #73) ; relancer la simulation avec --archiver-tous 1 (par defaut)."
            )
        dt = self.dt_simulation
        if dt is None:
            raise ValueError(
                f"{observable} refuse une trajectoire sans "
                "metadonnees['archivage']['dt_simulation_s'] permettant de verifier "
                "que tous les pas physiques sont presents (issue #73)."
            )
        if self.t.size >= 2:
            ecart_max = float(np.max(np.diff(self.t)))
            if ecart_max > dt * (1.0 + 1e-6):
                raise ValueError(
                    f"{observable} refuse une archive espacee "
                    f"(ecart temporel max {ecart_max:.4g} s > dt_simulation_s = {dt:.4g} s) : "
                    "des pas intermediaires manquent (issue #73)."
                )


def charger_et_valider_complete(
    source: Trajectoire | str | Path, observable: str = "le calcul d'observable"
) -> Trajectoire:
    """Charge ou valide une archive, en exigeant un enregistrement complet (K = 1)."""
    if isinstance(source, Trajectoire):
        source.exiger_complete(observable)
        return source
    if isinstance(source, (str, Path)):
        trajectoire = lire_trajectoire(source)
        trajectoire.exiger_complete(observable)
        return trajectoire
    raise TypeError(
        f"source de trajectoire invalide (attendu Trajectoire, str ou Path, "
        f"recu {type(source).__name__})"
    )


def ecrire_trajectoire(chemin: str | Path, donnees: Trajectoire) -> None:
    """Cree une archive sans ecraser un resultat existant, apres validation."""
    donnees = Trajectoire(**vars(donnees))
    chemin = Path(chemin)
    if chemin.suffix != ".npz":
        raise ValueError("la trajectoire doit porter l'extension .npz")
    contenu = json.dumps(donnees.metadonnees, ensure_ascii=False, sort_keys=True, allow_nan=False)
    facultatifs = {} if donnees.etats is None else {"etats": donnees.etats}
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
            **facultatifs,
        )


def lire_trajectoire(chemin: str | Path) -> Trajectoire:
    """Relit et controle les formes, valeurs finies et version avant les observables."""
    with np.load(chemin, allow_pickle=False) as archive:
        if set(archive.files) not in (_CHAMPS, _CHAMPS | {"etats"}):
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
            etats=archive["etats"] if "etats" in archive.files else None,
        )
