"""Carte de pression : par quelles chaines de contacts la foule pousse, et ou elle bloque.

Un modele a exclusion dure n'a pas de force de contact explicite : la projection
retire a chaque agent la part de sa vitesse libre qui le ferait penetrer un voisin
ou un mur. Cette part, a_i = (v_i - v_libre_i) / dt, est une acceleration (m/s^2,
soit une force par kilogramme). On la mesure pendant la simulation
(`simuler_piscine(..., contraintes=True)`).

Elle ne suffit pas a voir les chaines de force : dans un bouchon immobile, chaque
agent ne se voit retirer que SA poussee, la meme pour tous. La force transmise se
cumule, elle, le long des contacts : dans une file poussee contre la porte, le
dernier contact porte la poussee de toute la file. On la retrouve en cherchant,
a chaque image, les intensites de contact lambda_ij >= 0 qui expliquent les a_i :

    a_i = somme_j lambda_ij u_ij + w_i,     u_ij = (x_i - x_j) / |x_i - x_j|

ou w_i est la reaction d'un mur, inconnue libre pour les seuls agents a moins de
`JEU_CONTACT` d'une paroi. Moindres carres positifs (`scipy.optimize.nnls`).
Dans une colonne de trois disques poussee contre un mur, on retrouve 1, 2 puis 3
fois la poussee (test). Les traits rouges et epais sont les chaines de force ; un
arc de traits devant la porte est une arche.

Limites : une foule rigide est hyperstatique, plusieurs jeux de lambda expliquent
les memes a_i ; nnls en rend un, pas « le » vrai. La reaction d'un mur n'est pas
contrainte a sa normale. Aucune valeur n'est etalonnee.

Sensibilite au pas : un choc (agent qui arrive a v_n sur un voisin arrete) donne
a ~ v_n / dt et double quand dt est divise par deux ; une poussee soutenue n'en depend pas.
Sur `experiments/demo/pression-porte-saturee.yaml`, le 98e centile passe de 61,3 a
74,1 m/s^2 de dt = 0,005 a 0,0025 s (+21 %) : ni chocs purs, ni chaines independantes du
pas. Les intensites sont donc des ordres de grandeur, pas des forces a convertir en newtons.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from scipy.optimize import nnls

from viscocrowd.geometry.grille import paires_candidates
from viscocrowd.scenarios.piscine import EAU, PLAGE
from viscocrowd.ui.relecture_piscine import LecteurPiscine

JEU_CONTACT = 0.005  # m : en deca, deux disques (ou un disque et un mur) se touchent
COULEURS_PRESSION = ("#4a6378", "#ffd166", "#ff7b3a", "#e0245e")


def contacts(x: np.ndarray, r: np.ndarray, actifs: np.ndarray) -> np.ndarray:
    """Paires (K, 2) d'agents actifs dont le jeu est inferieur a `JEU_CONTACT`."""
    indices = np.flatnonzero(actifs)
    if indices.size < 2:
        return np.empty((0, 2), dtype=np.int64)
    return indices[paires_candidates(x[indices], r[indices], JEU_CONTACT)]


def forces_de_contact(
    x: np.ndarray,
    a: np.ndarray,
    paires: np.ndarray,
    contre_mur: np.ndarray,
    *,
    avec_residu: bool = False,
) -> np.ndarray | tuple[np.ndarray, float]:
    """Intensites lambda (K,) >= 0 des contacts `paires`, en m/s^2. Voir le module.

    Args:
        x: (N, 2) positions, en m.
        a: (N, 2) accelerations imposees par la projection, en m/s^2.
        paires: (K, 2) agents en contact.
        contre_mur: (N,) vrai pour un agent qui touche une paroi : il recoit une
            reaction libre, sans laquelle son equilibre serait impossible.
        avec_residu: rend aussi le residu relatif |A lambda - a| / |a| (sans unite). Pres
            de 0, les intensites expliquent les corrections ; un residu eleve signale un
            contact manque (jeu > `JEU_CONTACT`) ou une reaction de mur mal posee.
    """
    if paires.shape[0] == 0:
        return (np.zeros(0), 0.0) if avec_residu else np.zeros(0)
    agents = np.unique(paires)
    ligne = {int(k): n for n, k in enumerate(agents)}
    murs = [k for k in agents if contre_mur[k]]
    A = np.zeros((2 * len(agents), len(paires) + 4 * len(murs)))
    for col, (i, j) in enumerate(paires):
        u = x[i] - x[j]
        u = u / np.hypot(*u)
        A[2 * ligne[i] : 2 * ligne[i] + 2, col] += u
        A[2 * ligne[j] : 2 * ligne[j] + 2, col] -= u
    for m, k in enumerate(murs):
        base, n = len(paires) + 4 * m, ligne[int(k)]
        for d, (axe, signe) in enumerate(((0, 1), (0, -1), (1, 1), (1, -1))):
            A[2 * n + axe, base + d] = signe
    b = a[agents].ravel()
    solution, residu = nnls(A, b, maxiter=50 * A.shape[1])
    if avec_residu:
        return solution[: len(paires)], float(residu / max(np.linalg.norm(b), 1e-12))
    return solution[: len(paires)]


class LecteurPression(LecteurPiscine):
    """Relecture piscine avec le reseau des contacts, colore par leur intensite."""

    def __init__(
        self, donnees, contraintes: np.ndarray, piscine_contact, *, interactif=True, vitesse=1.0
    ):
        contraintes = np.asarray(contraintes, dtype=float)
        if contraintes.shape != donnees.x.shape:
            raise ValueError("contraintes doit avoir la forme (P, N, 2) des positions")
        if not np.all(np.isfinite(contraintes)):
            raise ValueError("contraintes doit etre finie")
        self.contraintes = contraintes
        self._contre_mur = piscine_contact
        self._cache: dict[int, tuple[np.ndarray, np.ndarray]] = {}
        self._residus: dict[int, float] = {}
        super().__init__(donnees, interactif=interactif, vitesse=vitesse)
        from matplotlib.collections import LineCollection
        from matplotlib.colors import LinearSegmentedColormap, Normalize

        # Echelle fixe pour toute l'evacuation : 98e centile sur une image par seconde.
        pas = max(1, round(1.0 / max(float(np.median(np.diff(donnees.t))), 1e-9)))
        echantillon = np.concatenate([self.reseau_a(k)[1] for k in range(0, len(donnees.t), pas)])
        self.echelle = float(np.quantile(echantillon, 0.98)) if echantillon.size else 1.0
        self.echelle = max(self.echelle, 1e-9)
        self.cmap = LinearSegmentedColormap.from_list("pression", COULEURS_PRESSION)
        self.norme = Normalize(0.0, self.echelle)
        self.ax.grid(False)
        self.sous_titre.set_text("ÉVACUATION PISCINE  /  FORCES DE CONTACT")
        for legende in list(self.figure.legends):
            legende.remove()
        self.ax.set_position((0.05, 0.29, 0.56, 0.46))
        self.reseau = LineCollection([], cmap=self.cmap, norm=self.norme, zorder=5)
        self.ax.add_collection(self.reseau)
        # Zoom sur la porte, ou se forment les arches.
        from matplotlib.patches import Circle

        g = self.p.piscine
        (xp, yb), (_, yh) = g.porte
        yc = 0.5 * (yb + yh)
        self.zoom = self.figure.add_axes((0.66, 0.27, 0.30, 0.50), facecolor="#263847")
        self.zoom.set_aspect("equal")
        self.zoom.set(xlim=(xp - 4.5, xp + 0.5), ylim=(yc - 3, yc + 3), xticks=[], yticks=[])
        self.zoom.set_title("Devant la porte", color="#b7c5d0", fontsize=10)
        for spine in self.zoom.spines.values():
            spine.set_color("#7dd3d8")
        self.zoom.plot([xp, xp], [yc - 3, yb], color="#cbd5df", lw=2)
        self.zoom.plot([xp, xp], [yh, yc + 3], color="#cbd5df", lw=2)
        self.zoom.plot([xp, xp], [yb, yh], color="#7dd3d8", lw=3)
        self.disques_zoom = [
            Circle(p, r, facecolor="#f4f8fb", edgecolor="#101923", lw=0.5, zorder=4)
            for p, r in zip(donnees.x[0], donnees.rayons, strict=True)
        ]
        for disque in self.disques_zoom:
            self.zoom.add_patch(disque)
        self.reseau_zoom = LineCollection([], cmap=self.cmap, norm=self.norme, zorder=5)
        self.zoom.add_collection(self.reseau_zoom)
        barre = self.figure.colorbar(
            self.reseau, ax=[self.ax, self.zoom], orientation="horizontal", fraction=0.04, pad=0.1
        )
        barre.set_label("intensité du contact (m/s², soit N/kg)", color="#b7c5d0")
        barre.ax.tick_params(colors="#b7c5d0", labelsize=9)
        self.afficher(self.index)

    def reseau_a(self, index: int) -> tuple[np.ndarray, np.ndarray]:
        """Contacts et intensites a l'instant archive `index`, calcules une fois."""
        if index not in self._cache:
            x, etats = self.donnees.x[index], self.donnees.etats[index]
            actifs = (etats == EAU) | (etats == PLAGE)
            paires = contacts(x, self.donnees.rayons, actifs)
            mur = self._contre_mur(x, self.donnees.rayons, self.donnees.t[index]) & actifs
            lam, residu = forces_de_contact(
                x, self.contraintes[index], paires, mur, avec_residu=True
            )
            self._cache[index] = (paires, lam)
            self._residus[index] = residu
        return self._cache[index]

    def residu_a(self, index: int) -> float:
        """Residu relatif de `forces_de_contact` a l'instant archive `index` (sans unite)."""
        self.reseau_a(index)
        return self._residus[index]

    def afficher(self, index: int) -> None:
        super().afficher(index)
        if not hasattr(self, "reseau_zoom"):
            return  # premier affichage du parent, avant la construction du reseau
        x, etats = self.donnees.x[self.index], self.donnees.etats[self.index]
        paires, lam = self.reseau_a(self.index)
        largeurs = 0.5 + 3.5 * np.clip(lam / self.echelle, 0, 1)
        for reseau in (self.reseau, self.reseau_zoom):
            reseau.set_segments(x[paires])
            reseau.set_array(lam)
            reseau.set_linewidths(largeurs)
        for disque, position, etat in zip(self.disques_zoom, x, etats, strict=True):
            disque.set_center(position)
            disque.set_visible(etat in (EAU, PLAGE))
        texte = self.compteur.get_text().split("  ·")[0]
        maximum = f"{lam.max():.1f} m/s²" if lam.size else "—"
        self.compteur.set_text(f"{texte}  ·  contacts : {len(paires)}  ·  max : {maximum}")
        self.figure.canvas.draw_idle()


def contre_mur(piscine):
    """Fonction (x, r, t) -> (N,) : agents a moins de `JEU_CONTACT` d'une paroi."""

    def _test(x: np.ndarray, r: np.ndarray, t: float) -> np.ndarray:
        gonfles = r + JEU_CONTACT
        return np.array(
            [piscine.violation(x[k : k + 1], gonfles[k : k + 1], t) > 0 for k in range(len(x))]
        )

    return _test


def simuler_pour_pression(configuration: dict, archiver_tous: int = 1):
    """Simule une configuration piscine en mesurant les contraintes.

    Returns:
        (donnees, contraintes, piscine) : la trajectoire au format de relecture, les
        accelerations (P, N, 2) et la geometrie.
    """
    from viscocrowd.io.trajectoires import Trajectoire
    from viscocrowd.scenarios.experience import _configuration_effective, _evenements_piscine
    from viscocrowd.scenarios.piscine import NOMS_ETATS, ParametresPiscine, simuler_piscine

    if configuration.get("scenario") != "piscine":
        raise ValueError("la carte de pression attend une configuration piscine")
    p = ParametresPiscine(**configuration["parametres"], graine=configuration["graine"])
    r = simuler_piscine(p, archiver_tous=archiver_tous, contraintes=True)
    r.projection.verifier_convergence()
    donnees = Trajectoire(
        r.t,
        r.x,
        r.v,
        r.rayons,
        {
            "configuration": _configuration_effective(configuration, p),
            "etats": list(NOMS_ETATS),
            "evenements": _evenements_piscine(r),
        },
        etats=r.etats,
    )
    return donnees, r.contraintes, p.piscine


def ajouter_commande(sous) -> None:
    commande = sous.add_parser(
        "pression",
        help="simule la piscine et montre les forces de contact (chaines de force, arches)",
    )
    commande.add_argument("configuration", type=Path, help="configuration YAML de la piscine")
    commande.add_argument("--gif", type=Path, help="export GIF hors ecran")
    commande.add_argument("--image", type=Path, help="export PNG hors ecran")
    commande.add_argument("--instant", type=float, default=0.0, help="instant du PNG, en s")
    commande.add_argument("--vitesse", type=float, default=4.0, help="facteur de lecture")
    commande.add_argument(
        "--archiver-tous", type=int, default=5, help="un instant sur K pas (defaut : 5)"
    )
    commande.set_defaults(fonction=commande_pression)


def commande_pression(args) -> int:
    import matplotlib

    if args.gif or args.image:
        matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.backends import backend_registry

    from viscocrowd.io.configuration import lire_configuration

    lecteur = None
    try:
        for chemin, extension in ((args.gif, ".gif"), (args.image, ".png")):
            if chemin and (chemin.exists() or chemin.suffix.lower() != extension):
                raise ValueError(f"choisir un nouveau fichier {extension} : {chemin}")
        donnees, contraintes, piscine = simuler_pour_pression(
            lire_configuration(args.configuration), args.archiver_tous
        )
        lecteur = LecteurPression(
            donnees,
            contraintes,
            contre_mur(piscine),
            interactif=not (args.gif or args.image),
            vitesse=args.vitesse,
        )
        print(f"Échelle de couleur (98e centile) : {lecteur.echelle:.2f} m/s²")
        lecteur.aller_au_temps(args.instant)
        paires, lam = lecteur.reseau_a(lecteur.index)
        maximum = f"{lam.max():.1f} m/s²" if lam.size else "—"
        print(
            f"t = {donnees.t[lecteur.index]:.2f} s : {len(paires)} contacts, max {maximum}, "
            f"résidu relatif {lecteur.residu_a(lecteur.index):.2e}"
        )
        if args.image:
            args.image.parent.mkdir(parents=True, exist_ok=True)
            lecteur.figure.savefig(args.image, dpi=140)
            print(f"Image : {args.image}")
        if args.gif:
            args.gif.parent.mkdir(parents=True, exist_ok=True)
            lecteur.exporter_gif(args.gif)
            print(f"Animation : {args.gif}")
        if not (args.gif or args.image):
            if backend_registry.resolve_backend(plt.get_backend())[1] is None:
                raise ValueError("affichage local requis ; utiliser --gif ou --image hors ecran")
            lecteur.basculer()
            plt.show(block=True)
        return 0
    except (OSError, ValueError) as erreur:
        print(f"Carte de pression refusee : {erreur}", file=sys.stderr)
        return 1
    finally:
        if lecteur is not None:
            plt.close(lecteur.figure)
