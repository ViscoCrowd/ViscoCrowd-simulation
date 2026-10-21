"""Geometrie commune de la piscine (tache C6) : bassin, plages, porte et sites de franchissement.

Le plan reprend `ui.parametres.DimensionsPlan` : un bassin rectangulaire entoure
de plages, dans une emprise rectangulaire, avec une porte unique au milieu du mur
de droite. Coordonnees en metres, origine au coin bas-gauche de l'emprise.

    y
    ^   +---------------------------------------------+
    |   |  plage             echelle            plage  |
    |   |     +---------------------+                  |
    |   |     |       bassin        |                  porte  -> dehors
    |   |     +---------------------+                  |
    |   |                   echelle                    |
    |   +---------------------------------------------+   -> x

Deux populations, separees par le bord du bassin, qui est un mur pour toutes deux :

  - les agents DANS L'EAU restent dans le bassin, a un rayon de son bord ;
  - les agents SUR LA PLAGE restent dans l'emprise, hors du bassin, et ne passent
    le mur de droite que par la porte.

On ne passe de l'un a l'autre que par un SITE DE FRANCHISSEMENT : les echelles,
rares et rapides, et le rebord, decoupe en sites tous les `pas_rebord` metres,
lents. Chaque site a une capacite de un agent (spec § 2.7) ; sa dynamique vit
dans le scenario.

Le cote d'un agent se lit sur la position de son centre (dans le rectangle du
bassin ou non). C'est sans ambiguite : un centre reste a un rayon au moins du
bord de son cote, et ne peut pas le franchir en un pas, limite a r/5 par le
scenario. Projeter sur le cote ou se trouve le centre revient alors a projeter
sur la plus proche des deux pieces de l'ensemble admissible.

La porte est un couloir de la largeur de la porte qui traverse le mur. Les
centres admissibles de la plage sont l'union de l'emprise reduite d'un rayon et
de ce couloir reduit d'un rayon ; on projette sur la plus proche des deux pieces
(projection exacte sur une union de convexes), puis hors du bassin. Pres des
montants de la porte, cette union est un peu plus stricte que l'ensemble exact
(qui arrondirait les coins) : aucun disque ne touche un mur, au prix d'un passage
legerement plus etroit aux montants.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from viscocrowd.core.verifications import exiger_fini, exiger_scalaire_fini
from viscocrowd.geometry.obstacle import ObstacleRectangle

COTES = ("bas", "haut", "gauche", "droite")
NATURES = ("rebord", "echelle")


@dataclass(frozen=True)
class SiteFranchissement:
    """Point du bord du bassin ou l'on sort de l'eau, un agent a la fois.

    Attributes:
        indice: numero du site.
        nature: "rebord" ou "echelle".
        position: point du bord, (2,), en m.
        normale: unitaire, du bassin vers la plage, (2,).
    """

    indice: int
    nature: str
    position: np.ndarray
    normale: np.ndarray

    def attente(self, rayon: float) -> np.ndarray:
        """Centre d'un agent qui attend ce site, dans l'eau, au contact du bord (m)."""
        return self.position - rayon * self.normale

    def arrivee(self, rayon: float) -> np.ndarray:
        """Centre d'un agent qui vient de franchir ce site, sur la plage (m)."""
        return self.position + rayon * self.normale


@dataclass(frozen=True)
class Piscine:
    """Dimensions en metres, toutes explicites (configuration YAML du scenario).

    `echelles` : couples (cote, fraction) ; le cote parmi "bas", "haut", "gauche",
    "droite", la fraction de 0 a 1 le long de ce cote, de gauche a droite ou de bas
    en haut. `largeur_mouillee` : bande de carrelage mouille autour du bassin.
    """

    longueur_bassin: float
    largeur_bassin: float
    plage_gauche: float
    plage_verticale: float
    plage_sortie: float
    largeur_porte: float
    profondeur_porte: float
    largeur_mouillee: float
    pas_rebord: float
    largeur_echelle: float
    echelles: tuple[tuple[str, float], ...]

    def __post_init__(self) -> None:
        for nom in (
            "longueur_bassin",
            "largeur_bassin",
            "plage_gauche",
            "plage_verticale",
            "plage_sortie",
            "largeur_porte",
            "profondeur_porte",
            "pas_rebord",
            "largeur_echelle",
        ):
            exiger_scalaire_fini(nom, getattr(self, nom), strictement_positif=True)
        exiger_scalaire_fini("largeur_mouillee", self.largeur_mouillee)
        if not self.largeur_mouillee >= 0.0:
            raise ValueError("largeur_mouillee doit etre positive ou nulle")
        if self.largeur_porte >= self.largeur_emprise:
            raise ValueError("la porte doit tenir dans le mur de droite")
        echelles = []
        for cote, fraction in self.echelles:
            if cote not in COTES:
                raise ValueError(f"cote d'echelle inconnu {cote!r} ; attendu : {COTES}")
            if not (np.isfinite(fraction) and 0.0 < fraction < 1.0):
                raise ValueError("la fraction d'une echelle doit etre dans ]0, 1[")
            echelles.append((cote, float(fraction)))
        object.__setattr__(self, "echelles", tuple(echelles))

    # --- Rectangles ------------------------------------------------------------

    @property
    def longueur_emprise(self) -> float:
        return self.plage_gauche + self.longueur_bassin + self.plage_sortie

    @property
    def largeur_emprise(self) -> float:
        return self.largeur_bassin + 2 * self.plage_verticale

    @property
    def bassin(self) -> ObstacleRectangle:
        """Le bassin, vu de la plage : un obstacle."""
        return ObstacleRectangle(
            self.plage_gauche,
            self.plage_gauche + self.longueur_bassin,
            self.plage_verticale,
            self.plage_verticale + self.largeur_bassin,
        )

    @property
    def porte(self) -> tuple[np.ndarray, np.ndarray]:
        """Segment de la porte, oriente pour compter positivement les sorties (vers +x)."""
        x, yc = self.longueur_emprise, self.largeur_emprise / 2
        return np.array([x, yc - self.largeur_porte / 2]), np.array(
            [x, yc + self.largeur_porte / 2]
        )

    def dans_bassin(self, x: np.ndarray) -> np.ndarray:
        """Vrai (N,) pour les centres (N, 2) situes dans le rectangle du bassin."""
        b = self.bassin
        x = np.asarray(x, dtype=float)
        return (x[:, 0] > b.x_min) & (x[:, 0] < b.x_max) & (x[:, 1] > b.y_min) & (x[:, 1] < b.y_max)

    # --- Sites -----------------------------------------------------------------

    def _cote(self, cote: str) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Origine, direction unitaire et normale sortante d'un cote du bassin."""
        b = self.bassin
        if cote == "bas":
            return np.array([b.x_min, b.y_min]), np.array([1.0, 0.0]), np.array([0.0, -1.0])
        if cote == "haut":
            return np.array([b.x_min, b.y_max]), np.array([1.0, 0.0]), np.array([0.0, 1.0])
        if cote == "gauche":
            return np.array([b.x_min, b.y_min]), np.array([0.0, 1.0]), np.array([-1.0, 0.0])
        return np.array([b.x_max, b.y_min]), np.array([0.0, 1.0]), np.array([1.0, 0.0])

    def sites(self) -> tuple[SiteFranchissement, ...]:
        """Echelles, puis sites de rebord tous les `pas_rebord` hors des echelles et des coins."""
        sites: list[SiteFranchissement] = []
        echelles_par_cote: dict[str, list[float]] = {c: [] for c in COTES}
        for cote, fraction in self.echelles:
            origine, direction, normale = self._cote(cote)
            longueur = self.longueur_bassin if cote in ("bas", "haut") else self.largeur_bassin
            abscisse = fraction * longueur
            echelles_par_cote[cote].append(abscisse)
            sites.append(
                SiteFranchissement(len(sites), "echelle", origine + abscisse * direction, normale)
            )
        for cote in COTES:
            origine, direction, normale = self._cote(cote)
            longueur = self.longueur_bassin if cote in ("bas", "haut") else self.largeur_bassin
            # Un site par intervalle de pas_rebord, centre ; aucun dans un coin.
            n = int(np.floor(longueur / self.pas_rebord + 1e-9))
            for k in range(n):
                abscisse = (k + 0.5) * longueur / n
                libre = all(
                    abs(abscisse - e) >= (self.largeur_echelle + self.pas_rebord) / 2
                    for e in echelles_par_cote[cote]
                )
                if libre:
                    sites.append(
                        SiteFranchissement(
                            len(sites), "rebord", origine + abscisse * direction, normale
                        )
                    )
        return tuple(sites)

    # --- Projection ------------------------------------------------------------

    def valider_rayons(self, r: np.ndarray) -> None:
        """Refuser une geometrie trop etroite pour les disques, avant toute projection."""
        r = np.asarray(r, dtype=float)
        exiger_fini(r=r)
        if np.any(r <= 0.0) or np.any(2 * r >= self.largeur_porte):
            raise ValueError("chaque rayon doit etre positif et passer la porte")
        if np.any(2 * r > min(self.plage_gauche, self.plage_verticale, self.plage_sortie)):
            raise ValueError("chaque plage doit mesurer au moins un diametre d'agent")
        if np.any(2 * r >= min(self.longueur_bassin, self.largeur_bassin)):
            raise ValueError("le bassin doit etre plus large qu'un diametre d'agent")

    def _entrees(self, x, r):
        x, r = np.asarray(x, dtype=float), np.asarray(r, dtype=float)
        if x.ndim != 2 or x.shape[1] != 2 or r.shape != (x.shape[0],):
            raise ValueError("x et r doivent etre de formes (N, 2) et (N,)")
        exiger_fini(x=x, r=r)
        self.valider_rayons(r)
        return x, r

    def projeter_plage(self, x: np.ndarray, r: np.ndarray) -> np.ndarray:
        """Projection exacte sur l'union emprise reduite et couloir de la porte (sans le bassin)."""
        x, r = self._entrees(x, r)
        L, W = self.longueur_emprise, self.largeur_emprise
        a, b = self.porte
        emprise = np.column_stack((np.clip(x[:, 0], r, L - r), np.clip(x[:, 1], r, W - r)))
        couloir = np.column_stack(
            (
                np.clip(x[:, 0], L - r, L + self.profondeur_porte),
                np.clip(x[:, 1], a[1] + r, b[1] - r),
            )
        )
        plus_proche = np.hypot(*(couloir - x).T) < np.hypot(*(emprise - x).T)
        return np.where(plus_proche[:, None], couloir, emprise)

    def projeter(self, x: np.ndarray, r: np.ndarray, t: float) -> np.ndarray:
        """Chaque centre sur son cote : bassin reduit d'un rayon, ou plage hors du bassin."""
        x, r = self._entrees(x, r)
        exiger_scalaire_fini("t", t)
        eau = self.dans_bassin(x)
        b = self.bassin
        resultat = self.projeter_plage(x, r)
        resultat = self.bassin.repousser(resultat, r)
        resultat[eau, 0] = np.clip(x[eau, 0], b.x_min + r[eau], b.x_max - r[eau])
        resultat[eau, 1] = np.clip(x[eau, 1], b.y_min + r[eau], b.y_max - r[eau])
        return resultat

    def violation(self, x: np.ndarray, r: np.ndarray, t: float) -> float:
        """Plus grand depassement (m) d'un mur, du bord du bassin ou de la porte."""
        x, r = self._entrees(x, r)
        eau = self.dans_bassin(x)
        b = self.bassin
        depassement = [0.0]
        if np.any(eau):
            xe, re = x[eau], r[eau]
            depassement.append(
                float(
                    np.max(
                        np.maximum.reduce(
                            [
                                b.x_min + re - xe[:, 0],
                                xe[:, 0] - (b.x_max - re),
                                b.y_min + re - xe[:, 1],
                                xe[:, 1] - (b.y_max - re),
                            ]
                        )
                    )
                )
            )
        if np.any(~eau):
            xp, rp = x[~eau], r[~eau]
            ecart = np.hypot(*(self.projeter_plage(xp, rp) - xp).T)
            depassement.append(float(np.max(ecart)))
            depassement.append(self.bassin.violation(xp, rp))
        return max(depassement)
