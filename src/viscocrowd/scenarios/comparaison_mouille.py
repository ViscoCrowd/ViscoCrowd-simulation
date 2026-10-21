"""Effet du sol mouille sur le banc de couloir, un parametre a la fois.

Le demonstrateur change en meme temps la vitesse souhaitee, le temps de
relaxation et l'adherence de la bande mouillee : il ne permet pas d'attribuer un
effet a l'un d'eux. Ici, on garde la meme population et les memes graines, on
part d'une REFERENCE ou le mouille est identique au sec, puis on ne change qu'un
parametre a la fois, et enfin des combinaisons.

Mesures, par graine :

  - t50 et dernier passage de la section de sortie, en s ;
  - temps moyen de traversee de la bande mouillee, de sa premiere a sa seconde
    frontiere, en s ;
  - distance de freinage moyenne, en m : au-dela de l'entree dans la bande,
    distance parcourue avant que la vitesse ne redescende a moins de 5 cm/s de
    la consigne du mouille, facteur de vitesse compris, comme dans le moteur
    (nulle si l'agent n'a pas a ralentir) ;
  - contacts dans la bande, en paires x s : duree cumulee des paires d'agents,
    tous deux dans la bande, a moins de 1 mm du contact. C'est la mesure de la
    compression.

Toutes les mesures portent sur tous les agents : une simulation trop courte
pour que chacun termine le protocole est refusee (`ProtocoleIncomplet`), au lieu
de moyenner en silence les seuls agents arrives. Le protocole suppose une bande
mouillee unique, encadree de sec.

Les valeurs des milieux restent celles, illustratives, de la configuration de
base : cette comparaison ne calibre rien, elle separe les mecanismes.
"""

from __future__ import annotations

from dataclasses import replace

import numpy as np

from viscocrowd.model.milieu import ParametresMilieu
from viscocrowd.observables.debit import franchissements
from viscocrowd.scenarios.couloir import ParametresCouloir, simuler_couloir

# Nom de la variante -> parametres du mouille que l'on reprend, le reste venant du sec.
VARIANTES: dict[str, tuple[str, ...]] = {
    "reference": (),
    "vitesse": ("vitesse",),
    "relaxation": ("relaxation",),
    "adherence": ("acceleration_max",),
    "vitesse+adherence": ("vitesse", "acceleration_max"),
    "complet": ("vitesse", "relaxation", "acceleration_max"),
}

LIBELLES = {
    "reference": "référence (mouillé = sec)",
    "vitesse": "vitesse seule",
    "relaxation": "relaxation seule",
    "adherence": "adhérence seule",
    "vitesse+adherence": "vitesse + adhérence",
    "complet": "complet (démonstrateur)",
}

MESURES = ("t50", "dernier", "traversee", "freinage", "contacts")
UNITES = {"t50": "s", "dernier": "s", "traversee": "s", "freinage": "m", "contacts": "paires.s"}

# Seuils des definitions ci-dessus.
_PRES_DE_LA_CONSIGNE = 0.05  # m/s
_PRES_DU_CONTACT = 1e-3  # m


def mouille_de_variante(nom: str, sec: ParametresMilieu, mouille: ParametresMilieu):
    """Parametres du mouille pour une variante : ceux du sec, sauf ceux qu'elle reprend."""
    if nom not in VARIANTES:
        raise ValueError(f"variante inconnue {nom!r} ; attendu : {', '.join(VARIANTES)}")
    return replace(sec, **{champ: getattr(mouille, champ) for champ in VARIANTES[nom]})


def _premier_passage(t: np.ndarray, x: np.ndarray, abscisse: float, largeur: float) -> np.ndarray:
    """Instant (N,) du premier franchissement de la droite x = abscisse ; NaN sinon."""
    a, b = np.array([abscisse, -largeur / 2]), np.array([abscisse, largeur / 2])
    passages = franchissements(t, x, a, b)
    instant = np.full(x.shape[1], np.nan)
    # Parcours a rebours : la derniere affectation est le PREMIER passage.
    for agent, moment in zip(passages.agent[::-1], passages.instant[::-1], strict=True):
        instant[agent] = moment
    return instant


class ProtocoleIncomplet(ValueError):  # noqa: N818 - nommage francais du projet
    """Un agent n'a pas termine le protocole : les moyennes porteraient sur des sous-populations."""


def _bande_mouillee(p: ParametresCouloir) -> tuple[float, float]:
    """Frontieres de l'unique bande MOUILLE, encadree de SEC des deux cotes."""
    if p.milieux.count("MOUILLE") != 1:
        raise ValueError("le protocole exige exactement une bande MOUILLE")
    k = p.milieux.index("MOUILLE")
    if not 0 < k < len(p.milieux) - 1 or {p.milieux[k - 1], p.milieux[k + 1]} != {"SEC"}:
        raise ValueError("la bande MOUILLE doit etre encadree de SEC des deux cotes")
    return p.frontieres[k - 1], p.frontieres[k]


def mesurer(p: ParametresCouloir) -> dict[str, float]:
    """Simule le banc et rend les mesures du module pour cette configuration.

    Chaque mesure porte sur TOUS les agents. Si l'un d'eux ne traverse pas la
    bande, ne passe pas la sortie ou ne redescend jamais a la consigne avant la
    fin, la comparaison est refusee : moyenner les seuls agents qui ont termine
    comparerait des variantes sur des effectifs differents sans le dire.

    Raises:
        ValueError: si le protocole n'est pas celui d'une bande mouillee unique
            encadree de sec.
        ProtocoleIncomplet: si un agent n'a pas termine le protocole ; allonger
            la duree.
    """
    entree, sortie = _bande_mouillee(p)
    # La consigne reelle du moteur, facteur de vitesse compris (pas_libre_milieux).
    consigne = p.facteur_vitesse * p.parametres_milieux["MOUILLE"].vitesse

    r = simuler_couloir(p)
    sorties = _premier_passage(r.t, r.x, p.longueur, p.largeur)
    traversee = _premier_passage(r.t, r.x, sortie, p.largeur) - _premier_passage(
        r.t, r.x, entree, p.largeur
    )
    vitesse = np.linalg.norm(r.v, axis=2)
    dans = (r.x[..., 0] >= entree) & (r.x[..., 0] < sortie)
    freinages = np.full(p.n_agents, np.nan)
    for agent in range(p.n_agents):
        # Dans la bande seulement : au-dela, la consigne redevient celle du sec.
        dedans = np.flatnonzero(dans[:, agent])
        calme = dedans[vitesse[dedans, agent] <= consigne + _PRES_DE_LA_CONSIGNE]
        if calme.size:
            freinages[agent] = r.x[calme[0], agent, 0] - entree

    for nom, valeurs in (("passage de la sortie", sorties), ("traversee", traversee)):
        if np.any(np.isnan(valeurs)):
            raise ProtocoleIncomplet(
                f"{int(np.sum(np.isnan(valeurs)))} agent(s) sur {p.n_agents} sans {nom} "
                f"avant {p.duree} s : allonger la duree"
            )
    if np.any(np.isnan(freinages)):
        raise ProtocoleIncomplet(
            f"{int(np.sum(np.isnan(freinages)))} agent(s) jamais revenus a la consigne "
            f"{consigne:.3g} m/s avant la fin de la bande : freinage plus long que la bande, "
            "allonger la bande ou la duree"
        )

    i, j = np.triu_indices(p.n_agents, 1)
    proches = np.linalg.norm(r.x[:, i] - r.x[:, j], axis=2) < 2 * p.rayon + _PRES_DU_CONTACT
    contacts = float(np.sum(proches & dans[:, i] & dans[:, j]) * p.dt)

    return {
        "t50": float(np.median(sorties)),
        "dernier": float(np.max(sorties)),
        "traversee": float(np.mean(traversee)),
        "freinage": float(np.mean(freinages)),
        "contacts": contacts,
    }


def comparer(configuration: dict, graines: list[int]) -> dict[str, np.ndarray]:
    """Mesures de chaque variante, de forme (len(graines), len(MESURES)).

    Args:
        configuration: configuration YAML du couloir, deja lue, avec des milieux
            SEC et MOUILLE declares.
        graines: graines du placement initial, les memes pour toutes les variantes.
    """
    if not graines:
        raise ValueError("il faut au moins une graine")
    base = configuration["parametres"]
    milieux = base["parametres_milieux"]
    sec, mouille = (ParametresMilieu(**dict(milieux[nom])) for nom in ("SEC", "MOUILLE"))
    resultats = {}
    for nom in VARIANTES:
        variante = mouille_de_variante(nom, sec, mouille)
        lignes = []
        for graine in graines:
            p = ParametresCouloir(
                **(base | {"parametres_milieux": milieux | {"SEC": sec, "MOUILLE": variante}}),
                graine=graine,
            )
            mesures = mesurer(p)
            lignes.append([mesures[m] for m in MESURES])
        resultats[nom] = np.array(lignes)
    return resultats
