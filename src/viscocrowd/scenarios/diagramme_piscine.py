"""M8, second volet : diagramme fondamental devant la porte de la piscine (#124).

Le premier volet (`diagramme_goulot`) mesure la relation densite-vitesse devant le
goulot sec E0. Ici, on la mesure devant la porte de la piscine, pour la piscine
mouillee (E2) et pour le temoin entierement sec (E1), apparies graine par graine :
c'est la question de la problematique, « le carrelage mouille deplace-t-il le
diagramme fondamental ? ».

Salle de Voronoi
----------------

La densite de Voronoi demande une salle CONVEXE qui borne les cellules
(`observables.densite`, « Limite de portee »). La plage ne l'est pas : le bassin y
fait un trou. On retient donc le rectangle de la plage qui va de `recul` metres
avant le mur de la porte jusqu'a ce mur, sur toute la largeur de l'emprise. Il ne
contient ni le bassin ni les points de reintroduction (refuse sinon). Les agents
encore dans l'eau, sur un bord, deja sortis ou plus loin de la porte n'ont pas de
cellule : c'est exact pres de la porte, approche sur le bord gauche du rectangle,
loin de la zone de mesure.

Choix a discuter avant toute conclusion (#124)
----------------------------------------------

  - la ZONE de mesure, par defaut 1,8 m sur 2 m devant la porte, comme celle de E0 ;
  - le RECUL de la salle, 10 m par defaut ;
  - la PORTE : a 1,2 m, elle n'est jamais saturee (E4, #128) et la file reste
    courte ; a 0,8 m, elle l'est. `--fixer largeur_porte=0.8` mesure ce cas ;
  - comme E0, l'evacuation n'a pas de phase stationnaire : chaque point est un
    instant d'une file qui se forme puis se vide.
"""

from __future__ import annotations

import sys
import time
from collections.abc import Sequence
from pathlib import Path

import numpy as np

from viscocrowd.observables.densite import Rectangle
from viscocrowd.observables.diagramme import ClassesDensite, classer
from viscocrowd.scenarios.diagramme_goulot import SerieVoronoi, serie_voronoi

SOLS = ("mouille", "sec")


def salle_porte(piscine, recul: float) -> Rectangle:
    """Rectangle convexe de la plage, de `recul` m avant le mur de la porte jusqu'a lui.

    Raises:
        ValueError: si le rectangle atteint le bassin, une bande de reintroduction ou
            un obstacle de la plage : les cellules n'y seraient plus bornees par les murs.
    """
    if not (np.isfinite(recul) and recul > 0):
        raise ValueError("recul doit etre un reel strictement positif")
    L, W = piscine.longueur_emprise, piscine.largeur_emprise
    x_min = L - recul
    # Points de reintroduction du cote droit du bassin : a un rayon du bord, on garde
    # une marge d'un metre, largement au-dela.
    if x_min <= piscine.bassin.x_max + 1.0:
        raise ValueError("la salle de mesure ne doit pas atteindre le bassin : reduire recul")
    for o in piscine.obstacles:
        if o.x_max > x_min:
            raise ValueError("un obstacle de la plage est dans la salle de mesure")
    return Rectangle(x_min, L, 0.0, W)


def zone_porte(piscine, profondeur: float = 1.8, largeur: float = 2.0) -> Rectangle:
    """Zone de mesure devant la porte, centree sur son axe, a 0,2 m du mur."""
    L = piscine.longueur_emprise
    (_, y_bas), (_, y_haut) = piscine.porte
    yc = 0.5 * (y_bas + y_haut)
    return Rectangle(L - 0.2 - profondeur, L - 0.2, yc - largeur / 2, yc + largeur / 2)


def mesurer(
    configuration: dict,
    graines: Sequence[int],
    *,
    recul: float,
    zone: Rectangle | None,
    debut: float,
    pas_mesure: int,
    fixes: dict | None = None,
) -> dict[tuple[str, int], SerieVoronoi]:
    """Simule la piscine mouillee et son temoin sec pour chaque graine, et mesure.

    Raises:
        ValueError: si une evacuation est incomplete : son diagramme melangerait un
            ecoulement et un blocage.
    """
    from viscocrowd.scenarios.balayage_piscine import _appliquer, temoin
    from viscocrowd.scenarios.piscine import SORTI, ParametresPiscine, simuler_piscine

    graines = list(graines)
    if not graines or len(set(graines)) != len(graines):
        raise ValueError("il faut des graines distinctes")
    parametres = configuration["parametres"]
    for nom, valeur in (fixes or {}).items():
        parametres = _appliquer(parametres, nom, valeur)
    series = {}
    for g in graines:
        for sol, base in zip(SOLS, (parametres, temoin(parametres)), strict=True):
            p = ParametresPiscine(**base, graine=g)
            salle = salle_porte(p.piscine, recul)
            mesure = zone or zone_porte(p.piscine)
            if not salle.contient(mesure):
                raise ValueError("la zone de mesure doit etre incluse dans la salle")
            r = simuler_piscine(p)
            restes = int(np.sum(r.etats[-1] != SORTI))
            if restes:
                raise ValueError(f"graine {g}, {sol} : {restes} baigneurs non sortis")
            series[(sol, g)] = serie_voronoi(
                r.t, r.x, salle, mesure, debut=debut, pas_mesure=pas_mesure
            )
    return series


def agreger(
    series: dict[tuple[str, int], SerieVoronoi], pas_classe: float
) -> dict[str, ClassesDensite]:
    """Un diagramme par sol, sur les memes classes de densite."""
    densites = np.concatenate([s.densite for s in series.values()])
    haut = pas_classe * np.ceil(float(np.max(densites, initial=0.0)) / pas_classe + 1e-9)
    bornes = np.arange(0.0, max(haut, pas_classe) + pas_classe / 2, pas_classe)
    resultat = {}
    for sol in SOLS:
        choisies = [s for (so, _), s in series.items() if so == sol]
        resultat[sol] = classer(
            np.concatenate([s.densite for s in choisies]),
            np.concatenate([s.vitesse for s in choisies]),
            bornes,
        )
    return resultat


def ajouter_commande(sous) -> None:
    commande = sous.add_parser(
        "diagramme-piscine",
        help="M8 : diagramme fondamental devant la porte de la piscine, mouille contre sec",
    )
    commande.add_argument("configuration", type=Path, help="configuration YAML de la piscine")
    commande.add_argument(
        "--graines", type=int, nargs="+", help="defaut : dix graines a partir de celle du YAML"
    )
    commande.add_argument(
        "--fixer",
        nargs="+",
        default=[],
        metavar="NOM=VALEUR",
        help="parametres de balayer-piscine fixes pour la mesure (ex. largeur_porte=0.8)",
    )
    commande.add_argument("--recul", type=float, default=10.0, help="profondeur de la salle, m")
    commande.add_argument(
        "--zone",
        type=float,
        nargs=4,
        metavar=("X_MIN", "X_MAX", "Y_MIN", "Y_MAX"),
        help="zone de mesure, en m (defaut : 1,8 m x 2 m devant la porte)",
    )
    commande.add_argument("--debut", type=float, default=0.0, help="premier instant, s")
    commande.add_argument("--pas-mesure", type=int, default=10, help="un instant sur N")
    commande.add_argument("--pas-classe", type=float, default=0.25, help="pers/m^2")
    commande.add_argument("--sortie", type=Path, help="bilan JSON, series et classes")
    commande.set_defaults(fonction=commande_diagramme)


def commande_diagramme(args) -> int:
    from viscocrowd.io.configuration import lire_configuration
    from viscocrowd.observables import weidmann
    from viscocrowd.scenarios.balayage_piscine import _lire_fixes
    from viscocrowd.scenarios.campagne import contexte, ecrire_json, verifier_sortie

    debut_calcul = time.perf_counter()
    try:
        configuration = lire_configuration(args.configuration)
        if configuration.get("scenario") != "piscine":
            raise ValueError("le diagramme attend une configuration du scenario piscine")
        graines = args.graines or [configuration["graine"] + k for k in range(10)]
        fixes = _lire_fixes(args.fixer)
        zone = Rectangle(*args.zone) if args.zone else None
        if args.sortie is not None:
            if args.sortie.suffix != ".json":
                raise ValueError("le bilan doit porter l'extension .json")
            verifier_sortie(args.sortie)
            if args.sortie.exists():
                raise ValueError(f"{args.sortie} existe deja : choisir un autre fichier")
        series = mesurer(
            configuration,
            graines,
            recul=args.recul,
            zone=zone,
            debut=args.debut,
            pas_mesure=args.pas_mesure,
            fixes=fixes,
        )
        classes = agreger(series, args.pas_classe)
    except (OSError, KeyError, TypeError, ValueError) as erreur:
        print(f"Diagramme refuse : {erreur}", file=sys.stderr)
        return 1

    print(f"M8, piscine devant la porte — graines {graines}, fixes {fixes or 'aucun'}")
    print("ecart-type = dispersion des etats, pas incertitude (points correles)")
    print(
        f"{'rho':>6} {'pts sec':>8} {'v sec':>14} {'pts mouille':>12} {'v mouille':>14} "
        f"{'v Weidmann':>11}"
    )
    sec, mouille = classes["sec"], classes["mouille"]
    for k in np.flatnonzero(sec.effectifs + mouille.effectifs):
        rho = 0.5 * (sec.bornes[k] + sec.bornes[k + 1])
        print(
            f"{rho:>6.2f} {sec.effectifs[k]:>8d} "
            f"{sec.vitesse[k]:>7.3f} ± {sec.ecart_vitesse[k]:<5.3f} "
            f"{mouille.effectifs[k]:>12d} "
            f"{mouille.vitesse[k]:>7.3f} ± {mouille.ecart_vitesse[k]:<5.3f} "
            f"{float(weidmann.vitesse(rho)):>11.3f}"
        )

    if args.sortie is not None:
        args.sortie.parent.mkdir(parents=True, exist_ok=True)
        ecrire_json(
            args.sortie,
            {
                "version": 1,
                "configuration_source": configuration,
                "contexte": contexte(),
                "graines": graines,
                "fixes": fixes,
                "recul": args.recul,
                "zone": args.zone,
                "debut": args.debut,
                "pas_mesure": args.pas_mesure,
                "series": [
                    {
                        "sol": sol,
                        "graine": g,
                        "t": s.t.tolist(),
                        "densite": s.densite.tolist(),
                        "vitesse": s.vitesse.tolist(),
                    }
                    for (sol, g), s in series.items()
                ],
                "classes": {
                    sol: {
                        nom: [None if v != v else v for v in valeurs.tolist()]
                        for nom, valeurs in vars(c).items()
                    }
                    for sol, c in classes.items()
                },
            },
        )
        print(f"Bilan : {args.sortie}")
    print(f"Temps d'execution : {time.perf_counter() - debut_calcul:.1f} s")
    return 0
