"""Modele de chutes, d'effet domino, de relevage et de contournement local.

Addendum a la specification (docs/modele-chutes.md). Ce module enrichit la
dynamique des pietons en integrant :

  1. Chutes par glissade (perte d'adherence) : declenchees lorsque l'acceleration
     demandee |s - v| / tau depasse l'adherence offerte par le sol a_max. La
     probabilite de chute par pas est 1 - exp(-lambda_chute * exces * dt),
     invariante par changement de pas de temps (section 1 de la spec).
  2. Obstacle au sol : un agent a terre arrete de se diriger vers la sortie
     (vitesse desiree nulle) et voit son emprise au sol etendue
     (r_effectif = facteur_rayon_terre * r, soit 1,5 * r par defaut).
  3. Effet domino / trebuchement en cascade : un pieton en mouvement rapide qui
     arrive sur une personne a terre a une distance inferieure a sa distance
     d'arret physique ne peut pas freiner a temps et a une probabilite elevee de
     glisser ou trebucher a son tour.
  4. Contournement local reactif : un pieton debout suffisamment eloigne
     decouvre l'obstacle dans sa portee de perception et devie tangentiellement
     sa vitesse desiree pour contourner la personne a terre sans recalculer le
     champ eikonal global.
  5. Relevage stochastique : duree au sol tiree selon une distribution
     log-normale de mediane 3,7 s (sourcee Becker et al. 2016).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from viscocrowd.core.rng import generateur


@dataclass(frozen=True)
class ParametresChutes:
    """Parametres physiques et stochastiques du module de chutes."""

    lambda_chute: float = 2.0
    lambda_domino: float = 4.0
    facteur_rayon_terre: float = 1.5
    mediane_relevage: float = 3.7
    sigma_relevage: float = 0.5
    distance_perception: float = 2.5
    force_contournement: float = 1.2

    def __post_init__(self) -> None:
        for nom in (
            "lambda_chute",
            "lambda_domino",
            "facteur_rayon_terre",
            "mediane_relevage",
            "sigma_relevage",
            "distance_perception",
            "force_contournement",
        ):
            valeur = getattr(self, nom)
            if not (isinstance(valeur, (int, float)) and np.isfinite(valeur) and valeur > 0):
                raise ValueError(f"{nom} doit etre un nombre reel strictement positif fini")
        if self.facteur_rayon_terre < 1.0:
            raise ValueError("facteur_rayon_terre doit etre superieur ou egal a 1.0")


@dataclass(frozen=True)
class EvenementChute:
    """Enregistrement d'un evenement de chute."""

    agent: int
    instant: float
    cause: str
    duree_relevage: float
    position: tuple[float, float]


class GestionnaireChutes:
    """Gere l'etat des chutes, le contournement et le relevage d'une population."""

    def __init__(self, n_agents: int, parametres: ParametresChutes, graine: int) -> None:
        if type(n_agents) is not int or n_agents < 1:
            raise ValueError("n_agents doit etre un entier strictement positif")
        self.n_agents = n_agents
        self.parametres = parametres
        self.rng = generateur(graine)

        self._a_terre = np.zeros(n_agents, dtype=bool)
        self._fin_relevage = np.full(n_agents, np.nan)
        self._positions_terre: dict[int, tuple[float, float]] = {}
        self._debut_chute: dict[int, float] = {}
        self._historique: list[EvenementChute] = []

    @property
    def a_terre(self) -> np.ndarray:
        """(N,) masque booleen des agents actuellement au sol."""
        return self._a_terre.copy()

    @property
    def nombre_a_terre(self) -> int:
        """Nombre d'agents actuellement a terre."""
        return int(np.sum(self._a_terre))

    @property
    def historique(self) -> tuple[EvenementChute, ...]:
        """Historique chronologique de toutes les chutes survenues."""
        return tuple(self._historique)

    def faire_tomber(
        self, agent: int, instant: float, cause: str, position: tuple[float, float]
    ) -> None:
        """Provoque explicitement la chute d'un agent."""
        if self._a_terre[agent]:
            return
        mu = math.log(self.parametres.mediane_relevage)
        z = float(self.rng.normal(0.0, 1.0))
        duree = math.exp(mu + self.parametres.sigma_relevage * z)

        self._a_terre[agent] = True
        self._fin_relevage[agent] = instant + duree
        self._positions_terre[agent] = position
        self._debut_chute[agent] = instant
        self._historique.append(
            EvenementChute(
                agent=agent,
                instant=instant,
                cause=cause,
                duree_relevage=duree,
                position=position,
            )
        )

    def rayons_effectifs(
        self, rayons_nominaux: np.ndarray, instant: float | None = None
    ) -> np.ndarray:
        """Rayons physiques d'exclusion : augmentes pour les corps allonges au sol.

        Si instant est fourni, l'expansion s'etale sur une courte duree d'affaissement
        (0.25 s) pour eviter une reaction discontinue brutale aux parois.
        """
        rayons = np.array(rayons_nominaux, dtype=float, copy=True)
        if not np.any(self._a_terre):
            return rayons

        facteur = self.parametres.facteur_rayon_terre
        indices_terre = np.flatnonzero(self._a_terre)
        if instant is None:
            rayons[indices_terre] *= facteur
        else:
            duree_affaissement = 0.25
            for ag in indices_terre:
                t0 = self._debut_chute.get(ag, instant)
                progression = min(1.0, max(0.0, (instant - t0) / duree_affaissement))
                rayons[ag] *= 1.0 + (facteur - 1.0) * progression
        return rayons

    def vitesses_desirees_effectives(
        self,
        x: np.ndarray,
        vitesse_desiree_nominale: np.ndarray,
        rayons_nominaux: np.ndarray,
        indices: np.ndarray | None = None,
    ) -> np.ndarray:
        """Calcule les vitesses desirees en annulant celles au sol et en deviant les debout."""
        vd = np.array(vitesse_desiree_nominale, dtype=float, copy=True)
        idx = np.asarray(indices) if indices is not None else np.arange(vd.shape[0])

        # 1. Annuler la vitesse desiree des agents a terre
        terre_dans_groupe = self._a_terre[idx]
        vd[terre_dans_groupe] = 0.0

        if not self._positions_terre:
            return vd

        debout_locaux = np.flatnonzero(~terre_dans_groupe)
        if debout_locaux.size == 0:
            return vd

        p = self.parametres
        pos_terre = np.array(list(self._positions_terre.values()))
        # Rayon au sol de reference
        r_terre_ref = np.mean(rayons_nominaux) * p.facteur_rayon_terre

        for loc in debout_locaux:
            si = vd[loc]
            norme_s = float(np.linalg.norm(si))
            if norme_s < 1e-9:
                continue

            xi = x[loc]
            deltas = pos_terre - xi
            distances = np.hypot(deltas[:, 0], deltas[:, 1])
            distances_nettes = distances - rayons_nominaux[loc] - r_terre_ref
            pertinents = (distances > 1e-6) & (distances_nettes < p.distance_perception)
            if not np.any(pertinents):
                continue

            deviation = np.zeros(2, dtype=float)
            for k in np.flatnonzero(pertinents):
                d = distances[k]
                u = deltas[k] / d
                alignement = float(np.dot(si, u))
                if alignement <= 0.0:
                    continue

                t_esquive = np.array([-u[1], u[0]])
                if np.dot(si, t_esquive) < 0:
                    t_esquive = -t_esquive

                poids = (
                    p.force_contournement
                    * ((p.distance_perception - distances_nettes[k]) / p.distance_perception) ** 2
                )
                deviation += poids * t_esquive

            if np.linalg.norm(deviation) > 1e-9:
                s_modifie = si + deviation * norme_s
                norme_modifiee = np.linalg.norm(s_modifie)
                if norme_modifiee > 1e-9:
                    vd[loc] = (s_modifie / norme_modifiee) * norme_s

        return vd

    def mettre_a_jour(
        self,
        instant: float,
        dt: float,
        x: np.ndarray,
        v: np.ndarray,
        vitesse_desiree: np.ndarray,
        a_max: np.ndarray,
        tau: np.ndarray,
        rayons_nominaux: np.ndarray,
        indices: np.ndarray | None = None,
    ) -> list[EvenementChute]:
        """Met a jour le relevage, evalue les glissades et les trebuchements en cascade."""
        nouvelles_chutes: list[EvenementChute] = []
        idx = np.asarray(indices) if indices is not None else np.arange(x.shape[0])

        # 1. Relevage des agents du groupe dont le temps est ecoule
        for ag in idx:
            if self._a_terre[ag] and instant >= self._fin_relevage[ag] - 1e-12:
                self._a_terre[ag] = False
                self._fin_relevage[ag] = np.nan
                self._positions_terre.pop(ag, None)
                self._debut_chute.pop(ag, None)

        debout_masque = ~self._a_terre[idx]
        locaux_debout = np.flatnonzero(debout_masque)
        if locaux_debout.size == 0:
            return nouvelles_chutes

        # 2. Chutes par perte d'adherence (glissade pure)
        deltas_v = vitesse_desiree[locaux_debout] - v[locaux_debout]
        a_demandee = np.hypot(deltas_v[:, 0], deltas_v[:, 1]) / tau[locaux_debout]
        adherence_sol = a_max[locaux_debout]

        exces = np.maximum(0.0, a_demandee / adherence_sol - 1.0)
        p_chute = 1.0 - np.exp(-self.parametres.lambda_chute * exces * dt)
        tirages_glissade = self.rng.uniform(0.0, 1.0, size=locaux_debout.size)

        glissades_loc = locaux_debout[tirages_glissade < p_chute]
        for loc in glissades_loc:
            ag_global = int(idx[loc])
            pos = (float(x[loc, 0]), float(x[loc, 1]))
            self.faire_tomber(ag_global, instant, "glissade", pos)
            nouvelles_chutes.append(self._historique[-1])

        # 3. Effet domino / trebuchement en cascade
        if self._positions_terre:
            pos_terre = np.array(list(self._positions_terre.values()))
            r_terre_ref = np.mean(rayons_nominaux) * self.parametres.facteur_rayon_terre

            # Re-evaluer les agents encore debout apres les glissades
            encore_debout_loc = [loc for loc in locaux_debout if not self._a_terre[idx[loc]]]
            for loc in encore_debout_loc:
                vi = v[loc]
                v_norme = float(np.linalg.norm(vi))
                if v_norme < 0.1:
                    continue

                d_arret = (v_norme**2) / (2.0 * a_max[loc])
                xi = x[loc]
                deltas = pos_terre - xi
                dist = np.hypot(deltas[:, 0], deltas[:, 1])
                dist_bord = dist - rayons_nominaux[loc] - r_terre_ref

                approchant = False
                pire_urgence = 0.0
                for k in range(pos_terre.shape[0]):
                    if dist[k] < 1e-6:
                        continue
                    u = deltas[k] / dist[k]
                    v_proj = float(np.dot(vi, u))
                    if v_proj > 0.05 and dist_bord[k] < d_arret:
                        approchant = True
                        urgence = 1.0 - max(0.0, dist_bord[k]) / max(d_arret, 1e-6)
                        pire_urgence = max(pire_urgence, urgence)

                if approchant and pire_urgence > 0.0:
                    p_domino = 1.0 - math.exp(-self.parametres.lambda_domino * pire_urgence * dt)
                    if self.rng.uniform(0.0, 1.0) < p_domino:
                        ag_global = int(idx[loc])
                        pos = (float(x[loc, 0]), float(x[loc, 1]))
                        self.faire_tomber(ag_global, instant, "domino", pos)
                        nouvelles_chutes.append(self._historique[-1])

        return nouvelles_chutes
