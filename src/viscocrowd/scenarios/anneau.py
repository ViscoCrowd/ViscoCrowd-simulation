"""M8 : diagramme fondamental en ecoulement libre, sur un couloir circulaire (#124).

Devant le goulot E0 et devant la porte de la piscine, la foule attend : la vitesse y
depend de la capacite de l'ouverture, pas de la seule densite, et aucune phase n'est
stationnaire (docs/diagramme-fondamental.md). Weidmann (1993) decrit, lui, une marche
unidirectionnelle sans contrainte exterieure. Pour s'y comparer dans son domaine, il
faut une densite IMPOSEE et un etat STATIONNAIRE : N agents sur un anneau, sans entree
ni sortie, que l'on laisse tourner jusqu'au regime etabli.

Mesure
------

La densite est imposee : rho = N / A, avec A l'aire de marche de l'anneau. La vitesse
est la moyenne, sur les agents et sur la fenetre [debut_mesure, duree], de la composante
tangentielle du deplacement realise a chaque pas, (x[n] - x[n-1]) / dt : la vitesse du
modele relue apres la projection. Le debit specifique vaut J = rho * v.

Guidage
-------

Chaque agent veut tourner dans le sens direct a la vitesse souhaitee V, le long du
cercle sur lequel il se trouve. Une vitesse souhaitee purement tangentielle ne suffit
pas : la relaxation la suit avec un retard tau, et l'agent derive vers le mur exterieur
(mesure : toute la foule contre ce mur en quelques tours). On ajoute donc la composante
centripete que demande la relaxation pour tenir un cercle a la vitesse actuelle |v| :

    U = V e_t - (tau - dt/2) |v|^2 / R e_r

Le terme en tau seul tient le cercle en temps continu. Le pas explicite le depasse d'un
demi-pas : la vitesse libre est appliquee sur toute la corde, alors qu'elle n'a tourne
que de la moitie. Mesure le 16 novembre sur un agent seul a R = 6 m, dt = 0,01 s,
pendant 30 s : il derive vers le centre de 1,50 mm/s avec tau seul, de 0,02 mm/s avec
tau - dt/2.
L'agent n'a pas de voie preferee : il garde son rayon tant que rien ne le pousse.

Meneur
------

Avec la relation vitesse-espacement de E0, V = min(v0, max(0, s / T)), ou s est le jeu
au meneur (`model.espacement`, Tordeux et al. 2016). Sur l'anneau, le meneur se cherche
le long du CERCLE, pas de la tangente : j mene i s'il est devant dans le sens direct
(0 < theta_j - theta_i < pi, angles ramenes modulo 2 pi) et si son ecart RADIAL est
inferieur a r_i + r_j. Le jeu reste la distance vraie entre les disques.

La tangente ne convient pas : elle s'ecarte du cercle de d^2 / (2 R). Mesure le
16 novembre a N = 15, avec `jeu_au_meneur` le long de la tangente : un agent de la voie
voisine, 0,42 m plus loin du centre et 0,7 m devant, passait a 0,376 m de la tangente,
sous le seuil de 0,4 m. Faux meneur, et l'agent marchait a 1,24 m/s au lieu de 1,34.

L'ordre d'avance de `model.espacement` est inutile ici : il n'y a pas de sortie, et le
seul cycle possible est la foule entiere, qui est l'ecoulement et non une attente.
Deux agents proches ne peuvent pas etre chacun devant l'autre.

Limite : a vitesse lineaire egale, un agent du bord interieur fait le tour plus vite.
La commande donne la vitesse des moities interieure et exterieure de l'anneau pour que
l'effet de la courbure se mesure.

Navigation (#158)
-----------------

Avec `navigation`, la consigne vient des heuristiques de Moussaid et al. (2011)
(`model.navigation`), comme sur la plage de la piscine : la destination est la tangente
directe e_t, sans le terme centripete, que l'heuristique de direction remplace (elle
evite elle-meme les deux murs, vus comme un disque et une enceinte circulaires). Chaque
agent a sa vitesse souhaitee, v0 fois un facteur individuel. La seconde heuristique est
une relation vitesse-espacement : `temps_espacement` doit alors etre null. Sans sortie,
il n'y a pas d'ordre d'avance : tous les voisins comptent.
"""

from __future__ import annotations

import math
import sys
import time
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from viscocrowd.core.integrator import pas_semi_implicite
from viscocrowd.core.rng import generateur
from viscocrowd.core.state import State
from viscocrowd.core.verifications import exiger_scalaire_fini
from viscocrowd.geometry.anneau import Anneau
from viscocrowd.geometry.grille import paires_candidates
from viscocrowd.geometry.projection import ProjectionExclusion
from viscocrowd.model.milieu import ParametresMilieu, vitesse_libre
from viscocrowd.model.navigation import (
    ParametresNavigation,
    ScenePlage,
    facteurs_individuels,
    vitesses_souhaitees,
)


@dataclass(frozen=True)
class ParametresAnneau:
    """Tous les choix du banc, en unites SI, lus dans le YAML.

    `navigation` : heuristiques de Moussaid et al. (2011), voir l'en-tete ; None (defaut)
    garde la consigne tangentielle et la relation vitesse-espacement.
    """

    rayon_interieur: float
    rayon_exterieur: float
    n_agents: int
    rayon: float
    bruit: float
    facteur_vitesse: float
    temps_espacement: float | None
    dt: float
    duree: float
    debut_mesure: float
    tolerance: float
    sec: ParametresMilieu
    graine: int
    navigation: ParametresNavigation | dict | None = None

    def __post_init__(self) -> None:
        if self.navigation is not None:
            if isinstance(self.navigation, dict):
                object.__setattr__(self, "navigation", ParametresNavigation(**self.navigation))
            elif not isinstance(self.navigation, ParametresNavigation):
                raise ValueError(
                    "navigation doit etre un dictionnaire ou une instance de ParametresNavigation"
                )
            if self.temps_espacement is not None:
                raise ValueError("navigation et temps_espacement ne se cumulent pas : choisir")
        for nom in ("n_agents", "graine"):
            valeur = getattr(self, nom)
            if type(valeur) is not int or valeur < (0 if nom == "graine" else 1):
                raise ValueError(f"{nom} doit etre entier, positif (graine nulle admise)")
        for nom in ("rayon", "dt", "duree", "tolerance"):
            exiger_scalaire_fini(nom, getattr(self, nom), strictement_positif=True)
        for nom in ("bruit", "facteur_vitesse", "debut_mesure"):
            exiger_scalaire_fini(nom, getattr(self, nom))
            if getattr(self, nom) < 0:
                raise ValueError(f"{nom} doit etre positif ou nul")
        if self.temps_espacement is not None:
            exiger_scalaire_fini(
                "temps_espacement", self.temps_espacement, strictement_positif=True
            )
        if not isinstance(self.sec, ParametresMilieu):
            object.__setattr__(self, "sec", ParametresMilieu(**self.sec))
        if self.debut_mesure >= self.duree:
            raise ValueError("debut_mesure doit preceder la fin de la simulation")
        if self.dt > self.sec.relaxation:
            raise ValueError("dt doit etre inferieur ou egal au temps de relaxation")
        vitesse_max = self.facteur_vitesse * self.sec.vitesse
        if self.navigation is not None:
            vitesse_max *= self.navigation.facteur_maximal  # le plus rapide des individus
        if self.dt * vitesse_max > self.rayon / 5:
            raise ValueError("dt trop grand : deplacement souhaite par pas > rayon/5")
        Anneau(self.rayon_interieur, self.rayon_exterieur)  # controle des rayons
        positions_de_depart(self, bruit=False)  # refuse une population qui ne tient pas

    @property
    def anneau(self) -> Anneau:
        return Anneau(self.rayon_interieur, self.rayon_exterieur)

    @property
    def densite(self) -> float:
        """Densite imposee, en pers/m^2."""
        return self.n_agents / self.anneau.aire


def positions_de_depart(p: ParametresAnneau, *, bruit: bool = True) -> np.ndarray:
    """Agents (N, 2) repartis sur des voies concentriques, a pas d'arc uniforme par voie.

    Les voies sont espacees d'un diametre plus le jeu necessaire au bruit ; chacune recoit
    une part de la population proportionnelle a son perimetre. Le bruit, borne, perturbe
    le rayon et l'angle sans permettre de recouvrement.
    """
    pas = 2 * p.rayon + 2 * p.bruit
    largeur = p.rayon_exterieur - p.rayon_interieur
    n_voies = int((largeur - 2 * p.rayon - 2 * p.bruit) // pas) + 1
    if n_voies < 1:
        raise ValueError("l'anneau est trop etroit pour une voie d'agents")
    marge = (largeur - (n_voies - 1) * pas) / 2
    rayons = p.rayon_interieur + marge + pas * np.arange(n_voies)
    # Repartition proportionnelle au perimetre, arrondie par plus forts restes.
    parts = p.n_agents * rayons / rayons.sum()
    effectifs = np.floor(parts).astype(int)
    effectifs[np.argsort(effectifs - parts)[: p.n_agents - effectifs.sum()]] += 1
    if np.any(2 * np.pi * rayons / np.maximum(effectifs, 1) < pas):
        raise ValueError("population trop grande pour l'anneau : densite au-dela du depart")
    rng = generateur(p.graine)
    points = []
    for rayon, n in zip(rayons, effectifs, strict=True):
        theta = 2 * np.pi * (np.arange(n) + rng.uniform()) / n
        rho = np.full(n, rayon)
        if bruit and p.bruit:
            rho = rho + rng.uniform(-p.bruit, p.bruit, n)
            theta = theta + rng.uniform(-p.bruit, p.bruit, n) / rayon
        points.append(np.column_stack((rho * np.cos(theta), rho * np.sin(theta))))
    return np.concatenate(points)


def jeu_au_meneur_anneau(x: np.ndarray, r: np.ndarray, portee: float) -> np.ndarray:
    """Jeu (N,) en m entre chaque disque et son meneur le long du cercle ; inf sans meneur.

    Voir « Meneur » dans l'en-tete du module. `portee` : jeu au-dela duquel on ignore.
    """
    jeux = np.full(x.shape[0], np.inf)
    paires = paires_candidates(x, r, marge=portee)
    if paires.size == 0:
        return jeux
    suiveur = np.concatenate((paires[:, 0], paires[:, 1]))
    meneur = np.concatenate((paires[:, 1], paires[:, 0]))
    theta = np.arctan2(x[:, 1], x[:, 0])
    rayon = np.hypot(x[:, 0], x[:, 1])
    devant = np.mod(theta[meneur] - theta[suiveur], 2 * np.pi) < np.pi
    contact = r[suiveur] + r[meneur]
    suit = devant & (np.abs(rayon[meneur] - rayon[suiveur]) < contact)
    distance = np.hypot(*(x[meneur[suit]] - x[suiveur[suit]]).T)
    np.minimum.at(jeux, suiveur[suit], distance - contact[suit])
    return jeux


def _reperes(x: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Distance au centre (N,), vecteurs tangent direct et radial sortant (N, 2)."""
    d = np.hypot(x[:, 0], x[:, 1])
    er = x / d[:, None]
    return d, np.column_stack((-er[:, 1], er[:, 0])), er


@dataclass(frozen=True)
class ResultatAnneau:
    """Attributes:
    t: (P,) instants, en s.
    vitesse: (P,) vitesse tangentielle moyenne realisee sur le pas qui finit en t, m/s.
    vitesse_interieure, vitesse_exterieure: (P,) la meme, sur les agents plus proches
        du mur interieur, resp. exterieur, que du milieu de l'anneau.
    violation_paroi_max, recouvrement_max: en m, sur toute la simulation.
    """

    parametres: ParametresAnneau
    t: np.ndarray
    vitesse: np.ndarray
    vitesse_interieure: np.ndarray
    vitesse_exterieure: np.ndarray
    violation_paroi_max: float
    recouvrement_max: float

    def _fenetre(self, serie: np.ndarray) -> np.ndarray:
        return serie[self.t > self.parametres.debut_mesure]

    @property
    def vitesse_moyenne(self) -> float:
        """Vitesse du point du diagramme, en m/s, sur la fenetre de mesure."""
        return float(np.mean(self._fenetre(self.vitesse)))

    @property
    def debit(self) -> float:
        """Debit specifique J = rho * v, en pers/(m.s)."""
        return self.parametres.densite * self.vitesse_moyenne

    @property
    def derive(self) -> float:
        """Ecart relatif des vitesses moyennes des deux moities de la fenetre.

        Un regime stationnaire donne un ecart de l'ordre des fluctuations ; une valeur
        qui ne diminue pas quand la duree augmente signale un transitoire.
        """
        serie = self._fenetre(self.vitesse)
        moitie = serie.size // 2
        a, b = np.mean(serie[:moitie]), np.mean(serie[moitie:])
        return float(abs(b - a) / max(abs(a), abs(b), 1e-12))


def simuler_anneau(p: ParametresAnneau) -> ResultatAnneau:
    """Fait tourner la foule ; la projection est stricte, comme pour tout resultat exploite."""
    anneau = p.anneau
    x = positions_de_depart(p)
    r = np.full(p.n_agents, p.rayon)
    tau, a_max = p.sec.relaxation, p.sec.acceleration_max
    v0 = np.full(p.n_agents, p.facteur_vitesse * p.sec.vitesse)
    navigation = p.navigation
    if navigation is not None:
        v0 = v0 * facteurs_individuels(p.n_agents, navigation, p.graine)
        bord = p.rayon_exterieur + 1.0  # boite englobante : seuls les cercles bornent
        scene = ScenePlage(
            boite=(-bord, bord, -bord, bord),
            rectangles=(),
            disques=((0.0, 0.0, p.rayon_interieur),),
            enceinte=(0.0, 0.0, p.rayon_exterieur),
        )
        taus = np.full(p.n_agents, tau)

    def libre(etat: State, dt: float) -> np.ndarray:
        d, et, er = _reperes(etat.x)
        if navigation is not None:
            u = vitesses_souhaitees(etat.x, etat.v, etat.r, v0, et, taus, scene, navigation)
            return vitesse_libre(etat.v, u, tau, a_max, dt)
        vitesse = v0
        if p.temps_espacement is not None:
            T = p.temps_espacement
            jeu = jeu_au_meneur_anneau(etat.x, etat.r, T * float(v0.max(initial=0.0)))
            vitesse = np.minimum(v0, np.maximum(0.0, jeu / T))
        carre = np.einsum("ij,ij->i", etat.v, etat.v)
        u = vitesse[:, None] * et - ((tau - dt / 2) * carre / d)[:, None] * er
        return vitesse_libre(etat.v, u, tau, a_max, dt)

    projection = ProjectionExclusion(anneau.projeter, tolerance=p.tolerance, strict=True)
    etat = State(x=x, v=np.zeros_like(x), r=r)
    milieu = (p.rayon_interieur + p.rayon_exterieur) / 2
    n_pas = math.ceil(p.duree / p.dt)
    t, v, v_int, v_ext = (np.empty(n_pas) for _ in range(4))
    violation = anneau.violation(etat.x, r, 0.0)
    for n in range(n_pas):
        avant = etat.x
        etat = pas_semi_implicite(etat, p.dt, libre, projection)
        # Tangente au milieu de la corde : le deplacement d'un pas est un arc.
        _, et, _ = _reperes(avant + etat.x)
        d = np.hypot(etat.x[:, 0], etat.x[:, 1])
        tangentielle = np.einsum("ij,ij->i", etat.x - avant, et) / p.dt
        t[n], v[n] = etat.t, tangentielle.mean()
        interieur = d < milieu
        v_int[n] = tangentielle[interieur].mean() if interieur.any() else np.nan
        v_ext[n] = tangentielle[~interieur].mean() if (~interieur).any() else np.nan
        violation = max(violation, anneau.violation(etat.x, r, etat.t))
    return ResultatAnneau(p, t, v, v_int, v_ext, violation, projection.recouvrement_max)


def parametres_anneau(configuration: dict, **remplacements) -> ParametresAnneau:
    """Parametres du YAML (cle `parametres`), avec la graine et d'eventuels remplacements."""
    valeurs = dict(configuration["parametres"])
    valeurs.setdefault("graine", configuration["graine"])
    valeurs.update(remplacements)
    return ParametresAnneau(**valeurs)


def mesurer(
    configuration: dict, effectifs: Sequence[int], graines: Sequence[int]
) -> dict[tuple[int, int], ResultatAnneau]:
    """Une simulation par effectif N et par graine."""
    if not effectifs or not graines:
        raise ValueError("il faut au moins un effectif et une graine")
    return {
        (n, g): simuler_anneau(parametres_anneau(configuration, n_agents=n, graine=g))
        for n in effectifs
        for g in graines
    }


def ajouter_commande(sous) -> None:
    commande = sous.add_parser(
        "diagramme-anneau",
        help="M8 : diagramme fondamental en ecoulement libre sur un anneau, compare a Weidmann",
    )
    commande.add_argument("configuration", type=Path, help="configuration YAML de l'anneau")
    commande.add_argument(
        "--effectifs", type=int, nargs="+", required=True, help="N, une densite imposee chacun"
    )
    commande.add_argument(
        "--graines", type=int, nargs="+", help="defaut : dix graines a partir de celle du YAML"
    )
    commande.add_argument("--sortie", type=Path, help="bilan JSON, un point par (N, graine)")
    commande.set_defaults(fonction=commande_anneau)


def commande_anneau(args) -> int:
    from viscocrowd.io.configuration import lire_configuration
    from viscocrowd.observables import weidmann
    from viscocrowd.scenarios.campagne import contexte, ecrire_json, verifier_sortie

    debut_calcul = time.perf_counter()
    try:
        configuration = lire_configuration(args.configuration)
        if configuration.get("scenario") != "anneau":
            raise ValueError("le diagramme attend une configuration du scenario anneau")
        graines = args.graines or [configuration["graine"] + k for k in range(10)]
        if args.sortie is not None:
            if args.sortie.suffix != ".json":
                raise ValueError("le bilan doit porter l'extension .json")
            verifier_sortie(args.sortie)
            if args.sortie.exists():
                raise ValueError(f"{args.sortie} existe deja : choisir un autre fichier")
        resultats = mesurer(configuration, args.effectifs, graines)
    except (OSError, KeyError, TypeError, ValueError) as erreur:
        print(f"Diagramme refuse : {erreur}", file=sys.stderr)
        return 1

    print(f"M8, anneau en ecoulement libre — graines {graines}")
    print("moyenne ± ecart-type entre graines (graines independantes)")
    print(
        f"{'N':>5} {'rho':>6} {'v (m/s)':>16} {'v Weid.':>8} {'J':>16} {'J Weid.':>8}"
        f" {'v int.':>7} {'v ext.':>7} {'derive':>7} {'viol. (m)':>10}"
    )
    lignes = []
    for n in args.effectifs:
        serie = [resultats[(n, g)] for g in graines]
        rho = serie[0].parametres.densite
        v = np.array([s.vitesse_moyenne for s in serie])
        j = rho * v
        ecart_v = v.std(ddof=1) if v.size > 1 else float("nan")
        ecart_j = j.std(ddof=1) if j.size > 1 else float("nan")
        v_int = np.mean([np.nanmean(s._fenetre(s.vitesse_interieure)) for s in serie])
        v_ext = np.mean([np.nanmean(s._fenetre(s.vitesse_exterieure)) for s in serie])
        derive = max(s.derive for s in serie)
        violation = max(max(s.violation_paroi_max, s.recouvrement_max) for s in serie)
        print(
            f"{n:>5d} {rho:>6.2f} {v.mean():>8.3f} ± {ecart_v:<5.3f} "
            f"{float(weidmann.vitesse(rho)):>8.3f} {j.mean():>8.3f} ± {ecart_j:<5.3f} "
            f"{float(weidmann.debit_specifique(rho)):>8.3f} {v_int:>7.3f} {v_ext:>7.3f} "
            f"{derive:>7.1%} {violation:>10.1e}"
        )
        lignes.append(
            {
                "n_agents": n,
                "densite": rho,
                "vitesses": v.tolist(),
                "vitesse_weidmann": float(weidmann.vitesse(rho)),
                "debit_weidmann": float(weidmann.debit_specifique(rho)),
                "vitesse_interieure": float(v_int),
                "vitesse_exterieure": float(v_ext),
                "derive_max": derive,
                "violation_max": violation,
            }
        )
    duree = time.perf_counter() - debut_calcul
    print(f"Calcul : {duree:.1f} s")
    if args.sortie is not None:
        ecrire_json(
            args.sortie,
            {
                "configuration": str(args.configuration),
                "graines": graines,
                "points": lignes,
                "duree_calcul_s": duree,
                **contexte(),
            },
        )
        print(f"Bilan ecrit dans {args.sortie}")
    return 0
