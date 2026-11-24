"""Relecture piscine avec le diagramme fondamental devant la porte, synchronise."""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image

from viscocrowd.cli import main
from viscocrowd.io.configuration import lire_configuration
from viscocrowd.io.trajectoires import Trajectoire, ecrire_trajectoire
from viscocrowd.scenarios.diagramme_piscine import zone_porte
from viscocrowd.scenarios.piscine import NOMS_ETATS, PLAGE, ParametresPiscine
from viscocrowd.viz.diagramme_anime import LecteurDiagramme

EXEMPLE = Path(__file__).parents[1] / "experiments/piscine.yaml"


def archive():
    """Deux agents ; le premier, hors de la salle de mesure, entre dans la zone a t = 3 s."""
    config = lire_configuration(EXEMPLE)
    config["parametres"]["n_agents"] = 2
    p = ParametresPiscine(**config["parametres"], graine=config["graine"])
    zone = zone_porte(p.piscine)
    yc = 0.5 * (zone.y_min + zone.y_max)
    t = np.arange(0.0, 6.01, 0.5)
    x0 = np.where(t < 3.0, zone.x_min - 12.0 + 0.5 * t, zone.x_min + 0.5 * (t - 3.0) + 0.1)
    x = np.stack([np.column_stack((x0, np.full_like(t, yc))), np.tile([34.0, 4.0], (len(t), 1))], 1)
    return Trajectoire(
        t,
        x,
        np.zeros_like(x),
        np.full(2, p.rayon),
        {
            "configuration": config,
            "etats": list(NOMS_ETATS),
            "evenements": {"sorties": [None, None]},
        },
        etats=np.full((len(t), 2), PLAGE),
    )


def test_le_point_suit_la_mesure_de_la_zone_et_s_efface_quand_elle_est_vide():
    vue = LecteurDiagramme(archive(), interactif=False, pas_mesure=1)
    try:
        vue.aller_au_temps(1.0)
        assert vue.mesure.get_text() == "zone vide"
        assert len(vue.point.get_xdata()) == 0
        vue.aller_au_temps(4.0)
        rho, j = vue.point.get_xdata()[0], vue.point.get_ydata()[0]
        k = np.searchsorted(vue.serie.t, 4.0, side="right") - 1
        assert rho == vue.serie.densite[k] > 0
        assert j == vue.serie.debit[k]
        assert "pers/m²" in vue.mesure.get_text()
        # Trainee : les points des 2 dernieres secondes, instant courant compris.
        attendus = np.sum((vue.serie.t <= 4.0) & (vue.serie.t > 2.0))
        assert len(vue.trainee.get_xdata()) == attendus == 3  # 3, 3,5 et 4 s
    finally:
        plt.close(vue.figure)


def test_exports_png_gif_et_refus(tmp_path):
    chemin = tmp_path / "piscine.npz"
    ecrire_trajectoire(chemin, archive())
    png, gif = tmp_path / "fd.png", tmp_path / "fd.gif"
    args = ["diagramme-anime", str(chemin), "--image", str(png), "--gif", str(gif)]
    assert main([*args, "--instant", "4", "--vitesse", "10"]) == 0
    with Image.open(png) as image:
        assert image.format == "PNG" and image.width > 1000
    with Image.open(gif) as film:
        assert film.format == "GIF"
    original = png.read_bytes()
    assert main(args) == 1
    assert png.read_bytes() == original
