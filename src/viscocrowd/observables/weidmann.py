"""Diagramme fondamental de Weidmann : la reference de la litterature.

Les consignes demandent de confronter les resultats a un resultat connu. Pour
une foule, c'est le diagramme fondamental de Weidmann (1993), qui donne la
vitesse de marche en fonction de la densite :

    v(rho) = v0 * (1 - exp(-gamma * (1/rho - 1/rho_max)))

et le debit specifique s'en deduit par J = rho * v.

Lecture : a faible densite, chacun marche a sa vitesse libre v0, mais il passe
peu de monde. Plus la foule est dense, plus il passe de monde... jusqu'a ce que
la gene ralentisse tout le monde. A rho_max, plus personne n'avance. Le debit
trace en fonction de la densite forme donc une colline, de sommet environ
1,22 pers/m/s vers 1,75 pers/m^2.

Source
------

Weidmann, U. (1993), *Transporttechnik der Fussgaenger*, 2e edition, IVT,
ETH Zurich, section 4.31.1, p. 62 : v0 = 1,34 m/s, gamma = 1,913 pers/m^2,
rho_max = 5,4 pers/m^2. Reference localisee a la page pres en relecture de la
PR #9 ; le scan diffuse n'a pas de couche texte, donc a recopier depuis la
source lors de la redaction de la bibliographie.

CE QUE CETTE COURBE VALIDE, ET CE QU'ELLE NE VALIDE PAS
-------------------------------------------------------

La section citee traite de la **marche unidirectionnelle en terrain plat**, en
conditions normales (p. 64). C'est donc une reference pour la partie PIETONNE
de notre modele — le carrelage mouille, le goulot, la zone sous l'echelle — et
pour elle seulement.

Elle ne valide PAS :

  - la **nage** dans le bassin, qui n'est pas de la marche : ni la vitesse
    libre, ni la densite de blocage, ni la forme de la courbe n'ont de raison
    d'etre transposables ;
  - l'extraction aquatique, ou les agents sortent de l'eau par un rebord ou une
    echelle, mouvement qui n'a pas d'equivalent dans la source ;
  - un ecoulement **bidirectionnel** ou croise, pas plus que la panique, qui
    sort des « conditions normales » de la source.

Autrement dit, la comparaison a Weidmann est un critere de validation pour nos
zones seches, pas un verdict sur le scenario entier. Le rapport doit le dire,
sinon la confrontation n'a pas de valeur.
"""

from __future__ import annotations

import numpy as np

V0 = 1.34  # vitesse de marche libre, m/s
GAMMA = 1.913  # parametre de forme, pers/m^2
RHO_MAX = 5.4  # densite a laquelle la marche s'arrete, pers/m^2


def _verifier_densite(rho: np.ndarray | float) -> np.ndarray:
    """Valide une densite et la rend en tableau de flottants.

    Une densite est un nombre de personnes par metre carre : elle est positive
    ou nulle, et finie. Sans ce controle, le masque `where=rho > 0` traitait
    toute densite NEGATIVE comme la limite a densite nulle et rendait la vitesse
    libre v0, pendant que le debit rendait une valeur negative : une entree
    fautive ressortait en resultat d'apparence plausible. Un NaN, lui, ressortait
    en vitesse nulle, donc indiscernable d'une foule bloquee.
    """
    rho = np.asarray(rho, dtype=float)
    if not np.all(np.isfinite(rho)):
        raise ValueError("la densite doit etre finie (ni NaN ni infinie)")
    if np.any(rho < 0.0):
        raise ValueError("la densite doit etre positive ou nulle, en pers/m^2")
    return rho


def vitesse(rho: np.ndarray | float) -> np.ndarray:
    """Vitesse de marche de Weidmann, en m/s, pour une densite en pers/m^2.

    Nulle au-dela de rho_max ; vaut v0 a densite nulle.

    Args:
        rho: densite, scalaire ou tableau, en pers/m^2. Positive ou nulle et finie.

    Raises:
        ValueError: si une densite est negative, NaN ou infinie.
    """
    rho = _verifier_densite(rho)
    # A densite nulle, 1/rho est infini et l'exponentielle vaut zero : v = v0.
    # On evite la division par zero en remplacant rho = 0 par une valeur sans effet.
    inverse = np.divide(1.0, rho, out=np.full_like(rho, np.inf), where=rho > 0.0)
    v = V0 * (1.0 - np.exp(-GAMMA * (inverse - 1.0 / RHO_MAX)))
    return np.where(rho < RHO_MAX, v, 0.0)


def debit_specifique(rho: np.ndarray | float) -> np.ndarray:
    """Debit specifique de Weidmann, J = rho * v(rho), en pers/m/s.

    Args:
        rho: densite, scalaire ou tableau, en pers/m^2. Positive ou nulle et finie.

    Raises:
        ValueError: si une densite est negative, NaN ou infinie.
    """
    rho = _verifier_densite(rho)
    return rho * vitesse(rho)
