"""Relecture hors ligne du banc de couloir : aucun appel a la simulation."""

import time

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.animation import FuncAnimation, PillowWriter
from matplotlib.patches import Circle, Rectangle
from matplotlib.widgets import Button, Slider

from viscocrowd.geometry.couloir import Couloir
from viscocrowd.io.trajectoires import Trajectoire
from viscocrowd.observables.debit import franchissements
from viscocrowd.scenarios.couloir import ParametresCouloir


def indices_animation(t: np.ndarray, fps: int, vitesse: float) -> np.ndarray:
    """Echantillonne en temps simule, meme si les instants archives sont irreguliers."""
    if fps < 1 or not np.isfinite(vitesse) or vitesse <= 0:
        raise ValueError("fps et vitesse doivent etre strictement positifs")
    cibles = np.append(np.arange(t[0], t[-1], vitesse / fps), t[-1])
    return np.clip(np.searchsorted(t, cibles, side="right") - 1, 0, len(t) - 1)


class LecteurCouloir:
    """Vue a echelle metrique, indexee exclusivement par les donnees archivees."""

    def __init__(self, donnees: Trajectoire, *, interactif: bool = True, vitesse: float = 1.0):
        if not np.isfinite(vitesse) or vitesse <= 0:
            raise ValueError("vitesse doit etre finie et strictement positive")
        config = donnees.metadonnees.get("configuration", {})
        if not isinstance(config, dict) or config.get("scenario") != "couloir":
            raise ValueError("cette relecture graphique attend une archive du scenario couloir")
        try:
            self.p = ParametresCouloir(**config["parametres"], graine=config["graine"])
        except (KeyError, TypeError) as erreur:
            raise ValueError(
                "configuration du couloir absente ou incomplete dans l'archive"
            ) from erreur
        if donnees.x.shape[1] != self.p.n_agents or not np.all(donnees.rayons == self.p.rayon):
            raise ValueError("population archivee incoherente avec sa configuration")
        self.donnees, self.vitesse = donnees, vitesse
        self.index, self.en_lecture = 0, False
        self.slider = self.bouton = None
        domaine = Couloir(self.p.longueur, self.p.largeur)
        passages = franchissements(donnees.t, donnees.x, *domaine.section_sortie)
        self.instants_passage = passages.instant[passages.sens > 0]

        self.figure = plt.figure(figsize=(12, 5.4), dpi=100, facecolor="#101923")
        self.figure.text(0.07, 0.91, "ViscoCrowd", color="white", fontsize=25, weight="bold")
        sous_titre = "FOULE GUIDÉE  /  BANC EN COULOIR"
        if self.p.obstacles:
            sous_titre += "  /  CONTOURNEMENT D'OBSTACLE"
        self.figure.text(0.07, 0.845, sous_titre, color="#7dd3d8", fontsize=11)
        self.figure.text(
            0.07,
            0.785,
            f"{self.p.n_agents} agents · rayon {self.p.rayon:g} m · graine {self.p.graine}",
            color="#b7c5d0",
            fontsize=10,
        )
        self.temps = self.figure.text(0.93, 0.89, "", ha="right", color="white", fontsize=17)
        self.compteur = self.figure.text(0.93, 0.825, "", ha="right", color="#7dd3d8", fontsize=11)
        self.ax = self.figure.add_axes((0.07, 0.3, 0.86, 0.4), facecolor="#172431")
        self.ax.set_aspect("equal", adjustable="box")
        # Une petite marge aval reste visible ; les agents hors champ restent simules.
        self.ax.set(
            xlim=(-0.4, self.p.longueur + 2.0),
            ylim=(-self.p.largeur / 2 - 0.5, self.p.largeur / 2 + 0.5),
            xlabel="x (m)",
            ylabel="y (m)",
        )
        self.ax.tick_params(colors="#b7c5d0", labelsize=9)
        self.ax.xaxis.label.set_color("#b7c5d0")
        self.ax.yaxis.label.set_color("#b7c5d0")
        for spine in self.ax.spines.values():
            spine.set_visible(False)
        bornes = (0.0, *self.p.frontieres, self.p.longueur + 2.0)
        couleurs = {"SEC": "#263847", "MOUILLE": "#215766", "EAU": "#274b80"}
        noms = {"SEC": "SEC", "MOUILLE": "MOUILLÉ", "EAU": "EAU"}
        for gauche, droite, nom in zip(bornes[:-1], bornes[1:], self.p.milieux, strict=True):
            self.ax.fill_between(
                [gauche, droite],
                -self.p.largeur / 2,
                self.p.largeur / 2,
                color=couleurs[nom],
                zorder=0,
            )
            self.ax.text(
                (gauche + droite) / 2,
                self.p.largeur / 2 + 0.16,
                noms[nom],
                ha="center",
                color="#b7c5d0",
                fontsize=8,
            )
        for y in (-self.p.largeur / 2, self.p.largeur / 2):
            self.ax.plot([0.0, bornes[-1]], [y, y], color="#cbd5df", lw=1.5)
        self.ax.plot([0.0, 0.0], [-self.p.largeur / 2, self.p.largeur / 2], color="#cbd5df", lw=1.5)
        # Les obstacles sont lus dans la configuration archivee, comme tout le reste.
        self.obstacles = [
            Rectangle(
                (o.x_min, o.y_min),
                o.x_max - o.x_min,
                o.y_max - o.y_min,
                facecolor="#cbd5df",
                edgecolor="none",
                zorder=2,
            )
            for o in self.p.rectangles
        ]
        for obstacle in self.obstacles:
            self.ax.add_patch(obstacle)
        self.ax.axvline(self.p.longueur, color="#7dd3d8", linestyle="--", lw=1.3)
        self.ax.text(
            self.p.longueur + 0.12,
            -self.p.largeur / 2 - 0.32,
            "section de sortie →",
            color="#7dd3d8",
            fontsize=8,
            ha="right",
        )
        self.disques = [
            Circle(x, r, facecolor="#f4f8fb", edgecolor="#101923", lw=0.8, zorder=3)
            for x, r in zip(donnees.x[0], donnees.rayons, strict=True)
        ]
        for disque in self.disques:
            self.ax.add_patch(disque)
        self.figure.text(
            0.07,
            0.19,
            "Paramètres illustratifs · passage mesuré, agents conservés en aval",
            color="#b7c5d0",
            fontsize=9,
        )
        self.timer = self.figure.canvas.new_timer(interval=30)
        self.timer.add_callback(self._tic)
        self.figure.canvas.mpl_connect("close_event", lambda event: self.timer.stop())
        if interactif and len(donnees.t) > 1:
            self.slider = Slider(
                self.figure.add_axes((0.28, 0.08, 0.65, 0.035)),
                "Temps (s)",
                donnees.t[0],
                donnees.t[-1],
                valinit=donnees.t[0],
                color="#4daeb9",
            )
            self.slider.label.set_color("white")
            self.slider.valtext.set_color("white")
            self.slider.on_changed(self.aller_au_temps)
            self.bouton = Button(
                self.figure.add_axes((0.07, 0.065, 0.12, 0.065)),
                "Lire",
                color="#7dd3d8",
                hovercolor="#b8eff1",
            )
            self.bouton.on_clicked(self.basculer)
        self.afficher(0)

    def afficher(self, index: int) -> None:
        self.index = int(np.clip(index, 0, len(self.donnees.t) - 1))
        t = self.donnees.t[self.index]
        for disque, x in zip(self.disques, self.donnees.x[self.index], strict=True):
            disque.set_center(x)
        self.temps.set_text(f"{t:05.2f} s  /  {self.donnees.t[-1]:05.2f} s")
        n = np.searchsorted(self.instants_passage, t, side="right")
        self.compteur.set_text(f"Passages vers l'aval : {n}")
        if self.slider is not None:
            self.slider.eventson = False
            self.slider.set_val(t)
            self.slider.eventson = True
        self.figure.canvas.draw_idle()

    def aller_au_temps(self, t: float) -> None:
        if not np.isfinite(t) or not self.donnees.t[0] <= t <= self.donnees.t[-1]:
            raise ValueError("instant hors de l'intervalle archive")
        self.afficher(np.searchsorted(self.donnees.t, t, side="right") - 1)
        self._origine_murale, self._origine_simulee = time.monotonic(), self.donnees.t[self.index]

    def basculer(self, _event=None) -> None:
        self.en_lecture = not self.en_lecture
        if self.en_lecture:
            if self.index == len(self.donnees.t) - 1:
                self.afficher(0)
            self._origine_murale, self._origine_simulee = (
                time.monotonic(),
                self.donnees.t[self.index],
            )
            self.timer.start()
        else:
            self.timer.stop()
        if self.bouton is not None:
            self.bouton.label.set_text("Pause" if self.en_lecture else "Lire")

    def _tic(self) -> None:
        if not self.en_lecture:
            return
        t = self._origine_simulee + self.vitesse * (time.monotonic() - self._origine_murale)
        self.afficher(np.searchsorted(self.donnees.t, t, side="right") - 1)
        if t >= self.donnees.t[-1]:
            self.basculer()

    def exporter_gif(self, chemin, fps: int = 20) -> None:
        indices = indices_animation(self.donnees.t, fps, self.vitesse)
        animation = FuncAnimation(
            self.figure, self.afficher, frames=indices, interval=1000 / fps, repeat=False
        )
        animation.save(chemin, writer=PillowWriter(fps=fps), dpi=100)
