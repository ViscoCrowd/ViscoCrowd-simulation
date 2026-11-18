"""Pose longue : toutes les trajectoires d'une archive piscine en une image, sans simulation."""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import numpy as np
import pytest
from PIL import Image

from viscocrowd.cli import main
from viscocrowd.io.configuration import lire_configuration
from viscocrowd.io.trajectoires import Trajectoire, ecrire_trajectoire
from viscocrowd.scenarios.piscine import (
    EAU,
    FRANCHISSEMENT,
    NOMS_ETATS,
    PLAGE,
    SORTI,
    ParametresPiscine,
)
from viscocrowd.viz.pose_longue import segments_actifs


def test_les_sauts_de_franchissement_et_de_sortie_ne_sont_pas_traces():
    """Agent 0 : eau, eau, bord, plage, plage, sorti. Seuls eau->eau et plage->plage restent."""
    x = np.array([[[0, 0]], [[1, 0]], [[5, 5]], [[9, 9]], [[10, 9]], [[50, 10]]], dtype=float)
    v = np.zeros_like(x)
    v[:, 0, 0] = [1.0, 2.0, 0.0, 3.0, 4.0, 0.0]
    etats = np.array([[EAU], [EAU], [FRANCHISSEMENT], [PLAGE], [PLAGE], [SORTI]])
    segments, vitesses = segments_actifs(x, v, etats)
    np.testing.assert_array_equal(segments, [[[0, 0], [1, 0]], [[9, 9], [10, 9]]])
    np.testing.assert_array_equal(vitesses, [1.0, 3.0])


def test_le_pas_saute_des_instants():
    x = np.arange(10, dtype=float).reshape(5, 1, 2)
    etats = np.full((5, 1), PLAGE)
    segments, _ = segments_actifs(x, np.zeros_like(x), etats, pas=2)
    assert segments.shape == (2, 2, 2)
    np.testing.assert_array_equal(segments[0], x[[0, 2], 0])


@pytest.mark.parametrize("pas", [0, -1, 1.5])
def test_pas_invalide(pas):
    x = np.zeros((3, 1, 2))
    with pytest.raises(ValueError, match="pas"):
        segments_actifs(x, x, np.zeros((3, 1), dtype=int), pas)


def _archive_deux_agents(tmp_path):
    """Archive piscine de deux agents sur la plage, ecrite sans simulation."""
    config = lire_configuration(Path(__file__).parents[1] / "experiments/piscine.yaml")
    config["parametres"]["n_agents"] = 2
    p = ParametresPiscine(**config["parametres"], graine=config["graine"])
    t = np.linspace(0.0, 4.0, 5)
    x = np.stack([[[30 + 4 * k, 10], [30 + 3 * k, 8]] for k in range(5)]).astype(float)
    archive = tmp_path / "piscine.npz"
    ecrire_trajectoire(
        archive,
        Trajectoire(
            t,
            x,
            np.full_like(x, 1.0),
            np.full(2, p.rayon),
            {
                "configuration": config,
                "etats": list(NOMS_ETATS),
                "evenements": {"sorties": [None, None]},
            },
            etats=np.full((5, 2), PLAGE),
        ),
    )
    return archive


def test_titre_et_pied_d_image(tmp_path):
    """Le sous-titre est remplace par son nom, et le pied d'image n'est plus « a valider »."""
    import matplotlib.pyplot as plt

    from viscocrowd.io.trajectoires import lire_trajectoire
    from viscocrowd.viz.pose_longue import figure_pose_longue

    figure = figure_pose_longue(lire_trajectoire(_archive_deux_agents(tmp_path)))
    try:
        textes = [texte.get_text() for texte in figure.texts]
        assert "ÉVACUATION PISCINE  /  POSE LONGUE" in textes
        assert "ÉVACUATION PISCINE  /  RELECTURE" not in textes
        assert not any("à valider" in texte for texte in textes)
        assert any("facteur de panique 1.5" in texte for texte in textes)
    finally:
        plt.close(figure)


def test_commande_png_et_refus_d_ecrasement(tmp_path, monkeypatch):
    def interdit(*args, **kwargs):
        raise AssertionError("aucune simulation pour une pose longue")

    monkeypatch.setattr("viscocrowd.scenarios.piscine.simuler_piscine", interdit)
    archive = _archive_deux_agents(tmp_path)
    png = tmp_path / "pose.png"
    args = ["pose-longue", str(archive), "--image", str(png)]
    assert main(args) == 0
    with Image.open(png) as image:
        assert image.format == "PNG" and image.width > 1000
    original = png.read_bytes()
    assert main(args) == 1
    assert png.read_bytes() == original
    assert main(["pose-longue", str(archive), "--image", str(tmp_path / "pose.jpg")]) == 1
