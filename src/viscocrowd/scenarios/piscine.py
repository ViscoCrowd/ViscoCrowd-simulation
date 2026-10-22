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

Quand plusieurs agents sont a portee de sites libres, les couples (agent, site)
sont servis du plus proche au plus loin : l'attribution depend des positions, pas
de la numerotation des agents.

Coherence, verifiee a chaque pas (une violation leve une erreur) :
  - chaque site occupe l'est par un agent en FRANCHISSEMENT, et chaque agent en
    FRANCHISSEMENT occupe exactement un site ;
  - un agent EAU a son centre dans le bassin, un agent PLAGE hors du bassin ;
  - le deplacement MESURE d'un agent actif reste sous r/5 par pas, corrections de
    contact comprises : c'est ce qui garantit qu'aucun centre ne passe le bord.
Les franchissements et les sorties sont enregistres comme evenements.
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
from viscocrowd.observables.sortie import Sorties

EAU, FRANCHISSEMENT, PLAGE, SORTI = 0, 1, 2, 3
# Legende des codes d'etat, archivee avec les etats pour la relecture hors ligne.
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
        for nom in ("geometrie", "parametres_milieux", "durees"):
            if not isinstance(getattr(self, nom), dict):
                raise ValueError(f"{nom} doit etre une table YAML (cle: valeur)")
        try:
            geometrie = dict(self.geometrie)
            geometrie["echelles"] = tuple(tuple(e) for e in geometrie["echelles"])
            piscine = Piscine(**geometrie)
            milieux = {
                Milieu[nom]: p if isinstance(p, ParametresMilieu) else ParametresMilieu(**p)
                for nom, p in self.parametres_milieux.items()
            }
        except (KeyError, TypeError, AttributeError) as erreur:
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
        # Le long d'un cote, un agent n'est ainsi a portee que d'un site. Aux coins du
        # bassin, les points d'attente des premiers sites de deux cotes voisins sont
        # plus proches (0,15 m avec les valeurs de reference) : un agent peut y etre a
        # portee de deux sites, mais l'attribution du plus proche ne lui en donne qu'un.
        if self.portee >= piscine.pas_rebord / 2:
            raise ValueError("portee doit rester sous la moitie de pas_rebord")
        # Ce qui doit tenir partout, coins compris : deux agents immobilises sur le
        # bord, hors de la projection, ne se recouvrent pas.
        bords = np.array([s.position for s in piscine.sites()])
        i, j = np.triu_indices(len(bords), 1)
        if np.min(np.hypot(*(bords[i] - bords[j]).T)) < 2 * self.rayon:
            raise ValueError("deux sites de franchissement sont a moins d'un diametre")
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
        """Instant ou la fraction donnee de la population est sortie ; +inf sinon.

        Delegue a `observables.sortie.Sorties`, qui controle aussi `fraction`.
        """
        return Sorties(self.sorties).temps_evacuation(fraction)


def _attribuer_sites(distances: np.ndarray, portee: float) -> list[tuple[int, int]]:
    """Couples (ligne, colonne) a portee, du plus proche au plus loin, chacun pris une fois.

    `distances` (A, S) separe A agents candidats de S sites libres. On sert d'abord le
    couple le plus proche, puis le suivant parmi les agents et sites restants : le
    resultat depend des positions, pas de l'ordre des agents (indices en dernier
    recours, pour les egalites exactes).
    """
    lignes, colonnes = np.nonzero(distances <= portee)
    ordre = np.lexsort((colonnes, lignes, distances[lignes, colonnes]))
    pris_lignes, pris_colonnes, couples = set(), set(), []
    for k in ordre:
        a, s = int(lignes[k]), int(colonnes[k])
        if a not in pris_lignes and s not in pris_colonnes:
            pris_lignes.add(a)
            pris_colonnes.add(s)
            couples.append((a, s))
    return couples


def verifier_coherence(
    etat: np.ndarray, occupant: np.ndarray, site_agent: np.ndarray, x: np.ndarray, piscine
) -> None:
    """Leve RuntimeError si les etats, les sites et les positions se contredisent.

    Args:
        etat: (N,) etat de chaque agent.
        occupant: (S,) agent qui occupe chaque site, -1 si libre.
        site_agent: (N,) site occupe ou dernier site occupe par chaque agent.
        x: (N, 2) positions, en m.
        piscine: la geometrie, pour le cote du bord ou se trouve chaque centre.
    """
    if np.any((etat < EAU) | (etat > SORTI)):
        raise RuntimeError("etat inconnu : un agent n'est dans aucun des quatre etats")
    occupes = np.flatnonzero(occupant >= 0)
    en_franchissement = np.flatnonzero(etat == FRANCHISSEMENT)
    if not np.array_equal(np.sort(occupant[occupes]), en_franchissement):
        raise RuntimeError(
            "sites et franchissements incoherents : un site occupe sans agent en "
            "franchissement, un agent en franchissement sans site, ou deux sites par agent"
        )
    if np.any(site_agent[occupant[occupes]] != occupes):
        raise RuntimeError("un agent en franchissement ne designe pas le site qu'il occupe")
    dans = piscine.dans_bassin(x)
    if not np.all(dans[etat == EAU]) or np.any(dans[etat == PLAGE]):
        raise RuntimeError("un agent est du mauvais cote du bord du bassin pour son etat")


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
            # Deplacement MESURE, corrections de contact comprises : le controle de dt
            # ne porte que sur la vitesse souhaitee, et la projection peut aller plus vite.
            deplacement = np.max(np.hypot(*(nouveau.x - x[actifs]).T))
            if deplacement > p.rayon / 5 * (1 + 1e-12):
                raise ValueError(
                    f"deplacement mesure de {deplacement:.3g} m en un pas, > rayon/5 a "
                    f"t = {t:.2f} s ; reduire dt"
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

        # Debuts de franchissement : un agent de l'eau pres du point d'attente d'un site
        # libre. Les couples les plus proches sont servis d'abord.
        dans_l_eau = np.flatnonzero(etat == EAU)
        libres = np.flatnonzero(occupant < 0)
        if dans_l_eau.size and libres.size:
            distances = np.hypot(
                x[dans_l_eau, None, 0] - attentes[None, libres, 0],
                x[dans_l_eau, None, 1] - attentes[None, libres, 1],
            )
            for a, s in _attribuer_sites(distances, p.portee):
                i, k = dans_l_eau[a], libres[s]
                occupant[k], fin[k] = i, t + durees[k]
                etat[i], debut_agent[i], site_agent[i] = FRANCHISSEMENT, t, k
                x[i], v[i] = positions_bord[k], 0.0

        verifier_coherence(etat, occupant, site_agent, x, piscine)
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
