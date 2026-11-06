"""Controles d'entree partages par le moteur.

Une valeur non finie (NaN ou infini) n'est jamais un resultat : c'est une
corruption, et elle doit s'arreter la ou elle est detectee. Le piege est qu'elle
ne se signale pas d'elle-meme, parce que TOUTE comparaison avec un NaN est
fausse : un test `valeur <= seuil` la declare conforme, un test `valeur > seuil`
la declare conforme aussi, et une recherche de paires en recouvrement n'en
trouve aucune. Une configuration corrompue affiche donc exactement les chiffres
publies comme preuve de justesse.

D'ou ce module, et le choix d'y centraliser le controle : les trois points
d'entree du moteur doivent refuser de la meme facon, avec le meme message, et
surtout en nommant l'agent fautif.
"""

from __future__ import annotations

import numpy as np

# Au-dela, la liste d'indices devient illisible et on ne donne plus que le compte.
_INDICES_MONTRES = 5

# Tolerance sur la norme d'un vecteur dit unitaire (guidage, direction de mesure). Plus
# large, une norme de 1 + 1e-5 multiplierait une vitesse sans que rien ne le signale.
TOLERANCE_UNITAIRE = 1e-9


def exiger_fini(contexte: str = "", **tableaux: np.ndarray) -> None:
    """Leve `ValueError` si l'un des tableaux contient un NaN ou un infini.

    Le message nomme le tableau fautif ET les agents concernes. Sur une campagne
    a plusieurs centaines d'agents, « x est non fini » n'apprend rien : savoir
    que c'est l'agent 437 est la seule information qui fasse gagner du temps.

    Args:
        contexte: phrase ajoutee au message, pour orienter vers la cause amont.
        **tableaux: les tableaux a controler, nommes comme dans le code appelant
            (`x=...`, `r=...`) pour que le message reprenne ce nom.

    Raises:
        ValueError: des qu'un tableau contient une valeur non finie.
    """
    for nom, tableau in tableaux.items():
        tableau = np.asarray(tableau)
        fini = np.isfinite(tableau)
        if bool(np.all(fini)):
            continue

        # Un tableau (N, 2) est fautif par AGENT : on reduit sur les colonnes pour
        # rendre des indices d'agents, et non des indices aplatis.
        axes = tuple(range(1, tableau.ndim))
        agents = np.flatnonzero(~np.all(fini, axis=axes) if axes else ~fini)
        montres = ", ".join(str(int(i)) for i in agents[:_INDICES_MONTRES])
        if agents.size > _INDICES_MONTRES:
            montres += f" et {agents.size - _INDICES_MONTRES} autres"

        total = tableau.shape[0] if tableau.ndim else 1
        message = (
            f"{nom} contient des valeurs non finies (NaN ou infini) : "
            f"agent(s) {montres} sur {total}"
        )
        raise ValueError(f"{message}. {contexte}" if contexte else message)


def exiger_scalaire_fini(nom: str, valeur: float, *, strictement_positif: bool = False) -> None:
    """Leve `ValueError` si `valeur` n'est pas un nombre fini.

    A utiliser pour les parametres scalaires du schema (pas de temps, duree,
    instant). Le test est ecrit en forme POSITIVE — `np.isfinite(...) and
    valeur > 0` — et non comme la negation d'une comparaison : `not valeur <= 0`
    laisse passer un NaN, puisque `NaN <= 0` est faux. C'est exactement le piege
    qui laissait passer un rayon NaN avant la correction de l'issue #16.

    Args:
        nom: nom du parametre, repris dans le message.
        valeur: la valeur a controler.
        strictement_positif: exiger en plus qu'elle soit > 0.

    Raises:
        ValueError: si la valeur n'est pas finie, ou pas strictement positive
            quand c'est demande.
    """
    if not np.isfinite(valeur):
        raise ValueError(f"{nom} doit etre un nombre fini, recu {valeur}")
    if strictement_positif and not valeur > 0.0:
        raise ValueError(f"{nom} doit etre strictement positif, recu {valeur}")
