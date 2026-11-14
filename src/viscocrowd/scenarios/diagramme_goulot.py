"""M8 : diagramme fondamental du goulot sec E0, mesure devant l'entree du goulot (#124).

E0 compare deja le DEBIT GLOBAL du goulot a Seyfried et al. (2009). Ce module mesure
autre chose : la relation locale entre densite et vitesse devant le goulot, que l'on
confronte a celle de Weidmann (1993). C'est le diagramme fondamental de la spec § 3.

Mesure
------

A chaque instant retenu, on calcule la densite et la vitesse de Voronoi (Steffen et
Seyfried 2010, `observables.densite.mesures_voronoi`) dans une zone rectangulaire de
la salle, juste en amont de l'entree du goulot. Chaque instant donne un point
(rho, v) ; le debit specifique de ce point vaut rho * v. Les points de toutes les
largeurs et de toutes les graines sont ensuite agreges par classes de densite
(`observables.diagramme.classer`).

Trois choix, a discuter avant toute conclusion (#124) :

  - la ZONE est celle ou #101 a mesure le biais de densite, l'entonnoir comprime
    devant le goulot. Ses cellules sont bornees par les murs de la salle, y compris
    le mur perce a x = L : c'est exact a gauche, en haut et en bas, approche pres
    de l'ouverture, ou les agents deja engages dans le goulot ne comptent pas ;
  - le DEBUT exclut la mise en marche : a t = 0, toute la foule est au repos a
    3,3 pers/m^2, puis le bloc demarre d'un seul tenant. Mesure le 13 novembre sur
    les 50 simulations E0 (5 largeurs, 10 graines) : en commencant a 1 s, 396 points
    forment une branche a fort debit (rho > 3,3 pers/m^2, J > 1,3 pers/(m.s)), tous
    entre 1,0 et 1,9 s. A partir de 3 s, il n'en reste aucun : c'est le defaut ;
  - le PAS DE MESURE espace les instants retenus. Des instants plus serres ne
    seraient pas plus independants (voir `observables.diagramme`).

La vitesse d'un agent a l'instant n est son deplacement realise sur le pas
precedent, (x[n] - x[n-1]) / dt : c'est exactement la vitesse du modele, relue
apres la projection (spec § 2.8).
"""

from __future__ import annotations

import math
import sys
import time
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from viscocrowd.core.verifications import exiger_fini, exiger_scalaire_fini
from viscocrowd.observables.densite import Rectangle, mesures_voronoi
from viscocrowd.observables.diagramme import ClassesDensite, classer
from viscocrowd.scenarios.goulot import champ_goulot, parametres_goulot, simuler_goulot


@dataclass(frozen=True)
class SerieVoronoi:
    """Points du diagramme mesures au fil d'une simulation.

    Attributes:
        t: (P,) instants, en s.
        densite: (P,) densite de Voronoi dans la zone, en pers/m^2.
        vitesse: (P,) vitesse de Voronoi dans la zone, en m/s.
    """

    t: np.ndarray
    densite: np.ndarray
    vitesse: np.ndarray

    @property
    def debit(self) -> np.ndarray:
        """Debit specifique de chaque point, rho * v, en pers/(m.s)."""
        return self.densite * self.vitesse


def serie_voronoi(
    t: np.ndarray,
    x: np.ndarray,
    salle: Rectangle,
    zone: Rectangle,
    *,
    debut: float = 0.0,
    pas_mesure: int = 1,
) -> SerieVoronoi:
    """Densite et vitesse de Voronoi dans `zone`, aux instants t[n] >= debut.

    Seuls les agents dont le centre est strictement dans la salle ont une cellule :
    ceux qui sont dans le goulot ou deja sortis sont ignores. Un instant ou la salle
    est vide ne donne aucun point.

    Args:
        t: (P,) instants archives, strictement croissants, en s.
        x: (P, N, 2) positions archivees, en m.
        salle: rectangle qui borne les cellules de Voronoi.
        zone: zone de mesure, incluse dans la salle.
        debut: premier instant retenu, en s.
        pas_mesure: on retient un instant sur `pas_mesure` a partir du premier.
    """
    t, x = np.asarray(t, dtype=float), np.asarray(x, dtype=float)
    exiger_fini(t=t, x=x)
    exiger_scalaire_fini("debut", debut)
    if t.ndim != 1 or x.ndim != 3 or x.shape[0] != t.size or x.shape[2] != 2:
        raise ValueError("t et x doivent etre de formes (P,) et (P, N, 2)")
    if t.size < 2 or np.any(np.diff(t) <= 0.0):
        raise ValueError("il faut au moins deux instants, strictement croissants")
    if type(pas_mesure) is not int or pas_mesure < 1:
        raise ValueError("pas_mesure doit etre un entier >= 1")

    retenus = [n for n in range(1, t.size) if t[n] >= debut][::pas_mesure]
    instants, densites, vitesses = [], [], []
    for n in retenus:
        p = x[n]
        dans = (
            (p[:, 0] > salle.x_min)
            & (p[:, 0] < salle.x_max)
            & (p[:, 1] > salle.y_min)
            & (p[:, 1] < salle.y_max)
        )
        if not dans.any():
            continue
        v = (p[dans] - x[n - 1, dans]) / (t[n] - t[n - 1])
        rho, vit = mesures_voronoi(p[dans], v, salle, zone)
        instants.append(t[n])
        densites.append(rho)
        vitesses.append(vit)
    return SerieVoronoi(np.array(instants), np.array(densites), np.array(vitesses))


def mesurer(
    configuration: dict,
    largeurs: Sequence[float],
    graines: Sequence[int],
    zone: Rectangle,
    *,
    debut: float,
    pas_mesure: int,
) -> dict[tuple[float, int], SerieVoronoi]:
    """Simule E0 pour chaque largeur et chaque graine, et rend la serie de chacune.

    Raises:
        ValueError: si une simulation n'est pas un ecoulement (bouchage, projection
            non convergee) : son diagramme ne decrirait pas une foule qui s'ecoule.
    """
    largeurs, graines = [float(b) for b in largeurs], list(graines)
    if not largeurs or not graines:
        raise ValueError("il faut au moins une largeur et une graine")
    if len(set(largeurs)) != len(largeurs) or len(set(graines)) != len(graines):
        raise ValueError("largeurs et graines doivent etre distinctes")
    series = {}
    for b in largeurs:
        p0 = parametres_goulot(configuration, largeur_goulot=b)
        salle = Rectangle(0.0, p0.longueur, 0.0, p0.largeur)
        if not salle.contient(zone):
            raise ValueError("la zone de mesure doit etre incluse dans la salle")
        champ = champ_goulot(p0)
        for g in graines:
            p = parametres_goulot(configuration | {"graine": g}, largeur_goulot=b)
            resultat = simuler_goulot(p, champ)
            if resultat.statut != "ecoulement":
                raise ValueError(f"b = {b} m, graine {g} : {resultat.statut}, pas un ecoulement")
            series[(b, g)] = serie_voronoi(
                resultat.t, resultat.x, salle, zone, debut=debut, pas_mesure=pas_mesure
            )
    return series


def agreger(series: dict[tuple[float, int], SerieVoronoi], pas_classe: float) -> ClassesDensite:
    """Toutes les series en un diagramme, par classes de largeur `pas_classe` (pers/m^2)."""
    exiger_scalaire_fini("pas_classe", pas_classe, strictement_positif=True)
    densites = np.concatenate([s.densite for s in series.values()])
    vitesses = np.concatenate([s.vitesse for s in series.values()])
    haut = pas_classe * math.ceil(float(np.max(densites, initial=0.0)) / pas_classe + 1e-9)
    bornes = np.arange(0.0, max(haut, pas_classe) + pas_classe / 2, pas_classe)
    return classer(densites, vitesses, bornes)


def ajouter_commande(sous) -> None:
    commande = sous.add_parser(
        "diagramme-goulot",
        help="M8 : diagramme fondamental devant le goulot E0, compare a Weidmann (1993)",
    )
    commande.add_argument("configuration", type=Path, help="configuration YAML du goulot")
    commande.add_argument(
        "--largeurs", type=float, nargs="+", default=[0.8, 0.9, 1.0, 1.1, 1.2], help="b, en m"
    )
    commande.add_argument(
        "--graines", type=int, nargs="+", help="defaut : dix graines a partir de celle du YAML"
    )
    commande.add_argument(
        "--zone",
        type=float,
        nargs=4,
        default=[6.0, 7.8, 1.5, 3.5],
        metavar=("X_MIN", "X_MAX", "Y_MIN", "Y_MAX"),
        help="zone de mesure, en m (defaut : l'entonnoir de #101, devant le goulot)",
    )
    commande.add_argument(
        "--debut",
        type=float,
        default=3.0,
        help="premier instant retenu, en s (defaut : apres le demarrage du bloc initial)",
    )
    commande.add_argument(
        "--pas-mesure", type=int, default=10, help="un instant archive sur N (defaut : 0,1 s)"
    )
    commande.add_argument(
        "--pas-classe", type=float, default=0.25, help="largeur des classes, en pers/m^2"
    )
    commande.add_argument("--figure", type=Path, help="dossier ou ecrire la figure")
    commande.add_argument("--sortie", type=Path, help="bilan JSON, series et classes")
    commande.set_defaults(fonction=commande_diagramme)


def commande_diagramme(args) -> int:
    from viscocrowd.io.configuration import lire_configuration
    from viscocrowd.observables import weidmann
    from viscocrowd.scenarios.campagne import contexte, ecrire_json, verifier_sortie

    debut_calcul = time.perf_counter()
    try:
        configuration = lire_configuration(args.configuration)
        if configuration.get("scenario") != "goulot":
            raise ValueError("le diagramme attend une configuration du scenario goulot")
        graines = args.graines or [configuration["graine"] + k for k in range(10)]
        zone = Rectangle(*args.zone)
        if args.sortie is not None:
            if args.sortie.suffix != ".json":
                raise ValueError("le bilan doit porter l'extension .json")
            verifier_sortie(args.sortie)
            if args.sortie.exists():
                raise ValueError(f"{args.sortie} existe deja : choisir un autre fichier")
        series = mesurer(
            configuration,
            args.largeurs,
            graines,
            zone,
            debut=args.debut,
            pas_mesure=args.pas_mesure,
        )
        classes = agreger(series, args.pas_classe)
    except (OSError, KeyError, TypeError, ValueError) as erreur:
        print(f"Diagramme refuse : {erreur}", file=sys.stderr)
        return 1

    n_agents = configuration["parametres"]["n_agents"]
    points = sum(s.t.size for s in series.values())
    print(f"M8, goulot sec E0 — {n_agents} agents, largeurs {args.largeurs}, graines {graines}")
    print(f"Zone {args.zone} m, des t = {args.debut} s, un instant sur {args.pas_mesure}")
    print(f"{points} points ; ecart-type = dispersion des etats, pas incertitude (points correles)")
    print(
        f"{'rho (pers/m^2)':>16} {'points':>7} {'v (m/s)':>16} {'v Weidmann':>11} "
        f"{'J (pers/(m.s))':>17} {'J Weidmann':>11}"
    )
    for k in np.flatnonzero(classes.effectifs):
        rho = classes.densite[k]
        print(
            f"{rho:>16.2f} {classes.effectifs[k]:>7d} "
            f"{classes.vitesse[k]:>8.3f} ± {classes.ecart_vitesse[k]:<5.3f} "
            f"{float(weidmann.vitesse(rho)):>11.3f} "
            f"{classes.debit[k]:>9.3f} ± {classes.ecart_debit[k]:<5.3f} "
            f"{float(weidmann.debit_specifique(rho)):>11.3f}"
        )

    if args.figure is not None:
        from viscocrowd.viz.figures import figure_diagramme_fondamental

        print(f"Figure : {figure_diagramme_fondamental(series, classes, args.figure)}")
    if args.sortie is not None:
        args.sortie.parent.mkdir(parents=True, exist_ok=True)
        ecrire_json(
            args.sortie,
            {
                "version": 1,
                "configuration_source": configuration,
                "contexte": contexte(),
                "largeurs": list(args.largeurs),
                "graines": graines,
                "zone": list(args.zone),
                "debut": args.debut,
                "pas_mesure": args.pas_mesure,
                "series": [
                    {
                        "largeur": b,
                        "graine": g,
                        "t": s.t.tolist(),
                        "densite": s.densite.tolist(),
                        "vitesse": s.vitesse.tolist(),
                    }
                    for (b, g), s in series.items()
                ],
                # JSON n'a pas de NaN : une classe vide s'ecrit null.
                "classes": {
                    nom: [None if v != v else v for v in valeurs.tolist()]
                    for nom, valeurs in vars(classes).items()
                },
            },
        )
        print(f"Bilan : {args.sortie}")
    print(f"Temps d'execution : {time.perf_counter() - debut_calcul:.1f} s")
    return 0
