"""Premier apercu de la piscine, vu du dessus.

Une unite du plan represente un metre, pour comparer bassin, passages et
taille humaine. Ces dimensions de travail restent a valider pour le scenario.
"""

from __future__ import annotations

import math
import sys
from dataclasses import replace
from numbers import Integral

import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from matplotlib.backends import backend_registry
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from matplotlib.patches import Circle, Rectangle
from matplotlib.widgets import Button

from viscocrowd.ui.parametres import DimensionsPlan, ParametresAffichage


def _formater_valeur(valeur: int | float | None) -> str:
    if valeur is None:
        return "—"
    # Les entiers (notamment la graine) restent exacts, sans notation scientifique.
    if isinstance(valeur, Integral):
        return str(int(valeur))
    return f"{valeur:.4g}".replace(".", ",")


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


def _installer_panneau_repliable(fig: Figure, plan: Axes, panneau: Axes, afficher: bool) -> None:
    """Repartit la place sans changer les coordonnees ni le zoom du plan."""
    separateur = Line2D(
        [0.715, 0.715], [0.085, 0.87], transform=fig.transFigure, color="white", lw=0.6
    )
    fig.add_artist(separateur)
    commande = fig.add_axes((0.65, 0.928, 0.16, 0.044), label="commande_parametres")
    bouton = Button(commande, "", color="black", hovercolor="0.15")
    bouton.label.set(color="white", fontsize=9)
    for bord in commande.spines.values():
        bord.set(color="white", linewidth=0.6)

    def afficher_panneau(visible: bool) -> None:
        panneau.set_visible(visible)
        separateur.set_visible(visible)
        plan.set_position((0.035, 0.10, 0.65 if visible else 0.93, 0.77))
        bouton.label.set_text("Masquer paramètres" if visible else "Afficher paramètres")

    def basculer(_evenement: object) -> None:
        afficher_panneau(not panneau.get_visible())
        fig.canvas.draw_idle()

    afficher_panneau(afficher)
    bouton.on_clicked(basculer)
    # Matplotlib demande de conserver le widget pour maintenir ses callbacks actifs.
    fig._bouton_parametres = bouton


def creer_figure(
    *,
    parametres: ParametresAffichage | None = None,
    temps_simule: float = 0.0,
    dimensions: DimensionsPlan | None = None,
    afficher_parametres: bool = False,
) -> Figure:
    """Construit le plan et ses annotations, sans lancer de simulation.

    Args:
        parametres: valeurs facultatives du panneau. Le rayon de reference,
            le nombre d'echelles et la largeur de sortie sont ceux du plan dessine.
        temps_simule: temps physique a afficher, en secondes. Il ne depend
            pas du temps ecoule depuis l'ouverture de la fenetre.
        dimensions: dimensions de travail en metres, partagees par le dessin,
            les annotations et le panneau. Elles ne lancent aucun calcul physique.
        afficher_parametres: ouvre le panneau des la creation. Le bouton permet
            ensuite de l'afficher ou le masquer, sans modifier les valeurs.
    """
    chronometre = _formater_temps(temps_simule)
    dimensions = dimensions or DimensionsPlan()
    parametres = replace(
        parametres or ParametresAffichage(),
        rayon_agents=dimensions.rayon_reference,
        nombre_echelles=1,
        largeur_sortie=dimensions.largeur_sortie,
    )
    fig = plt.figure(figsize=(14, 8), facecolor="black")
    ax = fig.add_axes((0.035, 0.10, 0.93, 0.77), anchor="N", label="plan")
    panneau = fig.add_axes((0.745, 0.07, 0.22, 0.80), label="parametres")
    _dessiner_parametres(panneau, parametres)
    _installer_panneau_repliable(fig, ax, panneau, afficher_parametres)
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

    # Bassin, passages et repere humain utilisent tous la meme unite : le metre.
    x_bassin, y_bassin = dimensions.plage_gauche, dimensions.plage_verticale
    longueur, largeur = dimensions.longueur_totale, dimensions.largeur_totale
    ax.add_patch(
        Rectangle(
            (x_bassin, y_bassin),
            dimensions.longueur_bassin,
            dimensions.largeur_bassin,
            facecolor="black",
            edgecolor="white",
            linewidth=2,
        )
    )
    ax.text(
        x_bassin,
        y_bassin + dimensions.largeur_bassin + 0.8,
        f"Piscine · {_formater_valeur(dimensions.longueur_bassin)} \N{MULTIPLICATION SIGN} "
        f"{_formater_valeur(dimensions.largeur_bassin)} m",
        va="bottom",
        fontsize=11,
        color="white",
    )

    # Masquer le rebord sous l'echelle, puis dessiner les montants et les barreaux.
    x_echelle = x_bassin + 0.9 * dimensions.longueur_bassin
    y_echelle = y_bassin + dimensions.largeur_bassin
    gauche = x_echelle - dimensions.largeur_echelle / 2
    droite = x_echelle + dimensions.largeur_echelle / 2
    bas = y_echelle - dimensions.longueur_echelle / 2
    haut = y_echelle + dimensions.longueur_echelle / 2
    ax.add_patch(
        Rectangle(
            (gauche, bas),
            dimensions.largeur_echelle,
            dimensions.longueur_echelle,
            facecolor="black",
            edgecolor="none",
        )
    )
    for x in (gauche, droite):
        ax.plot([x, x], [bas, haut], color="white", lw=1.4, solid_capstyle="round")
    for fraction in (0.15, 0.38, 0.62, 0.85):
        y = bas + fraction * dimensions.longueur_echelle
        ax.plot([gauche, droite], [y, y], color="white", lw=1)
    ax.text(
        x_echelle,
        haut + 0.6,
        f"Échelle\n{_formater_valeur(dimensions.largeur_echelle)} m",
        ha="center",
        va="bottom",
        fontsize=9,
        color="white",
    )

    # Le cadre reste continu derriere le symbole de sortie.
    ax.add_patch(Rectangle((0, 0), longueur, largeur, fill=False, edgecolor="white", linewidth=1))
    bas_sortie = (largeur - dimensions.largeur_sortie) / 2
    haut_sortie = bas_sortie + dimensions.largeur_sortie
    x_sortie = longueur - dimensions.largeur_sortie / 2
    ax.plot(
        [longueur, x_sortie, x_sortie, longueur],
        [bas_sortie, bas_sortie, haut_sortie, haut_sortie],
        color="white",
        lw=1.4,
    )
    ax.text(
        x_sortie - 0.5,
        largeur / 2,
        f"Sortie\n{_formater_valeur(dimensions.largeur_sortie)} m",
        ha="right",
        va="center",
        fontsize=10,
        color="white",
    )
    ax.text(
        0,
        largeur + 0.6,
        f"Emprise · {_formater_valeur(longueur)} \N{MULTIPLICATION SIGN} "
        f"{_formater_valeur(largeur)} m",
        fontsize=9,
        color="white",
    )

    # Coter la distance reelle au mur, independamment de la place prise par le panneau.
    bord_bassin = x_bassin + dimensions.longueur_bassin
    ax.annotate(
        "",
        xy=(longueur, 1.8),
        xytext=(bord_bassin, 1.8),
        arrowprops={"arrowstyle": "<->", "color": "white", "lw": 0.7, "shrinkA": 0, "shrinkB": 0},
    )
    for x in (bord_bassin, longueur):
        ax.plot([x, x], [1.4, 2.2], color="white", lw=0.7)
    ax.text(
        (bord_bassin + longueur) / 2,
        2.5,
        f"Bassin → sortie · {_formater_valeur(dimensions.plage_sortie)} m",
        ha="center",
        fontsize=9,
        color="white",
    )

    # Repere d'orientation, distinct de la barre d'echelle sous le plan.
    for extremite in ((2.4, 0.9), (0.9, 2.1)):
        ax.annotate(
            "",
            xy=extremite,
            xytext=(0.9, 0.9),
            arrowprops={"arrowstyle": "->", "color": "white", "lw": 0.8},
        )
    ax.text(2.6, 0.9, "$x$", va="center", fontsize=10, color="white")
    ax.text(0.9, 2.3, "$y$", ha="center", fontsize=10, color="white")

    # Ces reperes sont dans le MEME axe que le bassin : ils suivent son zoom
    # et son redimensionnement. Le disque est une reference, pas un agent ajoute.
    ax.plot([0, 5], [-1.2, -1.2], color="white", lw=1.4)
    for x, etiquette in ((0, "0"), (5, "5 m")):
        ax.plot([x, x], [-1.35, -1.05], color="white", lw=1)
        ax.text(x, -1.7, etiquette, ha="center", fontsize=9, color="white")
    ax.add_patch(
        Circle((10, -1.2), dimensions.rayon_reference, facecolor="white", edgecolor="none")
    )
    ax.text(
        10 + dimensions.rayon_reference + 0.4,
        -1.2,
        f"Personne · diamètre {_formater_valeur(2 * dimensions.rayon_reference)} m",
        va="center",
        fontsize=9,
        color="white",
    )

    ax.set(xlim=(-0.6, longueur + 0.6), ylim=(-2.3, largeur + 1.3), aspect="equal")
    ax.set_axis_off()
    fig.text(0.04, 0.025, "Vue en mètres · Dimensions provisoires", fontsize=8, color="white")
    return fig


def ouvrir_interface(
    *,
    parametres: ParametresAffichage | None = None,
    temps_simule: float = 0.0,
    dimensions: DimensionsPlan | None = None,
    afficher_parametres: bool = False,
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

    fig = creer_figure(
        parametres=parametres,
        temps_simule=temps_simule,
        dimensions=dimensions,
        afficher_parametres=afficher_parametres,
    )
    fig.canvas.manager.set_window_title("ViscoCrowd · Aperçu de la piscine")
    plt.show(block=True)
    return 0
