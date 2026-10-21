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
sortant. Concretement : son DERNIER passage a travers le segment est sortant, et
il termine de l'autre cote de la droite.

Le segment s'oriente comme pour `debit_specifique` : en marchant de a vers b, le
sens de sortie va de gauche a droite. L'exterieur est donc a droite (`cote < 0`).

Cette definition est rendue a posteriori, sur une trajectoire archivee : elle vaut
que le scenario retire les agents sortis (etat absorbant) ou qu'il les laisse
continuer. « Ne revient plus » s'entend jusqu'au dernier instant enregistre.

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

import numpy as np

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
        # Nombre d'agents a attendre, sans qu'une erreur d'arrondi (0,9 x 10 =
        # 9,000000000000002) n'en exige un de plus.
        rang = max(1, math.ceil(fraction * self.n_agents - 1e-9))
        instants = np.sort(self.instant[self.sortis])
        return float(instants[rang - 1]) if rang <= instants.size else math.inf


def sorties_definitives(t: np.ndarray, x: np.ndarray, a: np.ndarray, b: np.ndarray) -> Sorties:
    """Instant de sortie definitive de chaque agent a travers le segment [a, b].

    Args:
        t: instants, de forme (P,), en s.
        x: positions, de forme (P, N, 2), en m.
        a, b: extremites du segment de sortie, (2,), en m, orientees pour que la
            sortie aille de gauche a droite.

    Returns:
        Les sorties, une valeur par agent.

    Raises:
        ValueError: si les formes sont incoherentes ou le segment degenere.
    """
    t, x = np.asarray(t, dtype=float), np.asarray(x, dtype=float)
    if x.ndim != 3 or x.shape[2] != 2 or t.shape != (x.shape[0],):
        raise ValueError(
            f"t et x doivent etre de formes (P,) et (P, N, 2), recu {t.shape}, {x.shape}"
        )
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

    dehors_a_la_fin = cote(x[-1], a, b) < 0.0
    sorti = (dernier_sens == 1) & dehors_a_la_fin
    instant[sorti] = dernier_instant[sorti]
    return Sorties(instant)
