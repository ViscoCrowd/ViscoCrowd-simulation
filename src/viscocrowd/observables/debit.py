"""Debit a travers une ligne de mesure : porte, echelle ou rebord.

Le debit est un compteur de passage, comme un portique de metro : on trace un
segment [a, b] sur le plan, et on compte les agents qui le traversent.

Pour savoir si un agent a traverse entre deux instants, il suffit de savoir de
quel COTE du segment il se trouve a chaque instant : s'il change de cote, il a
franchi la ligne.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


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
    exactement sur la droite. Sa valeur, divisee par |ab|, est la distance de x
    a la droite, mais seul le signe sert a detecter un franchissement.

    Args:
        x: positions, de forme (..., 2), en metres. N'importe quel nombre de
            dimensions en tete : un agent (2,), N agents (N, 2), ou une
            trajectoire complete (P, N, 2).
        a: premiere extremite du segment, de forme (2,), en metres.
        b: seconde extremite du segment, de forme (2,), en metres.

    Returns:
        Tableau de forme (...) : positif a gauche, negatif a droite, nul sur
        la droite. En m^2.
    """
    ab = b - a
    ax = x - a
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

    Entre deux instants consecutifs, un agent a franchi le segment si :

      1. il a change de cote de la droite (a, b) ;
      2. le point ou il a croise la droite est ENTRE a et b. Sans ce test, un
         agent qui passe a cote de la porte serait compte lui aussi, puisque
         la droite, elle, est infinie.

    Un agent pile sur la droite est range a droite. Ainsi un agent qui s'arrete
    sur la ligne puis repart n'est compte qu'une fois, et pas deux.

    L'instant du passage est interpole : si l'agent etait a 30 cm avant la
    ligne puis a 10 cm apres, il l'a croisee aux trois quarts du pas de temps.
    Pour un mouvement rectiligne uniforme, l'instant obtenu est exact.

    Args:
        t: instants, de forme (P,), en s.
        x: positions, de forme (P, N, 2), en metres (sortie de
            core.integrator.trajectoire).
        a: premiere extremite du segment, de forme (2,), en metres.
        b: seconde extremite du segment, de forme (2,), en metres.

    Returns:
        Les passages detectes, tries par instant.
    """
    c = cote(x, a, b)  # (P, N)
    a_gauche = c > 0.0

    # 1. Changement de cote entre l'instant p et l'instant p + 1.
    pas, agent = np.nonzero(a_gauche[:-1] != a_gauche[1:])
    c_avant, c_apres = c[pas, agent], c[pas + 1, agent]

    # Fraction du pas a laquelle la droite est croisee. Le denominateur ne
    # s'annule jamais : les deux valeurs sont de part et d'autre de zero.
    fraction = c_avant / (c_avant - c_apres)

    # 2. Point de croisement, puis sa position le long du segment : 0 en a,
    # 1 en b. Le passage ne compte que s'il tombe entre les deux.
    x_avant, x_apres = x[pas, agent], x[pas + 1, agent]
    croisement = x_avant + fraction[:, None] * (x_apres - x_avant)
    ab = b - a
    le_long = (croisement - a) @ ab / (ab @ ab)
    sur_le_segment = (le_long >= 0.0) & (le_long <= 1.0)

    pas, agent, fraction = pas[sur_le_segment], agent[sur_le_segment], fraction[sur_le_segment]
    instant = t[pas] + fraction * (t[pas + 1] - t[pas])
    sens = np.where(a_gauche[pas, agent], 1, -1)

    ordre = np.argsort(instant, kind="stable")
    return Franchissements(agent=agent[ordre], instant=instant[ordre], sens=sens[ordre])


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

    Args:
        passages: sortie de `franchissements`.
        largeur: largeur du passage, en metres. En general la longueur |ab|.
        debut: debut de la fenetre de mesure, en s (inclus).
        fin: fin de la fenetre de mesure, en s (exclue).

    Returns:
        Le debit specifique, en pers/m/s.
    """
    if largeur <= 0.0:
        raise ValueError(f"la largeur doit etre strictement positive, recu {largeur}")
    if fin <= debut:
        raise ValueError(f"la fenetre doit avoir une duree positive, recu [{debut}, {fin}[")

    dans_la_fenetre = (passages.instant >= debut) & (passages.instant < fin)
    net = int(np.sum(passages.sens[dans_la_fenetre]))
    return net / ((fin - debut) * largeur)
