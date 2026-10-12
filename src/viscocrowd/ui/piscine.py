"""Premier apercu de la piscine, vu du dessus.

Les coordonnees servent uniquement a la mise en page de cette maquette : elles
ne definissent ni une geometrie physique ni des parametres de simulation.
"""

from __future__ import annotations

import math
import sys

import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from matplotlib.backends import backend_registry
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle

from viscocrowd.ui.parametres import ParametresAffichage


def _formater_valeur(valeur: int | float | None) -> str:
    if valeur is None:
        return "—"
    # Les entiers (notamment la graine) restent exacts, sans notation scientifique.
    return str(valeur) if isinstance(valeur, int) else f"{valeur:.4g}".replace(".", ",")


def _formater_temps(secondes: float) -> str:
    """Format minutes:secondes.centiemes, sans debordement a l'arrondi."""
    if not math.isfinite(secondes) or secondes < 0:
        raise ValueError("le temps simule doit etre fini et positif ou nul")
    minutes, reste = divmod(round(secondes * 100), 6000)
    secondes_entieres, centiemes = divmod(reste, 100)
    return f"{minutes:02d}:{secondes_entieres:02d}.{centiemes:02d}"


def _dessiner_parametres(ax: Axes, parametres: ParametresAffichage) -> None:
    """Panneau fixe : libelles a gauche, valeurs alignees a droite."""
    ax.set(xlim=(0, 1), ylim=(0, 1))
    ax.set_axis_off()
    ax.text(0, 0.995, "PARAMÈTRES", va="top", fontsize=11, color="white")

    def section(titre: str, y: float) -> None:
        ax.text(0, y, titre, fontsize=9, fontweight="bold", color="white")
        ax.plot([0, 1], [y - 0.013] * 2, color="white", lw=0.4)

    def ligne(libelle: str, valeur: int | float | None, y: float) -> None:
        ax.text(0, y, libelle, va="center", fontsize=9, color="white")
        ax.text(
            1,
            y,
            _formater_valeur(valeur),
            ha="right",
            va="center",
            fontsize=9,
            fontfamily="monospace",
            color="white",
        )

    section("Population", 0.91)
    ligne("Effectif N", parametres.nombre_agents, 0.87)
    ligne("Rayon r (m)", parametres.rayon_agents, 0.83)
    ligne("Niveau de panique", parametres.niveau_panique, 0.79)

    section("Géométrie", 0.73)
    ligne("Nombre d'échelles", parametres.nombre_echelles, 0.69)
    ligne("Largeur de sortie (m)", parametres.largeur_sortie, 0.65)
    ligne("Zone mouillée L (m)", parametres.longueur_zone_mouillee, 0.61)

    section("Milieux", 0.55)
    colonnes = (0.50, 0.73, 0.96)
    for x, nom in zip(colonnes, ("Eau", "Mouillé", "Sec"), strict=True):
        ax.text(x, 0.51, nom, ha="center", fontsize=8, color="white")
    for y, libelle, attribut in (
        (0.47, "s (m/s)", "vitesse"),
        (0.43, "τ (s)", "relaxation"),
        (0.39, "a max (m/s²)", "acceleration_max"),
    ):
        ax.text(0, y, libelle, va="center", fontsize=9, color="white")
        for x, milieu in zip(
            colonnes, (parametres.eau, parametres.mouille, parametres.sec), strict=True
        ):
            ax.text(
                x,
                y,
                _formater_valeur(getattr(milieu, attribut)),
                ha="center",
                va="center",
                fontsize=9,
                fontfamily="monospace",
                color="white",
            )

    section("Franchissements", 0.33)
    ligne("Rebord T (s)", parametres.temps_rebord, 0.29)
    ligne("Échelle T (s)", parametres.temps_echelle, 0.25)

    section("Calcul", 0.19)
    ligne("Pas de temps Δt (s)", parametres.dt, 0.15)
    ligne("Graine", parametres.graine, 0.11)
    ax.text(0, 0.025, "— : non renseigné", fontsize=8, color="white")


def creer_figure(
    *, parametres: ParametresAffichage | None = None, temps_simule: float = 0.0
) -> Figure:
    """Construit le plan et ses annotations, sans lancer de simulation.

    Args:
        parametres: valeurs facultatives du panneau ; vides par defaut.
        temps_simule: temps physique a afficher, en secondes. Il ne depend
            pas du temps ecoule depuis l'ouverture de la fenetre.
    """
    chronometre = _formater_temps(temps_simule)
    fig = plt.figure(figsize=(14, 8), facecolor="black")
    ax = fig.add_axes((0.035, 0.10, 0.65, 0.77), anchor="N")
    panneau = fig.add_axes((0.745, 0.07, 0.22, 0.80))
    _dessiner_parametres(panneau, parametres or ParametresAffichage())
    fig.text(0.04, 0.945, "ViscoCrowd — Vue en plan", fontsize=12, color="white")
    fig.text(0.965, 0.965, "TEMPS SIMULÉ", ha="right", fontsize=8, color="white")
    fig.text(
        0.965,
        0.923,
        chronometre,
        ha="right",
        fontsize=20,
        fontfamily="monospace",
        color="white",
    )
    fig.add_artist(
        Line2D([0.035, 0.965], [0.90, 0.90], transform=fig.transFigure, color="white", lw=0.6)
    )
    fig.add_artist(
        Line2D([0.715, 0.715], [0.085, 0.87], transform=fig.transFigure, color="white", lw=0.6)
    )

    # Le bassin et les deux passages reprennent le croquis de reference.
    # Leur position est indicative ; aucune dimension physique n'est imposee.
    ax.add_patch(
        Rectangle((2, 2.8), 19.5, 10.5, facecolor="black", edgecolor="white", linewidth=2.4)
    )
    ax.text(11.75, 8.05, "Piscine", ha="center", va="center", fontsize=14, color="white")

    # Masquer le rebord sous l'echelle, puis dessiner les montants et les barreaux.
    ax.add_patch(Rectangle((19.15, 11.2), 1.4, 3.3, facecolor="black", edgecolor="none"))
    for x in (19.35, 20.35):
        ax.plot([x, x], [11.4, 14.3], color="white", lw=2, solid_capstyle="round")
    for y in (11.65, 12.2, 12.75, 13.3, 13.85):
        ax.plot([19.35, 20.35], [y, y], color="white", lw=1.6)
    ax.text(19.85, 14.85, "Échelle", ha="center", fontsize=10, color="white")

    # Le cadre reste continu derriere le symbole de sortie.
    ax.add_patch(Rectangle((0, 0), 30, 17, fill=False, edgecolor="white", linewidth=1))
    ax.plot([30, 27.8, 27.8, 30], [7, 7, 10, 10], color="white", lw=1.4)
    ax.text(28.9, 8.5, "Sortie", ha="center", va="center", rotation=270, fontsize=10, color="white")

    # Repere d'orientation sans graduation, les dimensions n'etant pas calibrees.
    for extremite in ((2.4, 0.9), (0.9, 2.1)):
        ax.annotate(
            "",
            xy=extremite,
            xytext=(0.9, 0.9),
            arrowprops={"arrowstyle": "->", "color": "white", "lw": 0.8},
        )
    ax.text(2.6, 0.9, "$x$", va="center", fontsize=10, color="white")
    ax.text(0.9, 2.3, "$y$", ha="center", fontsize=10, color="white")

    ax.set(xlim=(-0.2, 30.2), ylim=(-0.2, 17.2), aspect="equal")
    ax.set_axis_off()
    fig.text(0.04, 0.025, "Schéma géométrique · Dimensions indicatives", fontsize=8, color="white")
    return fig


def ouvrir_interface(
    *, parametres: ParametresAffichage | None = None, temps_simule: float = 0.0
) -> int:
    """Affiche la maquette dans une fenetre locale avec zoom et deplacement."""
    # Conserver le backend choisi par Matplotlib, notamment Cocoa sur macOS.
    # Importer viz.figures ici imposerait Agg et empecherait l'ouverture locale.
    _, interface = backend_registry.resolve_backend(plt.get_backend())
    if interface is None:
        print(
            "L'aperçu nécessite un affichage graphique local. "
            "Lancez cette commande dans un terminal de votre ordinateur avec un backend "
            "Matplotlib interactif (macOS, Tk ou Qt), sans MPLBACKEND=Agg.",
            file=sys.stderr,
        )
        return 1

    fig = creer_figure(parametres=parametres, temps_simule=temps_simule)
    fig.canvas.manager.set_window_title("ViscoCrowd · Aperçu de la piscine")
    plt.show(block=True)
    return 0
