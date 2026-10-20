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
porte la tolerance.

Ce qui est GARANTI
------------------

1. *Admissibilite a la tolerance pres, ou echec declare.* En sortie, le
   recouvrement residuel est inferieur a `tolerance`, sinon l'appel est compte
   dans `non_convergences` — et leve `ProjectionNonConvergee` si `strict=True`.
   Jamais suppose : mesure et publie (`recouvrement_max`, `iterations_max`).
2. *Parois exactes.* Le domaine etant reprojete en dernier, les contraintes de
   paroi sont respectees a la precision machine, meme quand la projection echoue.
3. *Un contact qui se resout en moins de 80 balayages n'est jamais extrapole.*
   L'acceleration ne s'allume qu'au rang `_RANG_EXTRAPOLATION`, et la correction
   vaut exactement le recouvrement : un choc entre quelques agents suit donc la
   loi de choc mou, sans rebond artificiel (section « extrapolation » plus bas).
4. *Conservation du centre de gravite par l'etape de contact.* Chaque paire
   recoit deux corrections opposees de meme norme (ponderation symetrique,
   cf. `_corriger_contacts`), donc leur somme est nulle a chaque balayage. Le
   centre de gravite ne bouge que sous l'effet du domaine — ce qui est
   physiquement correct, une paroi exerce une force.

Ce qui est seulement MESURE, et pas demontre
--------------------------------------------

Le resultat n'est PAS la projection euclidienne de x_libre sur K, c'est-a-dire
l'argmin de |x - x_libre|. Des corrections decouplees, repetees jusqu'a
l'admissibilite, cherchent une configuration *admissible*, pas la *plus proche* :
rien ne minimise le deplacement, et aucune etape ne peut rapprocher deux disques
qu'un balayage a trop ecartes, puisque les corrections ne font qu'ecarter.

On le mesure plutot que de l'affirmer, en comparant a Gauss-Seidel (implemente
comme oracle de test dans `TestComparaisonGaussSeidel`) :

    configuration        |dX| Jacobi   |dX| Gauss-Seidel   ecart des solutions
    3 disques alignes     1,4141e-2        1,4141e-2             4,5e-7 m
    triangle serre        0,9999e-2        1,1770e-2             2,0e-3 m
    amas de 12            7,5924e-2        7,5044e-2             6,1e-3 m
    amas de 100           1,2109e-1        1,1924e-1             1,4e-2 m

Aucun des deux ne domine l'autre — sur le triangle serre c'est Jacobi qui deplace
le moins — donc aucun des deux n'est le minimiseur. Ce sont deux points
admissibles voisins de x_libre, qui peuvent s'eloigner jusqu'a 1,4e-2 m sur une
configuration dense. Le rapport doit donc ecrire « configuration admissible
obtenue par projections successives », et non « projection de Gauss-Seidel » ni
« projection euclidienne sur K ».

Choix de methode : Jacobi plutot que Gauss-Seidel
-------------------------------------------------

Chaque balayage traite toutes les paires EN MEME TEMPS (Jacobi) plutot que l'une
apres l'autre (Gauss-Seidel). Les deux sont des iterations de point fixe vers le
meme ensemble, et Gauss-Seidel demande nettement MOINS de balayages (13 a 19
contre 35 a 125 sur 12 a 600 agents) parce qu'il propage l'information d'un
contact a l'autre a l'interieur d'un balayage.

Le critere n'est pourtant pas le nombre de balayages mais le temps : un balayage
de Jacobi est une poignee d'operations NumPy, un balayage de Gauss-Seidel est une
boucle Python paire par paire. Mesure sur une boite occupee a 20 % :

    N agents      Jacobi    Gauss-Seidel    rapport
        12        1,46 ms      2,66 ms        1,8x
       100        1,51 ms      3,69 ms        2,4x
       600        7,87 ms     16,08 ms        2,0x

Jacobi est donc environ deux fois plus rapide malgre bien plus de balayages.
C'est la seule raison du choix : ce n'est pas une methode « meilleure », c'est la
seule des deux qui se vectorise. Un portage de Gauss-Seidel en code compile
inverserait la conclusion — et serait a reconsiderer si la taille des foules
simulees devenait le facteur limitant.

Deux precisions importantes :

  - Jacobi propage l'information d'UN contact par balayage. Une pile de disques
    posee sur le sol, ou la contrainte « le sol retient tout » doit remonter de
    proche en proche, converge alors tres lentement (plus de 3000 balayages
    mesures sur un tas de 64 disques). On accelere par extrapolation de Nesterov
    (FISTA). Sans elle, 716 projections sur 1500 echouent sur le tas de 36
    disques : l'acceleration n'est pas un confort, elle conditionne l'usage de la
    methode.
  - Chaque correction vaut EXACTEMENT le recouvrement, jamais plus. Sur-relaxer
    (corriger de 1,3 fois le recouvrement) irait plus vite mais separerait les
    disques au-dela du contact : la vitesse relue v = dx/dt contiendrait un
    rebond artificiel, et le choc cesserait d'etre mou.

L'extrapolation cree un rebond : comment il est contenu
-------------------------------------------------------

L'extrapolation `y = x + beta (x - x_precedent)` ecarte elle aussi les disques
au-dela du contact : chaque correction individuelle est exacte, mais la somme des
corrections ANTICIPEES ne l'est pas, et ce jeu est definitif puisqu'aucun
balayage ne rapproche. Il n'est pas borne par la tolerance, qui ne majore que le
recouvrement. Relu comme v = dx/dt, il devient un rebond : le choc mou cesse de
l'etre.

Ce n'est pas une crainte theorique. Avec l'extrapolation active des le premier
balayage, un choc de trois disques alignes laissait 1,27e-2 m de jeu et une
vitesse residuelle de 1,06e-2 m/s, soit 1 % de la vitesse d'arrivee. Le test du
choc a DEUX disques ne pouvait pas le voir : une paire isolee est corrigee
exactement en un balayage, l'artefact n'apparait qu'a partir de TROIS corps.

Deux correctifs, tous deux mesures :

  1. *L'extrapolation ne s'allume qu'au rang `_RANG_EXTRAPOLATION` = 80.* Un choc
     entre quelques agents se resout en moins de balayages, il reste donc exact ;
     seules les longues chaines de contacts, ou l'acceleration est indispensable,
     la recoivent.
  2. *Sa rampe repart de zero au declenchement* (`k = rang - _RANG_EXTRAPOLATION`).
     Sans cela, beta sautait directement a 80/83 = 0,96 : le premier balayage
     extrapole depassait largement le contact, et le retard AGGRAVAIT le defaut
     sur les chaines longues au lieu de le corriger (7,7e-4 contre 2,4e-5 a
     rang 0 sur une chaine de 12).

Energie cinetique residuelle apres un choc, rapportee a l'energie d'arrivee, pire
cas sur des chaines convergentes de 3 a 32 disques a quantite de mouvement nulle,
plus un triangle a trois contacts mutuels :

    rang 0 (extrapolation immediate)    1,0e-3      3 % de la vitesse restituee
    rang 20                             4,3e-5
    rang 40                             2,9e-5
    rang 80 (retenu)                    9,0e-7      0,09 % en vitesse

Cout du retard, sur le tas de 64 disques : 168 balayages au lieu de 91 et 11,7 s
au lieu de 5,3 s, pour 0 projection en echec sur 1500 dans les deux cas. Au-dela
de 80 le gain plafonne tandis que le budget d'iterations se consomme.

Ce qu'il RESTE comme artefact, mesure et assume :

  - Les chaines longues, seules extrapolees, gardent une restitution de l'ordre
    de 1e-6 de l'energie d'arrivee.
  - Trois contacts MUTUELS corriges dans le meme balayage laissent un defaut de
    POSITION, independant de l'extrapolation : le triangle finit tangent a
    1,7e-3 m pres, sans mouvement residuel. Il sature et ne decroit pas avec dt.
  - Sur le tas, les paires en contact sont tangentes a 5,0e-6 m au plus a
    dt = 2e-3 s, contre 2,5e-5 m a dt = 4e-3 s : ce defaut-la decroit bien
    comme dt^2.

`TestChocMultiple` controle ces bornes sur des contacts isoles, ou aucune
dissipation d'ensemble ne peut les masquer.
"""

from __future__ import annotations

from collections.abc import Callable

import numpy as np

from viscocrowd.core.verifications import exiger_fini
from viscocrowd.geometry.grille import paires_candidates, recouvrement_max

# Ramene des positions (N, 2) dans le domaine, au temps donne (cf. BoiteTournante.projeter).
ProjectionDomaine = Callable[[np.ndarray, np.ndarray, float], np.ndarray]

# Deux centres confondus n'ont pas de ligne des centres : on prend une direction fixe.
_DISTANCE_MIN = 1e-12

# Rang a partir duquel l'extrapolation de Nesterov s'allume. En deca, balayages
# simples, donc exacts : un choc entre quelques agents n'est jamais extrapole.
# Au-dela, seules les longues chaines de contacts sont accelerees, et la rampe
# repart de zero. Valeur justifiee par mesure, cf. la section « extrapolation ».
_RANG_EXTRAPOLATION = 80


class ProjectionNonConvergee(RuntimeError):  # noqa: N818 - nommage francais du projet
    """La projection a epuise son budget de balayages sans atteindre la tolerance.

    Une configuration encore en recouvrement n'est pas un etat physique : la
    laisser passer silencieusement reviendrait a publier des agents qui
    s'interpenetrent comme un resultat valide.

    Attributes:
        residu: recouvrement residuel atteint, en m.
        tolerance: recouvrement qui etait demande, en m.
        iterations: nombre de balayages consommes.
    """

    def __init__(self, residu: float, tolerance: float, iterations: int) -> None:
        super().__init__(
            f"projection non convergee : recouvrement residuel {residu:.3e} m "
            f"> tolerance {tolerance:.3e} m apres {iterations} balayages"
        )
        self.residu = residu
        self.tolerance = tolerance
        self.iterations = iterations


def _corriger_contacts(x: np.ndarray, r: np.ndarray, paires: np.ndarray) -> None:
    """Un balayage de correction des recouvrements, sur place. Voir le module.

    Un agent touche par plusieurs voisins recevrait la somme de corrections
    concurrentes et reculerait trop : il faut les ponderer. On divise chaque
    correction de PAIRE par max(c_i, c_j), ou c_k est le nombre de contacts de
    l'agent k, plutot que de moyenner les corrections recues par AGENT.

    Les deux amortissent autant, mais seule la ponderation par paire est
    symetrique en (i, j) : les deux disques recoivent des corrections opposees de
    meme norme, donc le centre de gravite est conserve exactement. Moyenner par
    agent le brise des que deux voisins n'ont pas le meme nombre de contacts, et
    la foule entiere derive — 2,2e-3 m mesures sur un amas de 12 disques,
    1,6e-4 m sur 100 disques, contre 1e-17 m ici. Cout : environ 30 % de
    balayages en plus.
    """
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
    contacts = np.bincount(i, minlength=n) + np.bincount(j, minlength=n)
    poids = 1.0 / np.maximum(np.maximum(contacts[i], contacts[j]), 1)
    correction = correction * poids[:, None]

    deplacement = np.zeros_like(x)
    for axe in range(2):
        deplacement[:, axe] -= np.bincount(i, weights=correction[:, axe], minlength=n)
        deplacement[:, axe] += np.bincount(j, weights=correction[:, axe], minlength=n)

    x += deplacement


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
        iterations: int = 300,
        strict: bool = False,
    ) -> None:
        """
        Args:
            domaine: projection sur le domaine (parois). None : domaine non borne.
            tolerance: recouvrement residuel accepte, en metres.
            iterations: budget maximal de balayages par appel. Le defaut laisse
                une marge d'environ 80 % sur les 168 balayages que demande le
                tas de 64 disques, cas le plus exigeant mesure.
            strict: lever `ProjectionNonConvergee` des qu'un appel n'atteint pas
                la tolerance, au lieu de le compter et de rendre la configuration.
                A reserver aux simulations dont on exploite les resultats ; les
                etudes de limites ont besoin du mode permissif pour MESURER
                l'echec. Sans ce mode, appeler `verifier_convergence()` apres la
                simulation.
        """
        if tolerance <= 0.0:
            raise ValueError(f"la tolerance doit etre strictement positive, recu {tolerance}")
        if iterations < 1:
            raise ValueError(f"il faut au moins une iteration, recu {iterations}")
        self.domaine = domaine
        self.tolerance = tolerance
        self.iterations = iterations
        self.strict = strict
        self.recouvrement_max = 0.0
        self.iterations_max = 0
        self.n_appels = 0
        self.non_convergences = 0

    def __call__(self, x: np.ndarray, r: np.ndarray, t: float) -> np.ndarray:
        x = np.array(x, dtype=float, copy=True)
        # Une entree non finie est une ERREUR, pas une non-convergence : elle leve dans
        # les deux modes. Le mode permissif sert a mesurer un echec de convergence, pas
        # a laisser passer un etat corrompu. Sans ce controle, un NaN rendait toutes les
        # distances incomparables : aucune paire, residu nul, projection « convergee ».
        exiger_fini(
            "La configuration est corrompue en amont : vitesse libre, guidage, pas de temps.",
            x=x,
            r=r,
        )
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
            if self.strict:
                raise ProjectionNonConvergee(residu, self.tolerance, n_iterations)
        return x

    def verifier_convergence(self) -> None:
        """Leve `ProjectionNonConvergee` si un appel n'a pas atteint la tolerance.

        A appeler apres une simulation dont on va exploiter les resultats, quand
        on n'a pas voulu interrompre le calcul au premier echec. Une trajectoire
        qui contient des agents interpenetres au-dela de la tolerance ne doit pas
        pouvoir alimenter une figure ou un tableau du rapport.
        """
        if self.non_convergences:
            raise ProjectionNonConvergee(self.recouvrement_max, self.tolerance, self.iterations_max)

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
                # prolonge dans la direction du dernier mouvement. Elle n'est allumee
                # qu'au-dela de _RANG_EXTRAPOLATION balayages, car elle ecarte les
                # disques au-dela du contact : un choc isole doit rester exact, seules
                # les longues chaines de contacts ont besoin d'etre accelerees.
                # La rampe de Nesterov repart de zero au declenchement : un saut
                # direct a beta = 80/83 = 0,96 depasserait largement le contact.
                k = rang - _RANG_EXTRAPOLATION
                beta = k / (k + 3.0) if k > 0 else 0.0
                y = x + beta * (x - x_precedent)
                if self.domaine is not None and beta > 0.0:
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
