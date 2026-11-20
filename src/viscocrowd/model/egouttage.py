"""Trainee d'eau : les baigneurs mouillent la plage en la traversant (facultatif).

Un baigneur qui sort de l'eau ruisselle : il emporte un `volume` d'eau (L) qu'il
perd en s'egouttant, de plus en plus lentement. On le depose sur la case de plage
sous son centre, a chaque pas :

    depot = volume / duree * exp(-(t - t_sortie) / duree) * dt          (L)

ou t_sortie est l'instant ou il a ete pose sur la plage. L'integrale sur tout le
trajet vaut `volume`. Le carrelage d'une case devient MOUILLE quand le film d'eau
cumule depasse `seuil` (L/m^2, soit mm).

C'est le seuil qui porte l'intuition « un seul baigneur ne change rien, cent
rendent le passage glissant » : un baigneur seul etale son eau sur tout son
trajet et reste sous le seuil ; la ou les trajets se superposent (sortie des
echelles, approche de la porte), l'eau s'accumule et le seuil est franchi.
L'eau ne seche pas : une evacuation dure environ une minute, bien moins que le
sechage d'un carrelage.

Ce qui change, et ce qui ne change pas :
  - le milieu sous chaque agent (adherence, vitesse souhaitee, relaxation) est lu
    sur cette carte a chaque pas, comme la carte statique ; le module de chutes
    voit donc aussi les cases mouillees (glissade) ;
  - le guidage reste calcule une fois, sur la carte statique : les agents ne
    savent pas que la trainee est glissante et ne la contournent pas ;
  - une case deja MOUILLE (bande autour du bassin) ou EAU ne change pas.

Valeurs par defaut : HYPOTHESES sans source, a balayer avant toute conclusion.
"""

from __future__ import annotations

from collections.abc import Callable

import numpy as np

from viscocrowd.core.verifications import exiger_fini, exiger_scalaire_fini
from viscocrowd.model.milieu import Milieu


class ChampEgouttage:
    """Eau deposee sur la plage, en L/m^2, et carte des milieux qui en tient compte.

    Objet appelable comme une carte : (N, 2) positions -> (N,) milieux.

    Attributes:
        eau: (nx, ny) film d'eau de chaque case, en L/m^2.
        pas: cote d'une case, en m.
        seuil: film a partir duquel une case seche devient MOUILLE, en L/m^2.
    """

    def __init__(
        self,
        carte: Callable[[np.ndarray], np.ndarray],
        longueur: float,
        largeur: float,
        pas: float,
        seuil: float,
    ) -> None:
        """
        Args:
            carte: carte statique des milieux, (N, 2) -> (N,).
            longueur, largeur: emprise couverte par la grille, en m (depuis 0).
            pas: cote d'une case, en m.
            seuil: film d'eau qui rend une case MOUILLE, en L/m^2.
        """
        for nom, valeur in (("longueur", longueur), ("largeur", largeur), ("pas", pas)):
            exiger_scalaire_fini(nom, valeur, strictement_positif=True)
        exiger_scalaire_fini("seuil", seuil, strictement_positif=True)
        self.carte, self.pas, self.seuil = carte, float(pas), float(seuil)
        self.eau = np.zeros((int(np.ceil(longueur / pas)) + 1, int(np.ceil(largeur / pas)) + 1))

    def _cases(self, x: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        nx, ny = self.eau.shape
        i = np.clip(np.floor(x[:, 0] / self.pas), 0, nx - 1).astype(np.int64)
        j = np.clip(np.floor(x[:, 1] / self.pas), 0, ny - 1).astype(np.int64)
        return i, j

    def deposer(self, x: np.ndarray, volumes: np.ndarray, rayons: np.ndarray | None = None) -> None:
        """Ajoute `volumes` (M,) litres sous les positions `x` (M, 2).

        Avec `rayons` (M,), en m, le volume est reparti a parts egales sur les cases dont le
        centre est a moins du rayon : l'empreinte du baigneur. Sans cela, le film laisse par
        un passage valait q / (v pas) et dependait de la taille des cases, un parametre
        numerique (revue de #165) ; reparti, il vaut environ 2 q / (pi r v), quelle que soit
        la grille des que `pas` < r. Une empreinte qui ne contient aucun centre de case
        (cases plus grandes que le baigneur) retombe sur la case sous le centre. Sans
        `rayons`, tout va sur la case sous le centre.
        """
        x, volumes = np.asarray(x, dtype=float).reshape(-1, 2), np.asarray(volumes, dtype=float)
        exiger_fini(x=x, volumes=volumes)
        if volumes.shape != (x.shape[0],) or np.any(volumes < 0):
            raise ValueError("volumes doit donner un volume positif ou nul par position")
        i, j = self._cases(x)
        if rayons is None:
            np.add.at(self.eau, (i, j), volumes / self.pas**2)
            return
        rayons = np.asarray(rayons, dtype=float).reshape(-1)
        exiger_fini(rayons=rayons)
        if rayons.shape != volumes.shape or np.any(rayons <= 0):
            raise ValueError("rayons doit donner un rayon strictement positif par position")
        nx, ny = self.eau.shape
        portee = int(np.ceil(rayons.max() / self.pas)) + 1
        decalages = np.arange(-portee, portee + 1)
        di, dj = (a.ravel() for a in np.meshgrid(decalages, decalages, indexing="ij"))
        ci, cj = i[:, None] + di[None, :], j[:, None] + dj[None, :]  # (M, K) cases voisines
        dx = (ci + 0.5) * self.pas - x[:, 0:1]
        dy = (cj + 0.5) * self.pas - x[:, 1:2]
        dedans = (dx**2 + dy**2 <= rayons[:, None] ** 2) & (ci >= 0) & (ci < nx)
        dedans &= (cj >= 0) & (cj < ny)
        vides = ~dedans.any(axis=1)
        dedans[vides] = (di == 0) & (dj == 0)  # repli : la case sous le centre
        poids = dedans / dedans.sum(axis=1, keepdims=True)
        lignes, colonnes = np.nonzero(dedans)
        np.add.at(
            self.eau,
            (ci[lignes, colonnes], cj[lignes, colonnes]),
            volumes[lignes] * poids[lignes, colonnes] / self.pas**2,
        )

    def mouille(self, x: np.ndarray) -> np.ndarray:
        """(N,) vrai la ou le film depasse le seuil."""
        i, j = self._cases(np.asarray(x, dtype=float).reshape(-1, 2))
        return self.eau[i, j] >= self.seuil

    def __call__(self, x: np.ndarray) -> np.ndarray:
        milieu = np.array(self.carte(x), copy=True)
        milieu[(milieu == Milieu.SEC) & self.mouille(x)] = Milieu.MOUILLE
        return milieu

    def fraction_mouillee(self, sec: np.ndarray) -> float:
        """Part des cases seches de la carte statique (`sec`, (nx, ny)) passees MOUILLE."""
        n = int(np.sum(sec))
        return float(np.sum(sec & (self.eau >= self.seuil)) / n) if n else 0.0

    def centres(self) -> np.ndarray:
        """(nx, ny, 2) centres des cases, en m."""
        nx, ny = self.eau.shape
        xs, ys = (np.arange(nx) + 0.5) * self.pas, (np.arange(ny) + 0.5) * self.pas
        return np.stack(np.meshgrid(xs, ys, indexing="ij"), axis=-1)


def debit_egouttage(volume: float, duree: float, depuis: np.ndarray) -> np.ndarray:
    """Debit d'eau perdu (L/s) par des baigneurs sortis depuis `depuis` (N,) s."""
    return volume / duree * np.exp(-np.asarray(depuis, dtype=float) / duree)
