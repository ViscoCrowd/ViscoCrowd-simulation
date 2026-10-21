"""Scenario piscine complet (jalon 4) : sortir de l'eau, traverser les plages, passer la porte.

Chaque agent passe par quatre etats :

    EAU  --(site libre atteint)-->  FRANCHISSEMENT  --(duree T ecoulee, place libre)-->
    PLAGE  --(porte franchie)-->  SORTI

  - EAU et PLAGE : l'agent est actif. Il suit le guidage de son cote, subit le sol
    sous lui (pas libre des milieux) et l'exclusion (projection). Le bord du bassin
    est un mur des deux cotes.
  - FRANCHISSEMENT (spec § 2.7) : un agent arrive a moins de `portee` du point
    d'attente d'un site LIBRE l'occupe (la portee est la distance a laquelle on
    saisit le bord ou l'echelle ; plus courte que le rayon, deux agents serres de
    part et d'autre d'une echelle se bloquaient mutuellement a un rayon du point
    d'attente, sans que l'un ou l'autre ne puisse jamais l'atteindre). Il est
    immobilise sur le bord pendant la duree du site (rebord ou echelle), hors de
    la projection. Le site reste occupe
    jusqu'a ce que l'agent soit reintroduit sur la plage, au point d'arrivee du
    site, des que ce point est libre de tout agent actif. Capacite : un agent par
    site, toujours.
  - SORTI : etat absorbant (proposition de l'issue #11). Un agent dont le centre
    passe la ligne de la porte est retire de la projection et du guidage ; il ne
    peut plus gener la porte. Son instant de sortie est interpole sur la ligne.

Conservation : a chaque pas, les quatre effectifs somment a N ; une violation leve
une erreur. Les franchissements et les sorties sont enregistres comme evenements.
"""

from __future__ import annotations

from dataclasses import dataclass, field, fields

import numpy as np

from viscocrowd.core.integrator import pas_semi_implicite
from viscocrowd.core.rng import generateur
from viscocrowd.core.state import State
from viscocrowd.geometry.piscine import NATURES, Piscine
from viscocrowd.geometry.projection import ProjectionExclusion
from viscocrowd.model.carte import CartePiscine
from viscocrowd.model.guidage_piscine import GuidagePiscine
from viscocrowd.model.milieu import Milieu, ParametresMilieu, pas_libre_milieux

EAU, FRANCHISSEMENT, PLAGE, SORTI = 0, 1, 2, 3
NOMS_ETATS = ("eau", "franchissement", "plage", "sorti")


@dataclass(frozen=True)
class ParametresPiscine:
    """Tous les choix du scenario, explicites dans le YAML, en unites SI."""

    geometrie: dict
    n_agents: int
    rayon: float
    espacement: float
    bruit: float
    parametres_milieux: dict
    facteur_vitesse: float
    durees: dict
    portee: float
    dt: float
    duree: float
    tolerance: float
    pas_guidage: float
    graine: int
    piscine: Piscine = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if type(self.n_agents) is not int or self.n_agents < 1:
            raise ValueError("n_agents doit etre un entier strictement positif")
        if type(self.graine) is not int or self.graine < 0:
            raise ValueError("graine doit etre un entier positif ou nul")
        for nom in (
            "rayon",
            "espacement",
            "bruit",
            "facteur_vitesse",
            "portee",
            "dt",
            "duree",
            "tolerance",
            "pas_guidage",
        ):
            valeur = getattr(self, nom)
            if type(valeur) not in (int, float) or not np.isfinite(valeur):
                raise ValueError(f"{nom} doit etre un nombre reel fini")
            if valeur < 0 or (nom != "bruit" and valeur == 0):
                raise ValueError(f"{nom} hors domaine")
        try:
            geometrie = dict(self.geometrie)
            geometrie["echelles"] = tuple(tuple(e) for e in geometrie["echelles"])
            piscine = Piscine(**geometrie)
            milieux = {
                Milieu[nom]: p if isinstance(p, ParametresMilieu) else ParametresMilieu(**p)
                for nom, p in self.parametres_milieux.items()
            }
        except (KeyError, TypeError) as erreur:
            raise ValueError(f"geometrie ou milieux incomplets : {erreur}") from erreur
        if set(milieux) != {Milieu.EAU, Milieu.MOUILLE, Milieu.SEC}:
            raise ValueError("parametres_milieux doit declarer EAU, MOUILLE et SEC")
        if any(p.vitesse <= 0 for p in milieux.values()):
            raise ValueError("les vitesses souhaitees doivent etre positives")
        if set(self.durees) != set(NATURES) or not all(
            type(d) in (int, float) and np.isfinite(d) and d >= 0 for d in self.durees.values()
        ):
            raise ValueError(f"durees doit donner un temps fini positif pour {NATURES}")
        if self.dt > min(p.relaxation for p in milieux.values()):
            raise ValueError("dt doit etre inferieur ou egal aux temps de relaxation")
        vitesse_max = self.facteur_vitesse * max(p.vitesse for p in milieux.values())
        if self.dt * vitesse_max > self.rayon / 5:
            raise ValueError("dt trop grand : deplacement souhaite par pas > rayon/5")
        if self.pas_guidage > self.rayon:
            raise ValueError("pas_guidage doit etre inferieur ou egal au rayon")
        # Au-dela de la moitie de l'espacement du rebord, deux sites voisins se
        # disputeraient le meme agent.
        if self.portee >= piscine.pas_rebord / 2:
            raise ValueError("portee doit rester sous la moitie de pas_rebord")
        if self.espacement - 2 * self.bruit < 2 * self.rayon:
            raise ValueError("espacement insuffisant pour garantir le non-recouvrement initial")
        object.__setattr__(self, "piscine", piscine)
        object.__setattr__(self, "parametres_milieux", milieux)
        object.__setattr__(self, "durees", {n: float(d) for n, d in self.durees.items()})
        candidats = _grille_initiale(self)
        if candidats.shape[0] < self.n_agents:
            raise ValueError(f"le bassin ne loge que {candidats.shape[0]} agents a cet espacement")

    def en_dictionnaire(self) -> dict:
        """Parametres effectifs, serialisables en JSON (milieux par nom)."""
        resultat = {f.name: getattr(self, f.name) for f in fields(self) if f.init}
        resultat["geometrie"] = {
            **self.geometrie,
            "echelles": [list(e) for e in self.piscine.echelles],
        }
        resultat["parametres_milieux"] = {
            m.name: {
                "relaxation": p.relaxation,
                "acceleration_max": p.acceleration_max,
                "vitesse": p.vitesse,
            }
            for m, p in self.parametres_milieux.items()
        }
        return resultat


def _grille_initiale(p: ParametresPiscine) -> np.ndarray:
    """Emplacements candidats dans l'eau, a l'espacement donne, loin du bord."""
    b, marge = p.piscine.bassin, p.rayon + p.bruit + 1e-9
    xs = np.arange(b.x_min + marge, b.x_max - marge + 1e-12, p.espacement)
    ys = np.arange(b.y_min + marge, b.y_max - marge + 1e-12, p.espacement)
    return np.array([[x, y] for x in xs for y in ys]).reshape(-1, 2)


def positions_initiales(p: ParametresPiscine) -> np.ndarray:
    """N emplacements tires sans remise parmi la grille du bassin, perturbes (graine)."""
    rng = generateur(p.graine)
    candidats = _grille_initiale(p)
    choix = rng.choice(candidats.shape[0], size=p.n_agents, replace=False)
    return candidats[np.sort(choix)] + rng.uniform(-p.bruit, p.bruit, size=(p.n_agents, 2))


@dataclass(frozen=True)
class ResultatPiscine:
    """Trajectoire et evenements.

    Attributes:
        t, x, v: instants (P,), positions et vitesses (P, N, 2), en s, m, m/s.
        etats: (P, N) entiers, 0 eau, 1 franchissement, 2 plage, 3 sorti.
        rayons: (N,), en m.
        franchissements: (M, 4) [agent, site, debut, fin] ; fin = reintroduction.
        natures: nature de chaque site, par indice.
        sorties: (N,) instant de passage de la porte, en s ; NaN si jamais sorti.
    """

    t: np.ndarray
    x: np.ndarray
    v: np.ndarray
    etats: np.ndarray
    rayons: np.ndarray
    franchissements: np.ndarray
    natures: tuple[str, ...]
    sorties: np.ndarray
    projection: ProjectionExclusion
    parametres: ParametresPiscine

    def violation_paroi_max(self) -> float:
        """Plus grand depassement des murs, sur tous les agents actifs et tous les instants."""
        pire = 0.0
        for x, e, t in zip(self.x, self.etats, self.t, strict=True):
            actifs = (e == EAU) | (e == PLAGE)
            if np.any(actifs):
                pire = max(
                    pire, self.parametres.piscine.violation(x[actifs], self.rayons[actifs], t)
                )
        return pire

    def temps_evacuation(self, fraction: float = 1.0) -> float:
        """Instant ou la fraction donnee de la population est sortie ; +inf sinon."""
        rang = max(1, int(np.ceil(fraction * self.sorties.size - 1e-12)))
        instants = np.sort(self.sorties[np.isfinite(self.sorties)])
        return float(instants[rang - 1]) if rang <= instants.size else float("inf")


def simuler_piscine(p: ParametresPiscine) -> ResultatPiscine:
    """Simule l'evacuation jusqu'a la sortie du dernier agent ou jusqu'a `duree`."""
    piscine = p.piscine
    guidage = GuidagePiscine(
        piscine, p.parametres_milieux, p.rayon, p.pas_guidage, p.durees, p.facteur_vitesse
    )
    libre = pas_libre_milieux(
        guidage, CartePiscine(piscine), p.parametres_milieux, facteur_vitesse=p.facteur_vitesse
    )
    projection = ProjectionExclusion(piscine.projeter, tolerance=p.tolerance, strict=True)
    sites = guidage.sites
    attentes = np.array([s.attente(p.rayon) for s in sites])
    arrivees = np.array([s.arrivee(p.rayon) for s in sites])
    positions_bord = np.array([s.position for s in sites])
    durees = np.array([p.durees[s.nature] for s in sites])
    x_porte, (_, y_bas), (_, y_haut) = piscine.longueur_emprise, *piscine.porte
    dehors = np.array([x_porte + piscine.profondeur_porte, 0.5 * (y_bas + y_haut)])

    n = p.n_agents
    x = positions_initiales(p)
    v = np.zeros((n, 2))
    r = np.full(n, p.rayon)
    etat = np.full(n, EAU, dtype=np.int64)
    occupant = np.full(len(sites), -1, dtype=np.int64)
    fin = np.zeros(len(sites))
    debut_agent = np.full(n, np.nan)
    site_agent = np.full(n, -1, dtype=np.int64)
    sorties = np.full(n, np.nan)
    evenements: list[list[float]] = []

    t = 0.0
    historique_t, historique_x, historique_v, historique_e = (
        [t],
        [x.copy()],
        [v.copy()],
        [etat.copy()],
    )
    n_pas = int(np.ceil(p.duree / p.dt))
    for pas in range(1, n_pas + 1):
        actifs = np.flatnonzero((etat == EAU) | (etat == PLAGE))
        avant = x.copy()
        if actifs.size:
            nouveau = pas_semi_implicite(
                State(x=x[actifs], v=v[actifs], r=r[actifs], t=t), p.dt, libre, projection
            )
            x[actifs], v[actifs] = nouveau.x, nouveau.v
        t = pas * p.dt  # sans accumulation d'arrondis : les durees restent exactes

        # Sorties : passage de la ligne de la porte, instant interpole.
        sortants = np.flatnonzero((etat == PLAGE) & (x[:, 0] >= x_porte))
        for i in sortants:
            s = (x_porte - avant[i, 0]) / (x[i, 0] - avant[i, 0])
            sorties[i] = t - p.dt + s * p.dt
            etat[i] = SORTI
            x[i], v[i] = dehors, 0.0

        # Fins de franchissement : reintroduction des que le point d'arrivee est libre.
        for k in np.flatnonzero((occupant >= 0) & (fin <= t + 1e-12)):
            i = occupant[k]
            sur_place = np.flatnonzero((etat == EAU) | (etat == PLAGE))
            if sur_place.size:
                ecart = np.hypot(*(x[sur_place] - arrivees[k]).T) - r[sur_place] - r[i]
                if np.min(ecart) < -p.tolerance:
                    continue  # place occupee : l'agent attend sur le bord, le site reste pris
            etat[i], x[i], v[i] = PLAGE, arrivees[k], 0.0
            occupant[k] = -1
            evenements.append([i, k, debut_agent[i], t])

        # Debuts de franchissement : un agent de l'eau pres du point d'attente d'un site libre.
        dans_l_eau = np.flatnonzero(etat == EAU)
        libres = np.flatnonzero(occupant < 0)
        if dans_l_eau.size and libres.size:
            distances = np.hypot(
                x[dans_l_eau, None, 0] - attentes[None, libres, 0],
                x[dans_l_eau, None, 1] - attentes[None, libres, 1],
            )
            for a, i in enumerate(dans_l_eau):
                proches = np.flatnonzero((distances[a] <= p.portee) & (occupant[libres] < 0))
                if proches.size:
                    k = libres[proches[np.argmin(distances[a, proches])]]
                    occupant[k], fin[k] = i, t + durees[k]
                    etat[i], debut_agent[i], site_agent[i] = FRANCHISSEMENT, t, k
                    x[i], v[i] = positions_bord[k], 0.0

        if np.bincount(etat, minlength=4).sum() != n:
            raise RuntimeError("conservation violee : un agent a disparu ou s'est dedouble")
        historique_t.append(t)
        historique_x.append(x.copy())
        historique_v.append(v.copy())
        historique_e.append(etat.copy())
        if np.all(etat == SORTI):
            break

    return ResultatPiscine(
        t=np.array(historique_t),
        x=np.stack(historique_x),
        v=np.stack(historique_v),
        etats=np.stack(historique_e),
        rayons=r,
        franchissements=np.array(evenements, dtype=float).reshape(-1, 4),
        natures=tuple(s.nature for s in sites),
        sorties=sorties,
        projection=projection,
        parametres=p,
    )
