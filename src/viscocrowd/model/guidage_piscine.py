"""Guidage de la piscine : un seul temps de parcours, de l'eau jusqu'a la porte (spec § 2.6).

Deux champs eikonaux, calcules une fois :

  1. SUR LA PLAGE, phi_plage(x) : temps minimal jusqu'a la porte, a la vitesse du
     milieu sous x (mouille ou sec), le bassin etant un obstacle gonfle d'un rayon.
  2. DANS L'EAU, phi_eau(x) : temps minimal pour sortir de la piscine en passant par
     un site de franchissement. Chaque site k est une source de temps initial

        phi_eau(attente_k) = T_k + phi_plage(arrivee_k)

     ou T_k est la duree du franchissement (rebord ou echelle). phi_eau est donc le
     temps TOTAL jusqu'a la porte, et chaque point de l'eau choisit le site qui le
     minimise : nager plus longtemps vers une echelle rapide, ou sortir par le
     rebord tout proche mais lent.

Le partage du flux entre rebord et echelles n'est ainsi pas impose : il emerge des
vitesses, des durees de franchissement et de la geometrie, comme le demande la
spec § 2.6. Le champ est statique : il ignore l'attente devant un site occupe.

Un agent dont le centre est dans le rectangle du bassin suit phi_eau, les autres
suivent phi_plage. Un agent arrive a son point d'attente recoit une direction
nulle : c'est le scenario qui declenche alors le franchissement.
"""

from __future__ import annotations

from collections.abc import Mapping

import numpy as np

from viscocrowd.core.state import State
from viscocrowd.core.verifications import exiger_scalaire_fini
from viscocrowd.geometry.piscine import NATURES, Piscine
from viscocrowd.model.carte import CartePiscine
from viscocrowd.model.eikonal import ChampEikonal, GrilleReguliere
from viscocrowd.model.milieu import Milieu, ParametresMilieu


class GuidagePiscine:
    """Champs phi_plage et phi_eau, et direction de guidage de chaque agent.

    Attributes:
        plage, eau: les deux champs eikonaux.
        sites: les sites de franchissement de la piscine.
        temps_sites: (K,) temps total jusqu'a la porte depuis le point d'attente
            de chaque site, en s : T_k + phi_plage(arrivee_k).
    """

    def __init__(
        self,
        piscine: Piscine,
        parametres: Mapping[Milieu, ParametresMilieu],
        rayon: float,
        pas: float,
        durees: Mapping[str, float],
        facteur_vitesse: float = 1.0,
    ) -> None:
        """
        Args:
            piscine: la geometrie.
            parametres: parametres des trois milieux ; seule la vitesse s sert ici.
            rayon: rayon des agents, en m ; marge autour des murs et du bassin.
            pas: pas des grilles, en m ; au plus le rayon.
            durees: duree du franchissement par nature de site, en s.
            facteur_vitesse: facteur de panique, applique comme dans le moteur.
        """
        exiger_scalaire_fini("rayon", rayon, strictement_positif=True)
        exiger_scalaire_fini("pas", pas, strictement_positif=True)
        exiger_scalaire_fini("facteur_vitesse", facteur_vitesse, strictement_positif=True)
        if pas > rayon:
            raise ValueError("le pas des grilles doit etre inferieur ou egal au rayon")
        if set(durees) != set(NATURES) or not all(
            np.isfinite(d) and d >= 0.0 for d in durees.values()
        ):
            raise ValueError(f"durees doit donner un temps fini positif pour {NATURES}")
        manquants = {Milieu.EAU, Milieu.MOUILLE, Milieu.SEC} - {Milieu(m) for m in parametres}
        if manquants:
            raise ValueError(f"parametres manquants pour {sorted(m.name for m in manquants)}")

        self.piscine, self.rayon = piscine, rayon
        piscine.valider_rayons(np.array([rayon]))
        self.sites = piscine.sites()
        if not self.sites:
            raise ValueError("la piscine doit proposer au moins un site de franchissement")
        attentes = np.array([s.attente(rayon) for s in self.sites])
        arrivees = np.array([s.arrivee(rayon) for s in self.sites])
        points_sites = np.concatenate((attentes, arrivees))
        tolerance_arrondi = (
            64 * np.finfo(float).eps * max(piscine.longueur_emprise, piscine.largeur_emprise, 1.0)
        )
        if (
            not np.all(piscine.dans_bassin(attentes))
            or np.any(piscine.dans_bassin(arrivees))
            or piscine.violation(points_sites, np.full(len(points_sites), rayon), 0.0)
            > tolerance_arrondi
        ):
            raise ValueError("un site de franchissement n'a pas d'attente ou d'arrivee admissible")
        vitesse = {Milieu(m): facteur_vitesse * p.vitesse for m, p in parametres.items()}
        carte = CartePiscine(piscine)

        # 1. Plage : emprise et couloir de la porte, hors du bassin gonfle d'un rayon.
        L, W = piscine.longueur_emprise, piscine.largeur_emprise
        grille = GrilleReguliere.couvrant(0.0, L + piscine.profondeur_porte, 0.0, W, pas)
        points = grille.noeuds().reshape(-1, 2)
        r = np.full(points.shape[0], rayon)
        sur_plage = (np.hypot(*(piscine.projeter_plage(points, r) - points).T) <= 1e-12) & (
            piscine.bassin.distance(points) >= rayon - 1e-9
        )  # arrondis : 3 - 2,8 < 0,2
        table = np.zeros(max(Milieu) + 1)
        for milieu, s in vitesse.items():
            table[milieu] = s
        F = np.where(sur_plage, table[carte(points)], 0.0)
        sortie = sur_plage & (points[:, 0] >= L)
        self.plage = ChampEikonal.depuis_tableaux(
            grille, F.reshape(grille.forme), sortie.reshape(grille.forme)
        )

        # 2. Eau : bassin reduit d'un rayon ; une source par site, au noeud libre le
        # plus proche de son point d'attente.
        b = piscine.bassin
        grille_eau = GrilleReguliere.couvrant(b.x_min, b.x_max, b.y_min, b.y_max, pas)
        noeuds = grille_eau.noeuds().reshape(-1, 2)
        libre = (
            (noeuds[:, 0] >= b.x_min + rayon - 1e-12)
            & (noeuds[:, 0] <= b.x_max - rayon + 1e-12)
            & (noeuds[:, 1] >= b.y_min + rayon - 1e-12)
            & (noeuds[:, 1] <= b.y_max - rayon + 1e-12)
        )
        indices_libres = np.flatnonzero(libre)
        self.temps_sites = np.array([durees[s.nature] for s in self.sites]) + self.plage.temps(
            arrivees
        )
        if not np.all(np.isfinite(self.temps_sites)):
            raise ValueError("un site debouche sur une plage sans chemin vers la porte")
        sources = np.zeros(noeuds.shape[0], dtype=bool)
        temps = np.full(noeuds.shape[0], np.inf)
        for site, total in zip(self.sites, self.temps_sites, strict=True):
            k = indices_libres[
                np.argmin(np.hypot(*(noeuds[indices_libres] - site.attente(rayon)).T))
            ]
            sources[k] = True
            temps[k] = min(temps[k], total)
        F_eau = np.where(libre, vitesse[Milieu.EAU], 0.0)
        self.eau = ChampEikonal.depuis_tableaux(
            grille_eau,
            F_eau.reshape(grille_eau.forme),
            sources.reshape(grille_eau.forme),
            np.where(sources, temps, 0.0).reshape(grille_eau.forme),
        )

    def direction(self, x: np.ndarray) -> np.ndarray:
        """Direction (N, 2) : champ de l'eau dans le bassin, de la plage ailleurs."""
        x = np.asarray(x, dtype=float)
        eau = self.piscine.dans_bassin(x)
        e = np.zeros_like(x)
        if np.any(eau):
            e[eau] = self.eau.direction(x[eau])
        if np.any(~eau):
            e[~eau] = self.plage.direction(x[~eau])
        return e

    def temps(self, x: np.ndarray) -> np.ndarray:
        """Temps estime (N,) jusqu'a la porte, en s, depuis chaque position."""
        x = np.asarray(x, dtype=float)
        eau = self.piscine.dans_bassin(x)
        t = np.empty(x.shape[0])
        if np.any(eau):
            t[eau] = self.eau.temps(x[eau])
        if np.any(~eau):
            t[~eau] = self.plage.temps(x[~eau])
        return t

    def __call__(self, etat: State) -> np.ndarray:
        return self.direction(etat.x)
