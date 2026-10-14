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

from viscocrowd.core.integrator import chute_libre, trajectoire
from viscocrowd.core.state import GRAVITE, State
from viscocrowd.observables.energie import ecart_entrainement, energie_mecanique
from viscocrowd.scenarios.bille_boite import ParametresBille, simuler_bille
from viscocrowd.scenarios.tassement import ParametresTassement, simuler_tassement

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


# Parametres du tassement servant aux figures 5 et 6. Ils sont groupes ici pour
# que les deux figures decrivent le MEME scenario, et que le manifeste n'ait
# qu'une seule configuration a declarer.
TASSEMENT_FIGURES = {"n_agents": 36, "duree": 2.5, "graine": 1}
TASSEMENT_DT = 2e-3
CONVERGENCE_DT = (4e-3, 2e-3, 1e-3, 5e-4, 2.5e-4)


def figure_tassement(destination: Path) -> Path:
    """Fig. 5 — instantanes de l'empilement de 36 disques.

    Le jalon 2 n'avait aucune figure : il se validait par des tableaux de
    nombres. Or le reproche fait a une simulation de foule est d'abord visuel —
    « vos agents se chevauchent » — et un tableau de recouvrements residuels n'y
    repond pas aussi directement que quatre images.

    Les disques sont colores par leur rangee de depart : on voit que la pile
    s'inverse peu, chaque rangee restant globalement a sa place. C'est le
    comportement attendu d'un empilement sans agitation, et c'est verifiable a
    l'oeil, ce que le recouvrement residuel ne permet pas.
    """
    parametres = ParametresTassement(dt=TASSEMENT_DT, **TASSEMENT_FIGURES)
    resultat = simuler_tassement(parametres)
    instants = [0.0, 0.3, 0.8, parametres.duree]
    demi = parametres.demi_largeur

    # Teinte par rangee de depart, de la plus haute a la plus basse.
    y_initial = resultat.x[0, :, 1]
    rang = np.argsort(np.argsort(-y_initial)) / max(len(y_initial) - 1, 1)
    couleurs = plt.get_cmap("viridis")(rang)

    fig, axes = plt.subplots(1, len(instants), figsize=(13, 3.6))

    for ax, instant in zip(axes, instants, strict=True):
        indice = int(np.argmin(np.abs(resultat.t - instant)))
        ax.add_patch(
            plt.Rectangle((-demi, -demi), 2 * demi, 2 * demi, fill=False, color="#333333", lw=1.2)
        )
        for agent in range(parametres.n_agents):
            ax.add_patch(
                plt.Circle(
                    tuple(resultat.x[indice, agent]),
                    parametres.rayon,
                    facecolor=couleurs[agent],
                    edgecolor="#1a1a1a",
                    lw=0.4,
                )
            )
        ax.set_aspect("equal")
        ax.set_xlim(-1.15, 1.15)
        ax.set_ylim(-1.15, 1.15)
        ax.set_title(f"$t$ = {resultat.t[indice]:.2f} s", fontsize=9)
        ax.set_xlabel("$x_1$ (m)", fontsize=8)
        ax.grid(alpha=0.15)

    axes[0].set_ylabel("$x_2$ (m)", fontsize=8)
    recouvrement = resultat.recouvrement_max()
    fig.suptitle(
        f"Fig. 5 — Empilement de {parametres.n_agents} disques de "
        f"{parametres.rayon * 100:.0f} cm, $\\Delta t$ = "
        f"{TASSEMENT_DT:.0e} s, graine {parametres.graine}\n"
        f"recouvrement residuel maximal sur toute la simulation : "
        f"{recouvrement:.1e} m, soit {recouvrement / parametres.rayon:.0e} rayon",
        fontsize=10,
    )
    return _enregistrer(fig, destination, "fig05_tassement")


def _erreur_chute_libre(dt: float, duree: float = 1.0) -> float:
    """Ecart a la solution CONTINUE exacte d'une chute libre, apres `duree`.

    Le schema semi-implicite a sa propre solution fermee, exacte au bit pres
    (c'est ce que verifient les tests). Ici on mesure autre chose : l'ecart a la
    solution du probleme CONTINU, c'est-a-dire l'erreur de discretisation. Elle
    vaut analytiquement |g| t dt / 2, donc l'ordre 1.
    """
    _, x, _ = trajectoire(
        State.single((0.0, 0.0), (1.0, 0.0)),
        dt=dt,
        duree=duree,
        vitesse_libre=chute_libre(GRAVITE),
    )
    exact = np.array([1.0 * duree, 0.5 * GRAVITE[1] * duree**2])
    return float(np.linalg.norm(x[-1, 0] - exact))


def _hauteur_finale_tassement(dt: float) -> float:
    """Hauteur moyenne finale du tas, grandeur d'ensemble robuste.

    On ne compare pas les trajectoires disque par disque : les chocs sont
    discontinus, et deux pas de temps voisins n'echangent pas les memes contacts
    au meme instant. La hauteur moyenne du tas, elle, est une grandeur
    d'ensemble, celle que l'invariant de stabilite en dt controle deja.
    """
    resultat = simuler_tassement(ParametresTassement(dt=dt, **TASSEMENT_FIGURES))
    return float(resultat.x[-1, :, 1].mean())


def figure_convergence_dt(destination: Path) -> Path:
    """Fig. 6 — ordre de convergence en pas de temps, avec et sans contacts.

    Une simulation qui ne converge pas en dt ne mesure rien : ses resultats
    dependent d'un parametre numerique et non de la physique. Cette figure
    l'etablit par la mesure, sur les deux regimes du moteur.

    A gauche, la chute libre : aucune contrainte active, la solution continue
    est connue, et l'erreur suit EXACTEMENT |g| t dt / 2. Ordre 1, celui du
    schema semi-implicite.

    A droite, l'empilement : les contacts rendent le probleme non regulier. On
    mesure donc une auto-convergence, l'ecart a la solution la plus fine.
    L'ordre observe est inferieur a 2 et irregulier, ce qui est attendu : entre
    deux pas de temps voisins, les disques n'echangent pas les memes contacts au
    meme instant, et ces rearrangements discrets dominent l'erreur une fois
    celle-ci descendue au micrometre.
    """
    dts = np.array(CONVERGENCE_DT)

    erreurs_libre = np.array([_erreur_chute_libre(float(dt)) for dt in dts])
    attendu_libre = abs(GRAVITE[1]) * 1.0 * dts / 2.0

    hauteurs = np.array([_hauteur_finale_tassement(float(dt)) for dt in dts])
    erreurs_tas = np.abs(hauteurs[:-1] - hauteurs[-1])
    dts_tas = dts[:-1]
    pente_tas = float(np.polyfit(np.log(dts_tas), np.log(erreurs_tas), 1)[0])

    fig, (gauche, droite) = plt.subplots(1, 2, figsize=(11, 4.2))

    gauche.loglog(
        dts,
        attendu_libre,
        "-",
        color="#999999",
        lw=3,
        alpha=0.5,
        label=r"analytique $|g|\,t\,\Delta t/2$",
    )
    gauche.loglog(dts, erreurs_libre, "o", color="#b4432f", ms=6, label="mesure")
    gauche.set_title("Sans contact : chute libre, $t$ = 1 s", fontsize=10)
    gauche.set_xlabel(r"$\Delta t$ (s)")
    gauche.set_ylabel("erreur sur la position finale (m)")
    gauche.legend(fontsize=8)
    gauche.grid(which="both", alpha=0.25)
    ecart_relatif = float(np.max(np.abs(erreurs_libre - attendu_libre) / attendu_libre))
    gauche.text(
        0.04,
        0.06,
        f"ordre 1 verifie\necart a l'analytique < {ecart_relatif:.0e}",
        transform=gauche.transAxes,
        fontsize=8,
        va="bottom",
    )

    reference_1 = erreurs_tas[0] * (dts_tas / dts_tas[0])
    reference_2 = erreurs_tas[0] * (dts_tas / dts_tas[0]) ** 2
    droite.loglog(dts_tas, reference_1, "--", color="#999999", lw=1, label="pente 1")
    droite.loglog(dts_tas, reference_2, ":", color="#999999", lw=1, label="pente 2")
    droite.loglog(dts_tas, erreurs_tas, "s", color="#2f6fb4", ms=6, label="mesure")
    droite.set_title(
        f"Avec contacts : hauteur du tas, {TASSEMENT_FIGURES['n_agents']} disques",
        fontsize=10,
    )
    droite.set_xlabel(r"$\Delta t$ (s)")
    droite.set_ylabel(r"$|h(\Delta t) - h(\Delta t_{\min})|$ (m)")
    droite.legend(fontsize=8)
    droite.grid(which="both", alpha=0.25)
    droite.text(
        0.04,
        0.06,
        f"pente mesuree {pente_tas:.2f}\nerreur deja sous {erreurs_tas.max() * 1e6:.0f} $\\mu$m",
        transform=droite.transAxes,
        fontsize=8,
        va="bottom",
    )

    # Les graduations automatiques d'un axe logarithmique se chevauchent sur une
    # plage aussi etroite : on n'affiche que les pas de temps reellement joues.
    for axe, valeurs in ((gauche, dts), (droite, dts_tas)):
        axe.set_xticks(valeurs)
        axe.set_xticklabels([f"{v * 1e3:g}" for v in valeurs])
        axe.set_xticks([], minor=True)
        axe.set_xlabel(r"$\Delta t$ (ms)")

    fig.suptitle(
        "Fig. 6 — Convergence en pas de temps : ordre 1 sans contact, "
        "limite par les rearrangements de contacts avec",
        fontsize=10,
    )
    fig.tight_layout()
    return _enregistrer(fig, destination, "fig06_convergence_dt")


TOUTES_LES_FIGURES = (
    figure_respect_contrainte,
    figure_energie,
    figure_entrainement,
    figure_trajectoire,
    figure_tassement,
    figure_convergence_dt,
)


def produire_toutes(destination: Path) -> list[Path]:
    """Produit l'ensemble des figures de validation du moteur."""
    return [fabrique(destination) for fabrique in TOUTES_LES_FIGURES]
