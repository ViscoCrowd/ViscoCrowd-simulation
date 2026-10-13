"""Scenario de validation : des disques qui tombent et s'empilent dans une boite.

Deuxieme banc d'essai du moteur, apres la bille seule. Il ne fait pas non plus
partie de la problematique ViscoCrowd : il verifie que la projection sur
l'exclusion entre agents, branchee dans le meme schema semi-implicite, tient ses
promesses AVANT qu'on lui ajoute le guidage, les milieux ou les franchissements.

N disques, de memes rayons, sont poses sans recouvrement sur un reseau regulier
dans la moitie haute d'une boite fixe, puis tombent sous la gravite et se
tassent au fond. On mesure ce que la spec impose de publier : le recouvrement
residuel entre disques, et le respect des parois.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from viscocrowd.core.integrator import chute_libre, trajectoire
from viscocrowd.core.rng import generateur
from viscocrowd.core.state import GRAVITE, State
from viscocrowd.geometry.boite import BoiteTournante
from viscocrowd.geometry.grille import recouvrement_max
from viscocrowd.geometry.projection import ProjectionExclusion


@dataclass(frozen=True)
class ParametresTassement:
    """Parametres du scenario, en unites SI.

    Les disques occupent 25 % de la boite : loin de l'empilement maximal, pour
    que la projection converge vite et que le test porte sur la methode, pas
    sur la difficulte du probleme.
    """

    n_agents: int = 64
    demi_largeur: float = 1.0  # R, m
    rayon: float = 0.07  # r, m
    dt: float = 2e-3  # s  : |v| dt ~ 1 cm par pas, soit un septieme du rayon
    duree: float = 3.0  # s
    tolerance: float = 1e-6  # recouvrement residuel accepte, m
    graine: int | None = None
    gravite: np.ndarray = field(default_factory=lambda: GRAVITE.copy())  # m/s^2


@dataclass(frozen=True)
class ResultatTassement:
    """Trajectoire simulee et grandeurs de validation."""

    t: np.ndarray  # (P,)       s
    x: np.ndarray  # (P, N, 2)  m
    v: np.ndarray  # (P, N, 2)  m/s
    rayons: np.ndarray  # (N,)  m
    boite: BoiteTournante
    projection: ProjectionExclusion
    parametres: ParametresTassement

    def recouvrement_max(self) -> float:
        """Plus grand recouvrement entre deux disques sur toute la simulation, en m."""
        return max(recouvrement_max(self.x[p], self.rayons) for p in range(self.t.size))

    def violation_paroi_max(self) -> float:
        """Plus grand depassement des parois sur toute la simulation, en m.

        Un resultat negatif signifie une marge (aucun disque ne touche la paroi).
        """
        return max(
            self.boite.violation(self.x[p], self.rayons, float(self.t[p]))
            for p in range(self.t.size)
        )

    def energie_cinetique(self, masse: float = 1.0) -> np.ndarray:
        """Energie cinetique totale a chaque instant, en J."""
        return 0.5 * masse * np.sum(self.v**2, axis=(1, 2))


def positions_initiales(p: ParametresTassement) -> np.ndarray:
    """Reseau carre sans recouvrement dans la moitie haute de la boite, legerement bruite.

    Le bruit reste inferieur a l'espace libre entre deux disques voisins : la
    configuration de depart est admissible, donc tout recouvrement observe
    ensuite vient du schema et non des conditions initiales.
    """
    marge = p.demi_largeur - p.rayon
    pas = 2.0 * p.rayon * 1.2  # 20 % d'espace libre entre disques voisins
    par_ligne = int(2.0 * marge // pas) + 1
    lignes = int(marge // pas) + 1  # de y = marge jusqu'au milieu de la boite
    if p.n_agents > par_ligne * lignes:
        raise ValueError("trop d'agents pour la moitie haute de la boite")

    colonnes = np.arange(par_ligne) * pas - 0.5 * (par_ligne - 1) * pas
    amplitude = 0.05 * p.rayon
    # La rangee du haut est decalee de l'amplitude du bruit : l'etat initial doit
    # lui aussi respecter les parois, sinon on mesurerait une violation qui n'est
    # pas celle de la projection.
    haut = marge - amplitude
    x = np.array(
        [(colonnes[k % par_ligne], haut - (k // par_ligne) * pas) for k in range(p.n_agents)]
    )
    bruit = generateur(p.graine).uniform(-amplitude, amplitude, size=x.shape)
    return x + bruit


def simuler_tassement(parametres: ParametresTassement | None = None) -> ResultatTassement:
    """Simule le scenario et rend la trajectoire complete."""
    p = parametres or ParametresTassement()

    boite = BoiteTournante(demi_largeur=p.demi_largeur)  # omega = 0 : boite fixe
    rayons = np.full(p.n_agents, p.rayon)
    etat_initial = State(
        x=positions_initiales(p),
        v=np.zeros((p.n_agents, 2)),
        r=rayons,
    )
    projection = ProjectionExclusion(boite.projeter, tolerance=p.tolerance)

    t, x, v = trajectoire(
        etat_initial,
        dt=p.dt,
        duree=p.duree,
        vitesse_libre=chute_libre(p.gravite),
        projection=projection,
    )

    return ResultatTassement(
        t=t, x=x, v=v, rayons=rayons, boite=boite, projection=projection, parametres=p
    )
