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
  4. Chute par bousculade et compression : declenchee lorsque la correction
     de projection cumulee sur le pas |x_nouveau - x_libre| / dt depasse le seuil
     seuil_bousculade (section 2 de la spec). Probabilite invariante par dt.
  5. Contournement local reactif : un pieton debout suffisamment eloigne
     decouvre l'obstacle dans sa portee de perception et devie tangentiellement
     sa vitesse desiree pour contourner la personne a terre sans recalculer le
     champ eikonal global.
  6. Relevage stochastique : duree au sol tiree selon une distribution
     log-normale de mediane 3,7 s (sourcee Becker et al. 2016).
  7. Observables dedies : taux de chute global (chutes/s), decomposition par cause,
     tailles des cascades par composantes connexes spatio-temporelles et serie temporelle
     des agents a terre.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from viscocrowd.core.rng import generateur

# Les positions initiales lisent le flux principal de la graine : les chutes ont le leur.
FLUX_CHUTES = 1


@dataclass(frozen=True)
class ParametresChutes:
    """Parametres physiques et stochastiques du module de chutes.

    Attributes:
        lambda_chute, lambda_domino, lambda_bousculade: taux de chute par unite
            d'exces, d'urgence ou de compression, en 1/s.
        facteur_rayon_terre: rayon au sol rapporte au rayon debout, sans unite.
        mediane_relevage: duree mediane au sol, en s.
        sigma_relevage: dispersion de la loi log-normale du relevage, sans unite.
        distance_perception: portee du contournement, en m.
        force_contournement: poids de la deviation, sans unite.
        duree_affaissement: duree de croissance du rayon apres la chute, en s.
        vitesse_min_domino: vitesse en dessous de laquelle on ne trebuche pas, en m/s.
        vitesse_approche_min: vitesse d'approche d'un corps, en dessous de
            laquelle il n'y a pas de risque de trebucher, en m/s.
        seuil_bousculade: seuil d'intensite de correction de projection (en m/s)
            au-dela duquel le risque de chute par bousculade apparait.
        duree_bousculade: duree d'exposition d'une bousculade, en s. Un choc ne dure
            qu'un pas de temps, quel que soit dt (mesure du 14 novembre, #130) : le
            risque d'un choc est donc compte sur cette duree fixe, et non sur dt.

    Valeurs par defaut non calibrees (docs/modele-chutes.md, section 8).
    """

    lambda_chute: float = 2.0
    lambda_domino: float = 4.0
    lambda_bousculade: float = 0.0
    facteur_rayon_terre: float = 1.5
    mediane_relevage: float = 3.7
    sigma_relevage: float = 0.5
    distance_perception: float = 2.5
    force_contournement: float = 1.2
    duree_affaissement: float = 0.25
    vitesse_min_domino: float = 0.1
    vitesse_approche_min: float = 0.05
    seuil_bousculade: float = 0.5
    duree_bousculade: float = 0.1

    def __post_init__(self) -> None:
        for nom in (
            "lambda_chute",
            "lambda_domino",
            "facteur_rayon_terre",
            "mediane_relevage",
            "sigma_relevage",
            "distance_perception",
            "force_contournement",
            "duree_affaissement",
            "vitesse_min_domino",
            "vitesse_approche_min",
            "seuil_bousculade",
            "duree_bousculade",
        ):
            valeur = getattr(self, nom)
            if not (isinstance(valeur, (int, float)) and np.isfinite(valeur) and valeur > 0):
                raise ValueError(f"{nom} doit etre un nombre reel strictement positif fini")
        if not (
            isinstance(self.lambda_bousculade, (int, float))
            and np.isfinite(self.lambda_bousculade)
            and self.lambda_bousculade >= 0.0
        ):
            raise ValueError("lambda_bousculade doit etre un nombre reel positif ou nul fini")
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
        self.rng = generateur(graine, flux=FLUX_CHUTES)

        self._a_terre = np.zeros(n_agents, dtype=bool)
        self._fin_relevage = np.full(n_agents, np.nan)
        self._positions_terre: dict[int, tuple[float, float]] = {}
        self._debut_chute: dict[int, float] = {}
        self._historique: list[EvenementChute] = []
        # Agents comprimes au-dela du seuil au pas precedent : un choc qui dure n'est
        # compte sur `duree_bousculade` qu'a son premier pas.
        self._comprime = np.zeros(n_agents, dtype=bool)

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

    def retirer(self, agent: int) -> None:
        """Oublie un agent qui a quitte le domaine : il n'est plus un obstacle."""
        self._a_terre[agent] = False
        self._fin_relevage[agent] = np.nan
        self._positions_terre.pop(agent, None)
        self._debut_chute.pop(agent, None)

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
            duree_affaissement = self.parametres.duree_affaissement
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
        correction_projection: np.ndarray | None = None,
    ) -> list[EvenementChute]:
        """Met a jour le relevage, evalue les glissades, le domino et les bousculades.

        `correction_projection` : deplacement (N, 2), en m, impose par la projection au pas
        PRECEDENT, nul pour un agent immobile pendant ce pas. Il comprend les murs, le bord
        du bassin et les obstacles, pas seulement les contacts (docs/modele-chutes.md, § 2).
        """
        nouvelles_chutes: list[EvenementChute] = []
        idx = np.asarray(indices) if indices is not None else np.arange(x.shape[0])

        # 1. Relevage des agents du groupe dont le temps est ecoule
        for ag in idx:
            if self._a_terre[ag] and instant >= self._fin_relevage[ag] - 1e-12:
                self.retirer(int(ag))

        # Un corps au sol peut etre pousse par la projection : l'obstacle le suit.
        for loc in np.flatnonzero(self._a_terre[idx]):
            self._positions_terre[int(idx[loc])] = (float(x[loc, 0]), float(x[loc, 1]))

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
                if v_norme < self.parametres.vitesse_min_domino:
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
                    if v_proj > self.parametres.vitesse_approche_min and dist_bord[k] < d_arret:
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

        # 4. Chute par bousculade et compression (section 2 de la spec)
        if correction_projection is not None and self.parametres.lambda_bousculade > 0.0:
            corr = np.asarray(correction_projection, dtype=float)
            if corr.shape == x.shape:
                corr_loc = corr[locaux_debout]
            elif corr.shape == (locaux_debout.size, 2):
                corr_loc = corr
            else:
                raise ValueError(
                    f"correction_projection de forme inattendue {corr.shape}, attendu {x.shape}"
                )

            normes_corr = np.hypot(corr_loc[:, 0], corr_loc[:, 1])
            vitesse_compression = normes_corr / dt
            exces_bousculade = np.maximum(
                0.0, vitesse_compression / self.parametres.seuil_bousculade - 1.0
            )
            # Exposition : `duree_bousculade` au premier pas d'un choc, dt aux suivants. Un
            # choc d'un seul pas (le cas mesure) a ainsi le meme risque a dt et a dt/2.
            globaux = idx[locaux_debout]
            exposition = np.where(
                self._comprime[globaux], dt, max(dt, self.parametres.duree_bousculade)
            )
            self._comprime[idx] = False
            self._comprime[globaux] = exces_bousculade > 0.0
            p_bousculade = 1.0 - np.exp(
                -self.parametres.lambda_bousculade * exces_bousculade * exposition
            )
            tirages_bousculade = self.rng.uniform(0.0, 1.0, size=locaux_debout.size)

            for i, loc in enumerate(locaux_debout):
                ag_global = int(idx[loc])
                if not self._a_terre[ag_global] and tirages_bousculade[i] < p_bousculade[i]:
                    pos = (float(x[loc, 0]), float(x[loc, 1]))
                    self.faire_tomber(ag_global, instant, "bousculade", pos)
                    nouvelles_chutes.append(self._historique[-1])

        return nouvelles_chutes


def taux_de_chute(
    historique: tuple[EvenementChute, ...] | list[EvenementChute], duree: float
) -> float:
    """Taux de chute par seconde sur la duree consideree, en chutes/s.

    Args:
        historique: sequence des evenements de chute.
        duree: duree d'observation en secondes (strictement positive).
    """
    if not isinstance(duree, (int, float)) or not np.isfinite(duree) or duree <= 0.0:
        raise ValueError("duree doit etre un nombre reel strictement positif fini")
    return float(len(historique) / duree)


def chutes_par_cause(
    historique: tuple[EvenementChute, ...] | list[EvenementChute],
) -> dict[str, int]:
    """Decompte du nombre de chutes par cause ('glissade', 'domino', 'bousculade')."""
    compte: dict[str, int] = {}
    for ev in historique:
        compte[ev.cause] = compte.get(ev.cause, 0) + 1
    return compte


def tailles_cascades(
    historique: tuple[EvenementChute, ...] | list[EvenementChute],
    distance_max: float = 2.0,
    temps_max: float = 3.0,
) -> list[int]:
    """Taille (nombre d'agents) de chaque composante connexe de chutes (cascades).

    Deux chutes i et j appartiennent a la meme cascade si
    |t_i - t_j| <= temps_max et ||x_i - x_j|| <= distance_max.
    Rend la liste des tailles de composantes connexes triee par ordre decroissant.
    """
    valide_dist = (
        isinstance(distance_max, (int, float)) and np.isfinite(distance_max) and distance_max > 0.0
    )
    if not valide_dist:
        raise ValueError("distance_max doit etre strictement positive et finie")
    valide_t = isinstance(temps_max, (int, float)) and np.isfinite(temps_max) and temps_max > 0.0
    if not valide_t:
        raise ValueError("temps_max doit etre strictement positive et finie")

    n = len(historique)
    if n == 0:
        return []

    adj: list[list[int]] = [[] for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            dt_ij = abs(historique[i].instant - historique[j].instant)
            if dt_ij <= temps_max:
                dx = historique[i].position[0] - historique[j].position[0]
                dy = historique[i].position[1] - historique[j].position[1]
                if math.hypot(dx, dy) <= distance_max:
                    adj[i].append(j)
                    adj[j].append(i)

    visite = [False] * n
    tailles = []
    for i in range(n):
        if not visite[i]:
            visite[i] = True
            taille = 0
            pile = [i]
            while pile:
                noeud = pile.pop()
                taille += 1
                for voisin in adj[noeud]:
                    if not visite[voisin]:
                        visite[voisin] = True
                        pile.append(voisin)
            tailles.append(taille)

    tailles.sort(reverse=True)
    return tailles


def serie_agents_a_terre(
    historique: tuple[EvenementChute, ...] | list[EvenementChute], t: np.ndarray
) -> np.ndarray:
    """Nombre d'agents au sol a chaque instant du tableau 1D t."""
    t_arr = np.asarray(t, dtype=float)
    if t_arr.ndim != 1:
        raise ValueError(f"t doit etre un tableau a 1 dimension, recu {t_arr.shape}")
    nb_terre = np.zeros(t_arr.shape, dtype=int)
    for ev in historique:
        t_deb = ev.instant
        t_fin = ev.instant + ev.duree_relevage
        nb_terre += ((t_arr >= t_deb - 1e-12) & (t_arr < t_fin - 1e-12)).astype(int)
    return nb_terre
