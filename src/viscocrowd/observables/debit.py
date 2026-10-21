"""Debit a travers une ligne de mesure : porte, echelle ou rebord.

Le debit est un compteur de passage, comme un portique de metro : on trace un
segment [a, b] sur le plan, et on compte les agents qui le traversent.

Pour savoir si un agent a traverse entre deux instants, il suffit de savoir de
quel COTE du segment il se trouve a chaque instant : s'il passe d'un cote a
l'autre, il a franchi la ligne.

Attention au troisieme cas : un agent peut se trouver EXACTEMENT sur la droite.
Le ranger d'office a droite ferait compter deux faux passages a celui qui touche
la ligne et repart du meme cote. On distingue donc trois etats — a gauche, a
droite, sur la droite — et un franchissement n'est compte que lorsque l'agent
arrive effectivement de l'AUTRE cote. Voir `franchissements`.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


def _verifier_segment(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Valide la ligne de mesure et rend le vecteur a->b.

    Un segment de longueur nulle ne definit aucun cote : `cote` vaudrait zero
    partout, aucun changement de cote ne serait detecte, et la mesure
    renverrait « aucun passage » — resultat indiscernable d'une porte que
    personne n'emprunte. C'est une erreur de configuration de la ligne de
    mesure, pas un resultat : on la signale.
    """
    a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    if not (np.all(np.isfinite(a)) and np.all(np.isfinite(b))):
        raise ValueError(f"les extremites du segment doivent etre finies, recu a={a}, b={b}")
    ab = b - a
    if not np.any(ab):
        raise ValueError(
            f"le segment de mesure est de longueur nulle (a = b = {a}) : "
            "il ne definit aucun cote, donc aucun franchissement"
        )
    return ab


def cote(x: np.ndarray, a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """De quel cote de la droite (a, b) se trouve chaque point x.

    On regarde la droite en marchant de a vers b :

                    x  (cote > 0, a gauche)
                    .
        a ------------------> b
                    .
                    x  (cote < 0, a droite)

    Le calcul est le produit vectoriel en 2D des vecteurs a->b et a->x. Son
    signe dit si x est a gauche ou a droite, et il vaut zero si x est
    exactement sur la droite — troisieme cas, qui n'est NI a gauche NI a
    droite, et que `franchissements` traite comme tel. Sa valeur, divisee par
    |ab|, est la distance de x a la droite, mais seul le signe sert a detecter
    un franchissement.

    Args:
        x: positions, de forme (..., 2), en metres. N'importe quel nombre de
            dimensions en tete : un agent (2,), N agents (N, 2), ou une
            trajectoire complete (P, N, 2).
        a: premiere extremite du segment, de forme (2,), en metres.
        b: seconde extremite du segment, de forme (2,), en metres.

    Returns:
        Tableau de forme (...) : positif a gauche, negatif a droite, nul sur
        la droite. En m^2.

    Raises:
        ValueError: si a et b sont confondus, ou si une extremite n'est pas finie.
    """
    ab = _verifier_segment(a, b)
    ax = np.asarray(x, dtype=float) - np.asarray(a, dtype=float)
    return ab[0] * ax[..., 1] - ab[1] * ax[..., 0]


@dataclass(frozen=True)
class Franchissements:
    """Liste des passages a travers un segment, un element par passage.

    Les trois tableaux ont la meme longueur M, le nombre de passages detectes,
    et sont tries par instant croissant.
    """

    agent: np.ndarray  # (M,) indice de l'agent qui passe
    instant: np.ndarray  # (M,) instant du passage, en s
    sens: np.ndarray  # (M,) +1 de gauche a droite, -1 de droite a gauche

    @property
    def nombre(self) -> int:
        """Nombre de passages, tous sens confondus."""
        return int(self.agent.size)


def franchissements(t: np.ndarray, x: np.ndarray, a: np.ndarray, b: np.ndarray) -> Franchissements:
    """Detecte tous les passages a travers le segment [a, b].

    Un agent a franchi le segment lorsque :

      1. il ARRIVE d'un cote de la droite (a, b) alors qu'il etait de l'autre.
         On compare donc l'echantillon courant au dernier echantillon ou l'agent
         etait strictement d'un cote, en SAUTANT ceux ou il etait pile sur la
         droite. Toucher la ligne et repartir du meme cote ne compte pas ;
         s'arreter dessus puis la traverser compte une fois.
      2. le point ou il a croise la droite est ENTRE a et b. Sans ce test, un
         agent qui passe a cote de la porte serait compte lui aussi, puisque
         la droite, elle, est infinie.

    L'instant du passage est interpole entre ces deux echantillons : si l'agent
    etait a 30 cm avant la ligne puis a 10 cm apres, il l'a croisee aux trois
    quarts du pas de temps. Pour un mouvement rectiligne uniforme, l'instant
    obtenu est exact. Quand l'agent a stationne sur la ligne, l'interpolation
    porte sur tout l'intervalle de stationnement, ce qui place le passage a
    l'interieur de celui-ci.

    Args:
        t: instants, de forme (P,), en s.
        x: positions, de forme (P, N, 2), en metres (sortie de
            core.integrator.trajectoire).
        a: premiere extremite du segment, de forme (2,), en metres.
        b: seconde extremite du segment, de forme (2,), en metres.

    Returns:
        Les passages detectes, tries par instant.

    Raises:
        ValueError: si a et b sont confondus, ou si une extremite n'est pas finie.
    """
    ab = _verifier_segment(a, b)
    t, x = np.asarray(t, dtype=float), np.asarray(x, dtype=float)
    c = cote(x, a, b)  # (P, N)
    vide = Franchissements(
        agent=np.empty(0, dtype=np.int64),
        instant=np.empty(0, dtype=float),
        sens=np.empty(0, dtype=np.int64),
    )
    if c.shape[0] < 2:
        return vide

    signe = np.sign(c)  # -1 a droite, +1 a gauche, 0 pile sur la droite
    place = signe != 0

    # Pour chaque instant, le rang du dernier echantillon ou l'agent etait
    # strictement d'un cote, celui-ci inclus. `deja_place` evite de pointer sur
    # l'echantillon 0 tant qu'aucun cote n'a encore ete observe.
    rangs = np.where(place, np.arange(c.shape[0])[:, None], 0)
    dernier = np.maximum.accumulate(rangs, axis=0)
    deja_place = np.maximum.accumulate(place, axis=0)
    signe_dernier = np.take_along_axis(signe, dernier, axis=0)

    # 1. Arrivee de l'autre cote : l'agent est place, il l'etait deja avant, et
    # ce n'est pas du meme cote.
    traverse = place[1:] & deja_place[:-1] & (signe[1:] != signe_dernier[:-1])
    apres, agent = np.nonzero(traverse)
    if agent.size == 0:
        return vide
    avant = dernier[apres, agent]  # rang du dernier echantillon de l'autre cote
    apres = apres + 1
    a = np.asarray(a, dtype=float)

    c_avant, c_apres = c[avant, agent], c[apres, agent]

    # Fraction du pas a laquelle la droite est croisee. Le denominateur ne
    # s'annule jamais : les deux valeurs sont strictement de part et d'autre de zero.
    fraction = c_avant / (c_avant - c_apres)

    # 2. Point de croisement, puis sa position le long du segment : 0 en a,
    # 1 en b. Le passage ne compte que s'il tombe entre les deux.
    x_avant, x_apres = x[avant, agent], x[apres, agent]
    croisement = x_avant + fraction[:, None] * (x_apres - x_avant)
    le_long = (croisement - a) @ ab / (ab @ ab)
    sur_le_segment = (le_long >= 0.0) & (le_long <= 1.0)
    instant = t[avant] + fraction * (t[apres] - t[avant])

    # Cas general ci-dessus : deux echantillons consecutifs, de part et d'autre.
    # Si l'agent est passe PAR la droite (un ou plusieurs echantillons dessus), la
    # ligne droite entre les deux echantillons stricts ne dit rien du point ou il
    # l'a traversee : on le localise avec les echantillons poses sur la droite.
    for k in np.flatnonzero(apres - avant > 1):
        instant_k = _instant_sur_la_porte(t, x, agent[k], avant[k], apres[k], a, ab)
        sur_le_segment[k] = instant_k is not None
        if instant_k is not None:
            instant[k] = instant_k

    agent, avant = agent[sur_le_segment], avant[sur_le_segment]
    instant = instant[sur_le_segment]
    sens = signe[avant, agent].astype(np.int64)  # +1 : il venait de gauche

    ordre = np.argsort(instant, kind="stable")
    return Franchissements(agent=agent[ordre], instant=instant[ordre], sens=sens[ordre])


def _instant_sur_la_porte(
    t: np.ndarray, x: np.ndarray, agent: int, avant: int, apres: int, a: np.ndarray, ab: np.ndarray
) -> float | None:
    """Instant ou un agent passe par la droite DANS la porte, ou None s'il passe hors de la porte.

    L'agent etait strictement d'un cote a l'echantillon `avant`, strictement de
    l'autre a `apres`, et exactement SUR la droite entre les deux. Sa trajectoire
    est une ligne brisee : elle touche la droite au premier echantillon pose
    dessus, puis la suit d'un echantillon pose dessus au suivant, puis la quitte
    au dernier. Il traverse donc la porte si cette portion de droite rencontre le
    segment [a, b].

    Exemple, porte de (0, 0) a (1, 0), positions (0,99 ; 0,01), (1,01 ; 0),
    (0,99 ; -0,01) : l'agent est passe par (1,01 ; 0), HORS de la porte. Interpoler
    entre le premier et le dernier echantillon donnerait un croisement fictif en
    (0,99 ; 0), dans la porte, et compterait un passage qui n'a pas eu lieu.

    L'instant rendu est celui ou l'agent entre pour la premiere fois dans la porte
    en suivant la droite : il est dans l'intervalle de stationnement, et vaut
    exactement l'instant de l'echantillon quand celui-ci est dans la porte.
    """
    rangs = np.arange(avant + 1, apres)  # les echantillons exactement sur la droite
    # Position le long du segment : 0 en a, 1 en b.
    s = (x[rangs, agent] - a) @ ab / (ab @ ab)

    for j in range(rangs.size):
        if 0.0 <= s[j] <= 1.0:
            return float(t[rangs[j]])
        if j + 1 < rangs.size and max(s[j], s[j + 1]) >= 0.0 and min(s[j], s[j + 1]) <= 1.0:
            # Le glissement de j a j+1 entre dans la porte par l'extremite a ou b.
            borne = 0.0 if s[j] < 0.0 else 1.0
            part = (borne - s[j]) / (s[j + 1] - s[j])
            return float(t[rangs[j]] + part * (t[rangs[j + 1]] - t[rangs[j]]))
    return None


def debit_specifique(passages: Franchissements, largeur: float, debut: float, fin: float) -> float:
    """Debit specifique a travers le segment, sur la fenetre de temps [debut, fin[.

        J = (passages dans le sens +1  -  passages dans le sens -1) / (duree * largeur)

    On divise par la LARGEUR pour comparer des passages de tailles differentes :
    une porte de 2 m laisse forcement passer plus de monde qu'une porte de 1 m,
    mais leur debit par metre peut etre le meme. C'est la grandeur que donne la
    litterature, de l'ordre de 1,2 a 1,4 pers/m/s pour un goulot.

    On retire les passages en sens inverse : un agent repousse en arriere apres
    avoir passe la ligne n'est pas sorti. Orienter le segment pour que le sens
    de sortie aille de gauche a droite (cf. `cote`), sinon le debit est negatif.

    CE QUE CETTE GRANDEUR N'EST PAS
    -------------------------------

    Un flux NET a travers une ligne n'est pas un nombre d'evacues, et le temps
    d'evacuation ne peut pas s'en deduire. Deux raisons :

      - un agent peut traverser, revenir, puis retraverser : il compte alors
        trois passages et un flux net de un, alors qu'il n'est sorti qu'une
        fois ;
      - une ligne de mesure n'est pas forcement une sortie. On en place aussi en
        travers du bassin ou devant l'echelle, pour mesurer un flux interne.

    Le flux net repond a « combien de personnes par metre et par seconde
    franchissent cette ligne », ce qu'il faut pour un diagramme fondamental et
    pour comparer a Weidmann. Pour « combien de personnes ont quitte la
    piscine » et « au bout de combien de temps », utiliser l'instant de sortie
    DEFINITIVE de chaque agent (`observables.sortie.sorties_definitives`), et non
    ce compteur.

    Args:
        passages: sortie de `franchissements`.
        largeur: largeur du passage, en metres. En general la longueur |ab|.
        debut: debut de la fenetre de mesure, en s (inclus).
        fin: fin de la fenetre de mesure, en s (exclue).

    Returns:
        Le debit specifique, en pers/m/s.
    """
    # Tests en forme POSITIVE : `largeur <= 0.0` et `fin <= debut` sont faux pour
    # un NaN, qui ressortait alors en debit NaN. Une borne ou une largeur infinie,
    # elle, rendait un debit nul, indiscernable d'une porte que personne n'emprunte.
    if not (np.isfinite(largeur) and largeur > 0.0):
        raise ValueError(f"la largeur doit etre finie et strictement positive, recu {largeur}")
    if not (np.isfinite(debut) and np.isfinite(fin) and fin > debut):
        raise ValueError(f"la fenetre doit etre finie et de duree positive, recu [{debut}, {fin}[")

    dans_la_fenetre = (passages.instant >= debut) & (passages.instant < fin)
    net = int(np.sum(passages.sens[dans_la_fenetre]))
    return net / ((fin - debut) * largeur)
