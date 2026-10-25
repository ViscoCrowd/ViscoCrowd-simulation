"""Vue des archives piscine : geometrie, etats et occupations, sans integration."""

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import ListedColormap
from matplotlib.lines import Line2D
from matplotlib.patches import Circle, Rectangle

from viscocrowd.io.trajectoires import Trajectoire
from viscocrowd.model.carte import CartePiscine
from viscocrowd.scenarios.piscine import (
    EAU,
    FRANCHISSEMENT,
    NOMS_ETATS,
    PLAGE,
    SORTI,
    ParametresPiscine,
)
from viscocrowd.ui.relecture import LecteurTrajectoire

COULEURS = ("#61c6ed", "#ffb454", "#f4f8fb", "#91a2b4")


def occupations_sites(
    x: np.ndarray, etats: np.ndarray, positions_sites: np.ndarray, t: np.ndarray
) -> np.ndarray:
    """Sites occupes (P, S) a chaque instant, deduits des agents en franchissement.

    Le scenario pose un agent en franchissement exactement sur son site : chacun doit
    donc s'y trouver a 1e-9 m pres, et un site ne porte qu'un agent a la fois.

    Raises:
        ValueError: au premier instant ou un agent est hors site ou partage son site.
    """
    instants, agents = np.nonzero(etats == FRANCHISSEMENT)
    occupations = np.zeros((len(t), len(positions_sites)), dtype=bool)
    if instants.size == 0:
        return occupations
    # Deux tableaux (K, S) plutot qu'un (K, S, 2) : moitie moins de memoire sur une
    # longue archive.
    px, py = x[instants, agents].T
    distances = np.hypot(px[:, None] - positions_sites[:, 0], py[:, None] - positions_sites[:, 1])
    sites = np.argmin(distances, axis=1)
    hors_site = np.min(distances, axis=1) > 1e-9
    _, premier, nombre = np.unique(
        instants * len(positions_sites) + sites, return_index=True, return_counts=True
    )
    partage = np.zeros(instants.size, dtype=bool)
    partage[premier[nombre > 1]] = True
    fautifs = np.flatnonzero(hors_site | partage)
    if fautifs.size:
        raise ValueError(
            "occupation des sites incoherente avec les positions archivees "
            f"a t = {t[instants[fautifs].min()]:.2f} s"
        )
    occupations[instants, sites] = True
    return occupations


class LecteurPiscine(LecteurTrajectoire):
    """L'etat archive fait foi ; aucun etat n'est invente entre deux echantillons."""

    def __init__(self, donnees: Trajectoire, *, interactif: bool = True, vitesse: float = 1.0):
        if not np.isfinite(vitesse) or vitesse <= 0:
            raise ValueError("vitesse doit etre finie et strictement positive")
        config = donnees.metadonnees.get("configuration", {})
        try:
            if config["scenario"] != "piscine":
                raise ValueError("cette relecture attend une archive piscine")
            self.p = ParametresPiscine(**config["parametres"], graine=config["graine"])
        except (KeyError, TypeError) as erreur:
            raise ValueError("configuration piscine absente ou incomplete") from erreur
        etats = donnees.etats
        if (
            etats is None
            or donnees.metadonnees.get("etats") != list(NOMS_ETATS)
            or np.any(etats > SORTI)
            or np.any(np.diff(etats, axis=0) < 0)
        ):
            raise ValueError("etats piscine absents, inconnus ou non monotones")
        if donnees.x.shape[1] != self.p.n_agents or not np.all(donnees.rayons == self.p.rayon):
            raise ValueError("population archivee incoherente avec sa configuration")
        try:
            sorties = donnees.metadonnees["evenements"]["sorties"]
            if len(sorties) != self.p.n_agents or any(
                s is not None and (type(s) not in (int, float) or not np.isfinite(s))
                for s in sorties
            ):
                raise ValueError("instants de sortie invalides")
            instants = np.array([np.inf if s is None else s for s in sorties])
            if (
                np.any(instants < donnees.t[0])
                or np.any(np.isfinite(instants) & (instants > donnees.t[-1]))
                or not np.array_equal(etats == SORTI, donnees.t[:, None] >= instants)
            ):
                raise ValueError("sorties incoherentes avec les etats archives")
        except (KeyError, TypeError) as erreur:
            raise ValueError("evenements de sortie absents ou incomplets") from erreur
        self.donnees, self.vitesse = donnees, vitesse
        self.index, self.en_lecture = 0, False
        self.slider = self.bouton = None
        g = self.p.piscine
        self.sites = g.sites()
        self.positions_sites = np.array([s.position for s in self.sites])
        # Controle une seule fois, avant la figure : une incoherence tardive ne doit pas
        # surgir en pleine lecture, ni interrompre un GIF deja commence.
        self.occupations = occupations_sites(donnees.x, etats, self.positions_sites, donnees.t)
        self.figure = plt.figure(figsize=(12, 7), dpi=100, facecolor="#101923")
        self.figure.text(0.07, 0.93, "ViscoCrowd", color="white", fontsize=25, weight="bold")
        self.figure.text(0.07, 0.875, "ÉVACUATION PISCINE  /  RELECTURE", color="#7dd3d8")
        self.temps = self.figure.text(0.93, 0.94, "", ha="right", color="white", fontsize=17)
        self.compteur = self.figure.text(0.93, 0.88, "", ha="right", color="#7dd3d8")
        self.effectifs = self.figure.text(0.07, 0.80, "", color="#b7c5d0", fontsize=10)
        self.ax = self.figure.add_axes((0.07, 0.29, 0.86, 0.46), facecolor="#172431")
        self.ax.set_aspect("equal", adjustable="box")
        self.ax.set(
            xlim=(-0.5, g.longueur_emprise + 1.5),
            ylim=(-0.5, g.largeur_emprise + 0.5),
            xlabel="x (m)",
            ylabel="y (m)",
        )
        self.ax.tick_params(colors="#b7c5d0", labelsize=9)
        self.ax.xaxis.label.set_color("#b7c5d0")
        self.ax.yaxis.label.set_color("#b7c5d0")
        for spine in self.ax.spines.values():
            spine.set_visible(False)
        # Le fond utilise la vraie carte, y compris les coins arrondis du mouille.
        xs = np.linspace(0, g.longueur_emprise, 500)
        ys = np.linspace(0, g.largeur_emprise, 250)
        xx, yy = np.meshgrid(xs, ys)
        carte = CartePiscine(g)(np.column_stack((xx.ravel(), yy.ravel()))).reshape(xx.shape)
        self.ax.imshow(
            carte,
            origin="lower",
            extent=(0, xs[-1], 0, ys[-1]),
            cmap=ListedColormap(["#274b80", "#215766", "#263847"]),
            vmin=0,
            vmax=2,
            interpolation="nearest",
            zorder=0,
        )
        b = g.bassin
        self.ax.add_patch(
            Rectangle(
                (b.x_min, b.y_min),
                b.x_max - b.x_min,
                b.y_max - b.y_min,
                fill=False,
                edgecolor="#cbd5df",
                lw=1.3,
            )
        )
        bas, haut = g.porte
        for xs_mur, ys_mur in [
            ([0, 0, g.longueur_emprise], [0, g.largeur_emprise, g.largeur_emprise]),
            ([0, g.longueur_emprise], [0, 0]),
            ([bas[0], bas[0]], [0, bas[1]]),
            ([haut[0], haut[0]], [haut[1], g.largeur_emprise]),
        ]:
            self.ax.plot(xs_mur, ys_mur, color="#cbd5df", lw=1.3)
        self.ax.plot(*np.array(g.porte).T, color="#7dd3d8", lw=3)
        self.ax.text(bas[0] + 0.4, bas[1], "Sortie", color="#7dd3d8", fontsize=9, rotation=90)
        self.marqueurs_sites = []
        for site in self.sites:
            (marqueur,) = self.ax.plot(
                *site.position,
                marker="s" if site.nature == "echelle" else ".",
                color="#8193a6",
                markersize=5 if site.nature == "echelle" else 3,
            )
            self.marqueurs_sites.append(marqueur)
        self.disques = [
            Circle(x, r, edgecolor="#101923", lw=0.5, zorder=4)
            for x, r in zip(donnees.x[0], donnees.rayons, strict=True)
        ]
        for disque in self.disques:
            self.ax.add_patch(disque)
        self.figure.legend(
            handles=[
                Line2D([], [], marker="o", linestyle="", color=c, label=n)
                for c, n in zip(
                    COULEURS[:3], ["Dans l'eau", "Franchissement", "Sur la plage"], strict=True
                )
            ]
            + [Line2D([], [], marker="s", linestyle="", color="#8193a6", label="Échelle libre")],
            loc="lower left",
            bbox_to_anchor=(0.06, 0.18),
            ncol=4,
            frameon=False,
            labelcolor="#b7c5d0",
            fontsize=9,
        )
        self.figure.text(
            0.07,
            0.15,
            f"{self.p.n_agents} agents · graine {self.p.graine} · paramètres physiques à valider",
            color="#b7c5d0",
            fontsize=9,
        )
        self._installer_commandes(interactif)
        self.afficher(0)

    def afficher(self, index: int) -> None:
        self.index = int(np.clip(index, 0, len(self.donnees.t) - 1))
        x, etats = self.donnees.x[self.index], self.donnees.etats[self.index]
        self.occupes = self.occupations[self.index]
        for disque, position, etat in zip(self.disques, x, etats, strict=True):
            disque.set_center(position)
            disque.set_facecolor(COULEURS[etat])
            disque.set_visible(etat != SORTI)
        for marqueur, occupe in zip(self.marqueurs_sites, self.occupes, strict=True):
            marqueur.set_color(COULEURS[FRANCHISSEMENT] if occupe else "#8193a6")
        effectifs = np.bincount(etats, minlength=4)
        self.temps.set_text(
            f"{self.donnees.t[self.index]:05.2f} s  /  {self.donnees.t[-1]:05.2f} s"
        )
        self.compteur.set_text(f"Évacués : {effectifs[SORTI]} / {self.p.n_agents}")
        self.effectifs.set_text(
            f"Eau : {effectifs[EAU]}    Franchissement : {effectifs[FRANCHISSEMENT]}"
            f"    Plage : {effectifs[PLAGE]}    Sites occupés : {self.occupes.sum()}"
        )
        if self.slider is not None:
            self.slider.eventson = False
            self.slider.set_val(self.donnees.t[self.index])
            self.slider.eventson = True
        self.figure.canvas.draw_idle()
