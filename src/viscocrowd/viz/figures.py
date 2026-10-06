"""Figures de validation du moteur.

Les consignes du module sont explicites : pas de capture d'ecran d'une fenetre
de simulation en guise de graphique. Toute figure est produite ici, numerotee,
legendee, avec des axes nommes portant leurs unites, et les parametres de la
simulation qui l'a produite indiques dans le titre.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # rendu hors ecran : indispensable en integration continue
import matplotlib.pyplot as plt
import numpy as np

from viscocrowd.observables.energie import ecart_entrainement, energie_mecanique
from viscocrowd.scenarios.bille_boite import ParametresBille, simuler_bille

# Repere de lisibilite commun a toutes les figures du projet.
plt.rcParams.update(
    {
        "figure.dpi": 150,
        "savefig.dpi": 150,
        "savefig.bbox": "tight",
        "font.size": 10,
        "axes.grid": True,
        "grid.alpha": 0.3,
        "legend.frameon": False,
    }
)


def _enregistrer(fig: plt.Figure, destination: Path, nom: str) -> Path:
    destination.mkdir(parents=True, exist_ok=True)
    chemin = destination / f"{nom}.png"
    fig.savefig(chemin)
    plt.close(fig)
    return chemin


def figure_respect_contrainte(destination: Path) -> Path:
    """Fig. 1 — le depassement de contrainte reste nul a la precision machine.

    Trace pour plusieurs pas de temps, y compris un dt volontairement grossier :
    le confinement ne depend pas de dt, parce que la position est projetee a
    chaque pas. Un schema a rebond explicite ne tiendrait pas cette propriete.
    """
    fig, ax = plt.subplots(figsize=(7, 4))

    for dt in (1e-1, 1e-2, 1e-3):
        resultat = simuler_bille(ParametresBille(dt=dt, duree=10.0))
        rayons = np.full(1, resultat.parametres.rayon)
        violations = np.array(
            [
                resultat.boite.violation(resultat.x[p], rayons, float(resultat.t[p]))
                for p in range(resultat.t.size)
            ]
        )
        ax.plot(resultat.t, np.abs(violations), label=f"$\\Delta t$ = {dt:g} s", lw=1)

    ax.set_yscale("log")
    ax.set_xlabel("temps $t$ (s)")
    ax.set_ylabel(r"$\max_i \left( x \cdot n_i - (R-r) \right)$  (m)")
    ax.set_title(
        "Fig. 1 — Respect de la contrainte de confinement\n"
        "$R$ = 1 m, $r$ = 0,05 m, $\\omega$ = 1 rad/s",
        fontsize=10,
    )
    ax.legend()
    return _enregistrer(fig, destination, "fig01_respect_contrainte")


def figure_energie(destination: Path) -> Path:
    """Fig. 2 — l'energie mecanique decroit par sauts, en boite fixe.

    On se place a omega = 0 : aucune paroi ne travaille, donc l'energie ne peut
    que decroitre. En vol libre elle baisse de (1/2) dt^2 |g|^2 par pas, et
    chaque choc mou en dissipe une part sous forme de chaleur.
    """
    resultat = simuler_bille(ParametresBille(omega=0.0, dt=1e-3, duree=10.0))
    energie = energie_mecanique(resultat.x, resultat.v, masse=resultat.parametres.masse)

    fig, ax = plt.subplots(figsize=(7, 4))
    ax.plot(resultat.t, energie, lw=1, color="#b4432f")

    ax.set_xlabel("temps $t$ (s)")
    ax.set_ylabel("energie mecanique $E$ (J)")
    ax.set_title(
        "Fig. 2 — Dissipation de l'energie par les chocs mous\n"
        "boite fixe ($\\omega$ = 0), $m$ = 1 kg, $\\Delta t$ = $10^{-3}$ s",
        fontsize=10,
    )
    return _enregistrer(fig, destination, "fig02_energie")


def figure_entrainement(destination: Path) -> Path:
    """Fig. 3 — l'entrainement solide n'a lieu qu'en regime centrifuge.

    Resultat non trivial : le critere de validation du sujet (« la bille se
    stabilise dans un coin et tourne solidairement avec la boite ») n'est
    verifie que si la force centrifuge domine la gravite, soit
    omega^2 R / g >~ 1. La valeur suggeree omega = 1 rad/s se situe nettement
    en dessous de ce seuil.
    """
    fig, ax = plt.subplots(figsize=(7, 4))

    for omega in (1.0, 3.0, 5.0, 10.0):
        resultat = simuler_bille(ParametresBille(omega=omega, dt=1e-3, duree=20.0))
        v_solide = np.stack(
            [resultat.boite.vitesse_entrainement(resultat.x[p]) for p in range(resultat.t.size)]
        )
        ecart = ecart_entrainement(resultat.v, v_solide)
        rapport = omega**2 * resultat.parametres.demi_largeur / 9.81
        ax.plot(
            resultat.t,
            ecart,
            lw=1,
            label=f"$\\omega$ = {omega:g} rad/s  ($\\omega^2 R/g$ = {rapport:.2f})",
        )

    ax.set_yscale("log")
    ax.set_xlabel("temps $t$ (s)")
    ax.set_ylabel(r"$\left| v - \omega x^{\perp} \right|$  (m/s)")
    ax.set_title(
        "Fig. 3 — Convergence vers la vitesse d'entrainement du solide\n"
        "$R$ = 1 m, $r$ = 0,05 m, $\\Delta t$ = $10^{-3}$ s",
        fontsize=10,
    )
    ax.legend(fontsize=8)
    return _enregistrer(fig, destination, "fig03_entrainement")


def figure_trajectoire(destination: Path) -> Path:
    """Fig. 4 — instantanes de la configuration a des instants choisis."""
    resultat = simuler_bille(ParametresBille(omega=5.0, dt=1e-3, duree=20.0))
    instants = [0.0, 1.0, 5.0, 20.0]

    fig, axes = plt.subplots(1, len(instants), figsize=(12, 3.2))

    for ax, instant in zip(axes, instants, strict=True):
        indice = int(np.argmin(np.abs(resultat.t - instant)))
        theta = resultat.boite.theta(float(resultat.t[indice]))
        demi = resultat.parametres.demi_largeur

        coins_locaux = np.array([[-1, -1], [1, -1], [1, 1], [-1, 1], [-1, -1]]) * demi
        rotation = np.array([[np.cos(theta), -np.sin(theta)], [np.sin(theta), np.cos(theta)]])
        coins = coins_locaux @ rotation.T

        ax.plot(coins[:, 0], coins[:, 1], color="#333333", lw=1.2)
        ax.plot(
            resultat.x[: indice + 1, 0, 0],
            resultat.x[: indice + 1, 0, 1],
            lw=0.5,
            alpha=0.5,
            color="#b4432f",
        )
        ax.add_patch(
            plt.Circle(
                tuple(resultat.x[indice, 0]),
                resultat.parametres.rayon,
                color="#b4432f",
            )
        )
        ax.set_aspect("equal")
        ax.set_xlim(-1.6, 1.6)
        ax.set_ylim(-1.6, 1.6)
        ax.set_title(f"$t$ = {resultat.t[indice]:.1f} s", fontsize=9)
        ax.set_xlabel("$x_1$ (m)", fontsize=8)
        ax.grid(alpha=0.2)

    axes[0].set_ylabel("$x_2$ (m)", fontsize=8)
    fig.suptitle(
        "Fig. 4 — Bille dans une boite en rotation, $\\omega$ = 5 rad/s, $\\Delta t$ = $10^{-3}$ s",
        fontsize=10,
    )
    return _enregistrer(fig, destination, "fig04_trajectoire")


TOUTES_LES_FIGURES = (
    figure_respect_contrainte,
    figure_energie,
    figure_entrainement,
    figure_trajectoire,
)


def produire_toutes(destination: Path) -> list[Path]:
    """Produit l'ensemble des figures de validation du moteur."""
    return [fabrique(destination) for fabrique in TOUTES_LES_FIGURES]
