"""Evacuation definitive : distinguer un franchissement d'une sortie (issue #11).

`debit.franchissements` compte des PASSAGES a travers une ligne. Ce n'est pas un
nombre d'evacues : un agent repousse puis ressorti compte trois passages pour
une seule sortie, et une ligne de mesure n'est pas forcement une sortie.
Deduire un temps d'evacuation de ce compteur serait faux, et faux dans le sens
optimiste, precisement dans les refoulements qu'on veut etudier.

Definition retenue
------------------

Un agent est SORTI quand il a franchi le segment de sortie dans le sens sortant
et qu'il ne le refranchit plus dans l'autre sens jusqu'a la fin de
l'enregistrement. Son instant de sortie est celui de ce dernier franchissement
sortant. Concretement : son DERNIER passage a travers le segment est sortant,
il termine de l'autre cote de la droite et ne revient jamais du cote interieur
apres ce passage, meme hors du segment de porte.

Le segment s'oriente comme pour `debit_specifique` : en marchant de a vers b, le
sens de sortie va de gauche a droite. L'exterieur est donc a droite (`cote < 0`).

Cette definition est rendue a posteriori, sur une trajectoire a population fixe
et identites stables. Un futur retrait d'agents devra conserver leur historique
ou adapter le format ; aucun etat absorbant n'est introduit ici. « Ne revient
plus » s'entend jusqu'au dernier instant enregistre. Le complement du nombre de
sortis n'est pas le nombre geometrique d'agents a l'interieur : un agent dehors
qui reviendra plus tard n'est pas encore classe definitivement sorti.

Proprietes, vraies par construction et testees
----------------------------------------------

  - chaque agent est compte au plus une fois : n_sortis(t_final) <= N ;
  - n_sortis(t) est croissante ;
  - a tout instant, agents non encore sortis + agents sortis = N ;
  - un agent qui traverse, revient et retraverse compte une sortie, la
    troisieme, la ou `franchissements` compte trois passages.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from viscocrowd.core.verifications import exiger_fini
from viscocrowd.io.trajectoires import Trajectoire, charger_et_valider_complete
from viscocrowd.observables.debit import cote, franchissements


@dataclass(frozen=True)
class Sorties:
    """Instant de sortie definitive de chaque agent.

    Attributes:
        instant: (N,) instant de sortie definitive, en s ; NaN pour un agent qui
            n'est pas sorti avant la fin de l'enregistrement.
    """

    instant: np.ndarray

    @property
    def n_agents(self) -> int:
        return int(self.instant.size)

    @property
    def sortis(self) -> np.ndarray:
        """(N,) vrai pour les agents sortis."""
        return ~np.isnan(self.instant)

    def nombre_sortis(self, t: np.ndarray | float) -> np.ndarray:
        """Nombre d'agents sortis a l'instant t (inclus), croissant en t par construction."""
        t = np.asarray(t, dtype=float)
        exiger_fini("Instants de comptage des sorties.", t=t)
        instants = np.sort(self.instant[self.sortis])
        return np.searchsorted(instants, t, side="right")

    def temps_evacuation(self, fraction: float = 1.0) -> float:
        """Instant ou la fraction donnee de la population est sortie, en s.

        fraction = 1 donne l'instant de sortie du dernier agent ; 0,5 et 0,9 donnent
        t50 et t90, plus robustes qu'un maximum qui depend d'un seul retardataire.
        Vaut +inf si cette fraction n'est pas atteinte avant la fin de l'enregistrement.
        """
        if not (np.isfinite(fraction) and 0.0 < fraction <= 1.0):
            raise ValueError(f"fraction doit etre dans ]0, 1], recu {fraction}")
        # Un seul arrondi flottant est tolere : une marge absolue de 1e-9
        # reduisait aussi le rang de fractions reellement au-dessus du seuil.
        rang = max(1, math.ceil(math.nextafter(fraction * self.n_agents, -math.inf)))
        instants = np.sort(self.instant[self.sortis])
        return float(instants[rang - 1]) if rang <= instants.size else math.inf


def sorties_definitives(
    t: np.ndarray | Trajectoire,
    x: np.ndarray,
    a: np.ndarray | None = None,
    b: np.ndarray | None = None,
) -> Sorties:
    """Instant de sortie definitive de chaque agent a travers le segment [a, b].

    Args:
        t: instants, de forme (P,), en s, ou objet Trajectoire complet.
        x: positions, de forme (P, N, 2), en m, ou extremite 'a' si t est une Trajectoire.
        a: extremite 'a' du segment de sortie (ou 'b' si t est Trajectoire).
        b: extremite 'b' du segment de sortie.

    Returns:
        Les sorties, une valeur par agent.

    Raises:
        ValueError: si les formes, valeurs finies, temps ou segment sont invalides,
            ou si une archive espacee est fournie (issue #73).
    """
    if isinstance(t, Trajectoire):
        t.exiger_complete("le calcul de sorties definitives")
        if a is None:
            raise ValueError("les extremites a et b du segment de sortie sont requises")
        return sorties_definitives(t.t, t.x, x, a)

    if a is None or b is None:
        raise ValueError("les extremites a et b du segment de sortie sont requises")
    t, x = np.asarray(t, dtype=float), np.asarray(x, dtype=float)
    if x.ndim != 3 or x.shape[2] != 2 or t.shape != (x.shape[0],):
        raise ValueError(
            f"t et x doivent etre de formes (P,) et (P, N, 2), recu {t.shape}, {x.shape}"
        )
    a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    if a.shape != (2,) or b.shape != (2,):
        raise ValueError("a et b doivent etre de forme (2,)")
    exiger_fini("Trajectoire de mesure des sorties.", t=t, x=x, a=a, b=b)
    if np.any(np.diff(t) <= 0.0):
        raise ValueError("t doit etre strictement croissant")
    c = cote(x, a, b)  # valide aussi le segment, meme avec une trajectoire vide
    instant = np.full(x.shape[1], np.nan)
    if x.shape[0] == 0:
        return Sorties(instant)

    passages = franchissements(t, x, a, b)  # tries par instant croissant
    # Rang du DERNIER passage de chaque agent. Une affectation NumPy a indices
    # repetes ne garantit pas que la derniere valeur l'emporte : on le cherche
    # explicitement, comme premiere occurrence dans la liste renversee.
    agents, depuis_la_fin = np.unique(passages.agent[::-1], return_index=True)
    rang = passages.agent.size - 1 - depuis_la_fin
    dernier_sens = np.zeros(x.shape[1], dtype=np.int64)
    dernier_instant = np.full(x.shape[1], np.nan)
    dernier_sens[agents] = passages.sens[rang]
    dernier_instant[agents] = passages.instant[rang]

    dehors_a_la_fin = c[-1] < 0.0
    dernier_interieur = np.max(np.where(c > 0.0, t[:, None], -np.inf), axis=0)
    sorti = (dernier_sens == 1) & dehors_a_la_fin & (dernier_instant > dernier_interieur)
    instant[sorti] = dernier_instant[sorti]
    return Sorties(instant)


def sorties_definitives_trajectoire(
    archive: Trajectoire | str | Path, a: np.ndarray, b: np.ndarray
) -> Sorties:
    """Instant de sortie definitive de chaque agent a travers [a, b] depuis une archive.

    Refuse toute archive espacee (K > 1, issue #73) : des images espacees
    ne permettent pas de garantir l'absence de retours interieurs non echantillonnes.
    """
    donnees = charger_et_valider_complete(archive, "le calcul de sorties definitives")
    return sorties_definitives(donnees.t, donnees.x, a, b)
