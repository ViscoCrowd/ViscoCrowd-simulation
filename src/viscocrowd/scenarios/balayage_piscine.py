"""Balayages E3/E4 de la piscine : quand le sol mouille ralentit-il l'evacuation ? (M6)

Au point de reference, le sol mouille ne change rien de mesurable (#83) : a
1,34 m/s, la relance en ligne droite reste sous l'adherence du mouille
(a_max tau = 1,65 m/s), et 17 m de sol sec separent la bande mouillee de la porte
(issue #26). Ce module fait varier UN parametre a la fois, les autres restant ceux
du YAML, pour tracer les courbes de reponse de la spec § 4 :

  - E3 : largeur de la bande mouillee et adherence du mouille ;
  - E4 : niveau de panique, largeur de la porte et population.

Mesure appariee
---------------

Pour chaque valeur et chaque graine, deux simulations partent des memes positions :

  - MOUILLE : la piscine telle que configuree, a cette valeur ;
  - TEMOIN : la meme piscine, sol entierement sec (bande mouillee de largeur
    nulle, parametres du mouille remplaces par ceux du sec).

L'effet du sol mouille est l'ecart Delta = MOUILLE - TEMOIN, graine par graine.
Comparer des graines differentes melangerait l'effet du sol et le hasard du
placement initial ; les apparier le retire.

Le temoin ne depend pas toujours de la valeur balayee : ni la largeur de la bande
ni l'adherence du mouille ne changent une piscine toute seche. Chaque simulation
est donc identifiee par ses parametres effectifs et calculee une seule fois. Un
point dont le mouille equivaut au sec (bande nulle, ou memes parametres que le
sec) reprend son temoin : son Delta vaut 0 par construction, sans calcul.

Mesures, par simulation, sur TOUTE la population :

  - t50, t90, t100 : instants ou 50, 90 et 100 % des agents sont sortis, en s ;
  - debit : debit specifique a la porte, en pers/(m.s), avec l'estimateur du
    goulot E0 (`debit_seyfried`), pour que les deux restent comparables ;
  - non_sortis : agents encore presents a la fin de `duree`.

Une evacuation INCOMPLETE (non_sortis > 0) est un resultat, pas une erreur : une
porte qui se bouche en est un. Elle est donc conservee, avec t100 = +inf et un
debit indefini, et le balayage continue. Aucune moyenne ne la cache : le tableau
de la commande affiche « incomplet » pour toute valeur ou une graine n'a pas fini,
comme le goulot E0 classe un bouchage a part. Une projection non convergee, elle,
arrete le balayage : la trajectoire n'est pas un etat physique.
"""

from __future__ import annotations

import json
import math
import sys
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from viscocrowd.model.milieu import Milieu
from viscocrowd.scenarios.goulot import debit_seyfried
from viscocrowd.scenarios.piscine import ParametresPiscine, simuler_piscine

MESURES = ("t50", "t90", "t100", "debit", "non_sortis")
UNITES = {"t50": "s", "t90": "s", "t100": "s", "debit": "pers/(m.s)", "non_sortis": "pers"}


@dataclass(frozen=True)
class ParametreBalaye:
    """Un parametre que l'on peut balayer, et ou il se trouve dans le YAML."""

    campagne: str
    unite: str
    description: str
    chemin: tuple[str, ...]


PARAMETRES = {
    "largeur_mouillee": ParametreBalaye(
        "E3",
        "m",
        "largeur de la bande mouillee autour du bassin "
        "(distance mouille-porte = plage_sortie - largeur)",
        ("geometrie", "largeur_mouillee"),
    ),
    "adherence_mouille": ParametreBalaye(
        "E3",
        "m/s^2",
        "acceleration maximale sur le carrelage mouille",
        ("parametres_milieux", "MOUILLE", "acceleration_max"),
    ),
    "facteur_vitesse": ParametreBalaye(
        "E4",
        "-",
        "niveau de panique, multiplie toutes les vitesses souhaitees",
        ("facteur_vitesse",),
    ),
    "largeur_porte": ParametreBalaye(
        "E4", "m", "largeur de la porte", ("geometrie", "largeur_porte")
    ),
    "n_agents": ParametreBalaye("E4", "pers", "nombre de baigneurs", ("n_agents",)),
    # Pas un parametre physique : il sert a verifier que les ecarts ne dependent pas
    # du pas de temps (spec § 5), et a fixer un pas plus fin quand la panique l'exige.
    "dt": ParametreBalaye("M9", "s", "pas de temps (sensibilite numerique)", ("dt",)),
}


@dataclass(frozen=True)
class PointBalayage:
    """Mesures a une valeur du parametre, de forme (len(graines), len(MESURES)).

    Attributes:
        valeur: valeur du parametre balaye, dans son unite.
        mouille: mesures de la piscine configuree.
        temoin: mesures de la meme piscine toute seche, memes graines.
        equivaut_au_sec: vrai si le mouille de ce point ne differe pas du sec ;
            `mouille` est alors une copie de `temoin`.
    """

    valeur: float
    mouille: np.ndarray
    temoin: np.ndarray
    equivaut_au_sec: bool

    @property
    def ecart(self) -> np.ndarray:
        """Delta = mouille - temoin, graine par graine ; NaN si l'un des deux est inacheve."""
        # inf - inf = NaN est voulu : un ecart entre deux evacuations inachevees n'existe pas.
        with np.errstate(invalid="ignore"):
            return self.mouille - self.temoin


def _remplacer(table: dict, chemin: tuple[str, ...], valeur) -> dict:
    """Copie de `table` ou seule la valeur au bout de `chemin` change."""
    tete, *reste = chemin
    if tete not in table:
        raise ValueError(f"la configuration n'a pas de champ {'.'.join(chemin)}")
    return table | {tete: _remplacer(table[tete], tuple(reste), valeur) if reste else valeur}


def temoin(parametres: dict) -> dict:
    """Les memes parametres, sol entierement sec."""
    milieux = parametres["parametres_milieux"]
    return parametres | {
        "geometrie": parametres["geometrie"] | {"largeur_mouillee": 0.0},
        "parametres_milieux": milieux | {"MOUILLE": milieux["SEC"]},
    }


def mouille_equivaut_au_sec(p: ParametresPiscine) -> bool:
    """Vrai si le sol mouille de `p` ne peut rien changer a la simulation."""
    milieux = p.parametres_milieux
    return p.piscine.largeur_mouillee == 0.0 or milieux[Milieu.MOUILLE] == milieux[Milieu.SEC]


def mesurer(p: ParametresPiscine) -> dict[str, float]:
    """Simule l'evacuation et rend les mesures du module.

    Une evacuation incomplete rend +inf pour les fractions non atteintes, et un debit
    indefini (NaN) : un debit mesure sur les seuls agents sortis d'une porte bouchee ne
    se compare a aucun autre.

    Raises:
        ProjectionNonConvergee: si un appel de la projection n'a pas converge.
    """
    # Seuls les instants de sortie servent : on n'archive que le premier et le dernier pas.
    r = simuler_piscine(p, archiver_tous=math.ceil(p.duree / p.dt))
    r.projection.verifier_convergence()
    restants = int(np.sum(~np.isfinite(r.sorties)))
    return {
        "t50": r.temps_evacuation(0.5),
        "t90": r.temps_evacuation(0.9),
        "t100": r.temps_evacuation(1.0),
        "debit": debit_seyfried(r.sorties, p.piscine.largeur_porte) if not restants else math.nan,
        "non_sortis": float(restants),
    }


def _valeurs_valides(parametre: str, valeurs: Sequence[float]) -> list:
    if parametre not in PARAMETRES:
        raise ValueError(f"parametre inconnu {parametre!r} ; attendu : {', '.join(PARAMETRES)}")
    if not valeurs:
        raise ValueError("il faut au moins une valeur")
    if not all(type(v) in (int, float) and math.isfinite(v) for v in valeurs):
        raise ValueError("les valeurs doivent etre des nombres reels finis")
    if len(set(valeurs)) != len(valeurs):
        raise ValueError("les valeurs doivent etre distinctes")
    if parametre == "n_agents":
        # Le debit demande au moins deux sorties.
        if not all(float(v).is_integer() and v >= 2 for v in valeurs):
            raise ValueError("n_agents : entiers d'au moins 2 attendus")
        return [int(v) for v in valeurs]
    return [float(v) for v in valeurs]


# Un plan : pour chaque valeur, les couples (mouille, temoin) de chaque graine.
Plan = list[tuple[float, list[tuple[ParametresPiscine, ParametresPiscine]]]]


def planifier(
    configuration: dict,
    parametre: str,
    valeurs: Sequence[float],
    graines: Sequence[int],
    *,
    fixes: dict[str, float] | None = None,
) -> Plan:
    """Construit, donc controle, toutes les configurations du balayage, sans rien simuler.

    Une valeur hors domaine est ainsi refusee tout de suite, pas apres une heure de calcul.

    Args:
        configuration: configuration YAML de la piscine, deja lue.
        parametre: une cle de PARAMETRES.
        valeurs: valeurs distinctes du parametre, dans l'ordre de calcul.
        graines: graines du placement initial, les memes a chaque valeur.
        fixes: autres parametres de PARAMETRES, fixes a une valeur differente de
            celle du YAML pendant tout le balayage. Par exemple, balayer la
            largeur mouillee a un facteur de panique de 1,5.
    """
    if configuration.get("scenario") != "piscine":
        raise ValueError("le balayage attend une configuration du scenario piscine")
    valeurs = _valeurs_valides(parametre, valeurs)
    graines = list(graines)
    if not graines:
        raise ValueError("il faut au moins une graine")
    if any(type(g) is not int or g < 0 for g in graines) or len(set(graines)) != len(graines):
        raise ValueError("graines distinctes, entieres et positives ou nulles attendues")

    parametres = configuration["parametres"]
    for nom, valeur in (fixes or {}).items():
        if nom == parametre:
            raise ValueError(f"{nom} est le parametre balaye : il ne peut pas etre fixe")
        (valeur,) = _valeurs_valides(nom, [valeur])
        parametres = _remplacer(parametres, PARAMETRES[nom].chemin, valeur)

    plan = []
    for valeur in valeurs:
        base = _remplacer(parametres, PARAMETRES[parametre].chemin, valeur)
        couples = [
            (ParametresPiscine(**base, graine=g), ParametresPiscine(**temoin(base), graine=g))
            for g in graines
        ]
        plan.append((valeur, couples))
    return plan


def executer(
    plan: Plan, *, apres_point: Callable[[PointBalayage], None] | None = None
) -> list[PointBalayage]:
    """Simule le plan et rend un PointBalayage par valeur, dans l'ordre du plan.

    Args:
        plan: rendu par `planifier`.
        apres_point: appelee apres chaque valeur, pour afficher ou enregistrer
            les resultats au fil d'un balayage long.
    """
    deja_calcules: dict[str, dict[str, float]] = {}

    def calculer(p: ParametresPiscine) -> list[float]:
        cle = json.dumps(p.en_dictionnaire(), sort_keys=True)
        if cle not in deja_calcules:
            deja_calcules[cle] = mesurer(p)
        return [deja_calcules[cle][m] for m in MESURES]

    points = []
    for valeur, couples in plan:
        equivaut = mouille_equivaut_au_sec(couples[0][0])
        temoins = np.array([calculer(t) for _, t in couples])
        mouilles = temoins.copy() if equivaut else np.array([calculer(m) for m, _ in couples])
        point = PointBalayage(valeur, mouilles, temoins, equivaut)
        points.append(point)
        if apres_point is not None:
            apres_point(point)
    return points


def balayer(
    configuration: dict,
    parametre: str,
    valeurs: Sequence[float],
    graines: Sequence[int],
    *,
    fixes: dict[str, float] | None = None,
    apres_point: Callable[[PointBalayage], None] | None = None,
) -> list[PointBalayage]:
    """Mesures appariees mouille / temoin pour chaque valeur : `planifier` puis `executer`."""
    plan = planifier(configuration, parametre, valeurs, graines, fixes=fixes)
    return executer(plan, apres_point=apres_point)


def _en_json(point: PointBalayage) -> dict:
    """Mesures brutes, graine par graine : de quoi recalculer tout tableau ou figure."""

    def lignes(tableau: np.ndarray) -> list[list[float | None]]:
        return [[float(v) if math.isfinite(v) else None for v in ligne] for ligne in tableau]

    return {
        "valeur": point.valeur,
        "equivaut_au_sec": point.equivaut_au_sec,
        "mouille": lignes(point.mouille),
        "temoin": lignes(point.temoin),
    }


# Colonnes du tableau dont on affiche l'ecart moyen ; non_sortis a sa propre colonne.
_ECARTS = ("t50", "t90", "t100", "debit")


def _moyenne_ecart(valeurs: np.ndarray, decimales: int) -> str:
    """« moyenne ± ecart-type » sur toutes les graines, ou « incomplet k/n ».

    Jamais de moyenne sur une partie des graines : une seule valeur non finie (une
    evacuation inachevee) rend la case « incomplet ».
    """
    manquantes = int(np.sum(~np.isfinite(valeurs)))
    if manquantes:
        return f"incomplet {manquantes}/{valeurs.size}"
    ecart = np.std(valeurs, ddof=1) if valeurs.size > 1 else 0.0
    return f"{np.mean(valeurs):.{decimales}f} ± {ecart:.{decimales}f}"


def _ligne_tableau(point: PointBalayage) -> str:
    k = {m: MESURES.index(m) for m in MESURES}
    ecart = point.ecart[:, k["t100"]]
    finis = np.isfinite(ecart)
    non_sortis = f"{point.mouille[:, k['non_sortis']].sum():.0f}/"
    non_sortis += f"{point.temoin[:, k['non_sortis']].sum():.0f}"
    cellules = [
        f"{point.valeur:>8g}",
        f"{_moyenne_ecart(point.mouille[:, k['t100']], 2):>16}",
        *(f"{_moyenne_ecart(point.ecart[:, k[m]], 3):>17}" for m in _ECARTS),
        f"{non_sortis:>11}",
        f"{int(np.sum(ecart[finis] > 0)):>8}/{int(finis.sum())}",
    ]
    if point.equivaut_au_sec:
        cellules.append("  (= temoin)")
    return " ".join(cellules)


def ajouter_commande(sous) -> None:
    commande = sous.add_parser(
        "balayer-piscine", help="effet du sol mouille selon un parametre (E3/E4)"
    )
    commande.add_argument("configuration", type=Path, help="configuration YAML de la piscine")
    commande.add_argument("--parametre", required=True, choices=list(PARAMETRES))
    commande.add_argument("--valeurs", required=True, nargs="+", type=float)
    commande.add_argument(
        "--graines", nargs="+", type=int, help="defaut : dix graines a partir de celle du YAML"
    )
    commande.add_argument(
        "--fixer",
        nargs="+",
        default=[],
        metavar="NOM=VALEUR",
        help="autres parametres, fixes pendant le balayage (ex. facteur_vitesse=1.5)",
    )
    commande.add_argument("--sortie", type=Path, help="bilan JSON, mesures graine par graine")
    commande.set_defaults(fonction=commande_balayer)


def _lire_fixes(textes: list[str]) -> dict[str, float]:
    fixes = {}
    for texte in textes:
        nom, egal, valeur = texte.partition("=")
        if not egal or nom not in PARAMETRES:
            raise ValueError(f"--fixer attend NOM=VALEUR avec NOM parmi {', '.join(PARAMETRES)}")
        if nom in fixes:
            raise ValueError(f"{nom} est fixe deux fois")
        fixes[nom] = float(valeur)
    return fixes


def commande_balayer(args) -> int:
    from viscocrowd.geometry.projection import ProjectionNonConvergee
    from viscocrowd.io.configuration import lire_configuration
    from viscocrowd.scenarios.campagne import _ecrire_json, _verifier_sortie, contexte

    debut = time.perf_counter()
    try:
        configuration = lire_configuration(args.configuration)
        graines = args.graines or [configuration["graine"] + k for k in range(10)]
        fixes = _lire_fixes(args.fixer)
        plan = planifier(configuration, args.parametre, args.valeurs, graines, fixes=fixes)
        if args.sortie is not None:
            if args.sortie.suffix != ".json":
                raise ValueError("le bilan doit porter l'extension .json")
            _verifier_sortie(args.sortie)
            if args.sortie.exists():
                raise ValueError(f"{args.sortie} existe deja : choisir un autre fichier")
            args.sortie.parent.mkdir(parents=True, exist_ok=True)
        initial = contexte()
        bilan = {
            "version": 1,
            "parametre": args.parametre,
            "unite": PARAMETRES[args.parametre].unite,
            "fixes": fixes,
            "graines": graines,
            "mesures": list(MESURES),
            "unites": UNITES,
            "configuration_source": configuration,
            "contexte": initial,
            "points": [],
        }

        description = PARAMETRES[args.parametre]
        print(f"{description.campagne} — balayage de {args.parametre} ({description.unite})")
        print(f"  {description.description}")
        autres = ", ".join(f"{nom} = {v:g}" for nom, v in fixes.items()) or "aucun"
        print(f"Parametres fixes hors YAML : {autres} ; graines {graines}")
        print("Delta = mouille - temoin (meme piscine toute seche, meme graine) ; moyenne ± ecart")
        print("non sortis : total sur les graines, mouille/temoin, a la fin de la duree")
        print(
            f"{'valeur':>8} {'t100 mouille (s)':>16} "
            + " ".join(f"{'Delta ' + m + ' (' + UNITES[m] + ')':>17}" for m in _ECARTS)
            + f" {'non sortis':>11} Delta t100 > 0"
        )

        def apres_point(point: PointBalayage) -> None:
            print(_ligne_tableau(point), flush=True)
            if contexte() != initial:
                raise ValueError("code ou environnement modifie pendant le balayage ; relancer")
            if args.sortie is not None:
                bilan["points"].append(_en_json(point))
                _ecrire_json(args.sortie, bilan)

        executer(plan, apres_point=apres_point)
    except KeyboardInterrupt:
        print("Balayage interrompu ; les valeurs terminees sont dans le bilan.", file=sys.stderr)
        return 130
    except (OSError, KeyError, ValueError, ProjectionNonConvergee) as erreur:
        print(f"Balayage refuse : {erreur}", file=sys.stderr)
        return 1
    if args.sortie is not None:
        print(f"Mesures graine par graine : {args.sortie}")
    print(f"Temps d'execution : {time.perf_counter() - debut:.1f} s")
    return 0
