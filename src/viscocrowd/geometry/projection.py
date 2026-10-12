"""Projection iterative sur l'ensemble des configurations sans recouvrement.

Le pas libre deplace chaque disque sans se soucier des autres. La projection
ramene ensuite la configuration dans

    K = { X : |x_i - x_j| >= r_i + r_j pour i != j, et x_i dans le domaine }.

K n'est PAS convexe : le non-recouvrement est l'exterieur d'une boule. On suit
Maury & Venel et on LINEARISE chaque contrainte autour de la configuration
courante, ce qui donne un ensemble de demi-espaces, donc convexe. Pour une paire
en recouvrement, la contrainte linearisee dit : « s'ecarter le long de la ligne
des centres d'au moins le recouvrement ». Les deux disques ont la meme masse
apparente, chacun recule donc de la moitie.

Une paire corrigee peut en recreer une autre (un disque pousse contre son
voisin), et le domaine peut ramener un disque contre un autre. On alterne donc
« corriger les contacts » et « reprojeter sur le domaine » jusqu'a ce que le
recouvrement residuel passe sous une tolerance, ou que le budget d'iterations
soit epuise. Le domaine est TOUJOURS reprojete en dernier : les parois sont
respectees a la precision machine, et c'est le recouvrement entre agents qui
porte la tolerance. Cette tolerance est une grandeur mesuree et publiee, jamais
supposee (`recouvrement_max`, `iterations_max`, `non_convergences`).

Choix de methode : chaque balayage traite toutes les paires EN MEME TEMPS
(Jacobi) plutot que l'une apres l'autre (Gauss-Seidel). Les deux sont des
iterations de point fixe vers le meme ensemble ; Jacobi se vectorise en NumPy,
ce qui est decisif pour des centaines d'agents sur des milliers de pas. Un agent
touche par c voisins recoit la MOYENNE des c corrections : sans cela deux
corrections concurrentes s'additionneraient et les disques reculeraient trop.

Deux precisions importantes :

  - Jacobi propage l'information d'UN contact par balayage. Une pile de disques
    posee sur le sol, ou la contrainte « le sol retient tout » doit remonter de
    proche en proche, converge alors tres lentement (plus de 3000 balayages
    mesures sur un tas de 64 disques). On accelere par extrapolation de Nesterov
    (FISTA) : environ 100 balayages pour le meme tas.
  - Chaque correction vaut EXACTEMENT le recouvrement, jamais plus. Sur-relaxer
    (corriger de 1,3 fois le recouvrement) irait plus vite mais separerait les
    disques au-dela du contact : la vitesse relue v = dx/dt contiendrait un
    rebond artificiel, et le choc cesserait d'etre mou.
"""

from __future__ import annotations

from collections.abc import Callable

import numpy as np

from viscocrowd.geometry.grille import paires_candidates, recouvrement_max

# Ramene des positions (N, 2) dans le domaine, au temps donne (cf. BoiteTournante.projeter).
ProjectionDomaine = Callable[[np.ndarray, np.ndarray, float], np.ndarray]

# Deux centres confondus n'ont pas de ligne des centres : on prend une direction fixe.
_DISTANCE_MIN = 1e-12


def _corriger_contacts(x: np.ndarray, r: np.ndarray, paires: np.ndarray) -> None:
    """Un balayage de correction des recouvrements, sur place. Voir le module."""
    if paires.shape[0] == 0:
        return
    i, j = paires[:, 0], paires[:, 1]

    ecart = x[j] - x[i]  # de i vers j
    distance = np.linalg.norm(ecart, axis=1)
    recouvrement = r[i] + r[j] - distance

    actif = recouvrement > 0.0
    if not np.any(actif):
        return
    i, j, ecart = i[actif], j[actif], ecart[actif]
    distance, recouvrement = distance[actif], recouvrement[actif]

    confondus = distance < _DISTANCE_MIN
    direction = np.where(
        confondus[:, None],
        np.array([1.0, 0.0]),
        ecart / np.where(confondus, 1.0, distance)[:, None],
    )
    correction = 0.5 * recouvrement[:, None] * direction  # part de chaque disque

    n = x.shape[0]
    deplacement = np.zeros_like(x)
    for axe in range(2):
        deplacement[:, axe] -= np.bincount(i, weights=correction[:, axe], minlength=n)
        deplacement[:, axe] += np.bincount(j, weights=correction[:, axe], minlength=n)
    contacts = np.bincount(i, minlength=n) + np.bincount(j, minlength=n)

    x += deplacement / np.maximum(contacts, 1)[:, None]


class ProjectionExclusion:
    """Projection sur « pas de recouvrement » puis sur le domaine, avec ses mesures.

    Objet appelable de signature (x_libre, r, t) -> x : il se branche tel quel
    comme argument `projection` de `core.integrator.pas_semi_implicite`.

    Attributes mesures, cumulees sur tous les appels :
        recouvrement_max: plus grand recouvrement residuel observe en fin de projection, en m.
        iterations_max: plus grand nombre de balayages utilise par un appel.
        n_appels: nombre de projections effectuees.
        non_convergences: appels ayant epuise leur budget sans passer sous la tolerance.
    """

    def __init__(
        self,
        domaine: ProjectionDomaine | None = None,
        *,
        tolerance: float = 1e-6,
        iterations: int = 200,
    ) -> None:
        """
        Args:
            domaine: projection sur le domaine (parois). None : domaine non borne.
            tolerance: recouvrement residuel accepte, en metres.
            iterations: budget maximal de balayages par appel.
        """
        if tolerance <= 0.0:
            raise ValueError(f"la tolerance doit etre strictement positive, recu {tolerance}")
        if iterations < 1:
            raise ValueError(f"il faut au moins une iteration, recu {iterations}")
        self.domaine = domaine
        self.tolerance = tolerance
        self.iterations = iterations
        self.recouvrement_max = 0.0
        self.iterations_max = 0
        self.n_appels = 0
        self.non_convergences = 0

    def __call__(self, x: np.ndarray, r: np.ndarray, t: float) -> np.ndarray:
        x = np.array(x, dtype=float, copy=True)
        if x.shape[0] >= 2:
            x, n_iterations, residu = self._iterer(x, r, t)
        else:
            n_iterations, residu = 0, 0.0
            if self.domaine is not None:
                x = self.domaine(x, r, t)

        self.n_appels += 1
        self.iterations_max = max(self.iterations_max, n_iterations)
        self.recouvrement_max = max(self.recouvrement_max, residu)
        if residu > self.tolerance:
            self.non_convergences += 1
        return x

    def _iterer(self, x: np.ndarray, r: np.ndarray, t: float) -> tuple[np.ndarray, int, float]:
        # Les disques bougent pendant les balayages : on detecte donc les paires avec
        # une marge, puis on verifie a la fin avec une recherche exacte.
        marge = 0.5 * float(r.min())
        n_iterations = 0
        residu = recouvrement_max(x, r)

        while True:
            paires = paires_candidates(x, r, marge)
            x_precedent = x
            rang = 0  # rang du balayage depuis la derniere recherche de paires
            while n_iterations < self.iterations:
                if residu <= self.tolerance and n_iterations > 0:
                    break
                # Extrapolation (Nesterov / FISTA) : on corrige a partir d'un point
                # prolonge dans la direction du dernier mouvement. Au rang 0 il n'y a
                # pas de mouvement, donc pas d'extrapolation : une paire isolee est
                # corrigee exactement en un balayage, sans rebond artificiel.
                y = x + (rang / (rang + 3.0)) * (x - x_precedent)
                if self.domaine is not None and rang > 0:
                    y = self.domaine(y, r, t)
                _corriger_contacts(y, r, paires)
                if self.domaine is not None:
                    y = self.domaine(y, r, t)
                x_precedent, x = x, y
                n_iterations += 1
                rang += 1
                residu = self._recouvrement_sur(x, r, paires)
                if residu <= self.tolerance:
                    break

            # Verification sur la liste COMPLETE : une paire absente de `paires` a pu se creer.
            residu = recouvrement_max(x, r)
            if residu <= self.tolerance or n_iterations >= self.iterations:
                return x, n_iterations, residu

    @staticmethod
    def _recouvrement_sur(x: np.ndarray, r: np.ndarray, paires: np.ndarray) -> float:
        if paires.shape[0] == 0:
            return 0.0
        i, j = paires[:, 0], paires[:, 1]
        return float(max(0.0, np.max(r[i] + r[j] - np.linalg.norm(x[i] - x[j], axis=1))))
