"""Duel : deux evacuations de piscine rejouees ensemble, mouillee contre temoin sec."""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import numpy as np
import pytest
import yaml
from PIL import Image

from viscocrowd.cli import main
from viscocrowd.io.configuration import lire_configuration
from viscocrowd.io.trajectoires import Trajectoire
from viscocrowd.scenarios.piscine import NOMS_ETATS, PLAGE, SORTI
from viscocrowd.viz.duel import configuration_temoin, exporter_duel, instants_communs

EXEMPLE = Path(__file__).parents[1] / "experiments/piscine.yaml"


def archive(fin: float) -> Trajectoire:
    """Deux agents sur la plage ; le premier sort a `fin`."""
    config = lire_configuration(EXEMPLE)
    config["parametres"]["n_agents"] = 2
    x = np.array([[[40, 10], [35, 8]], [[48.5, 10], [36, 8]]], dtype=float)
    return Trajectoire(
        np.array([0.0, fin]),
        x,
        np.zeros_like(x),
        np.full(2, config["parametres"]["rayon"]),
        {
            "configuration": config,
            "etats": list(NOMS_ETATS),
            "evenements": {"sorties": [fin, None]},
        },
        etats=np.array([[PLAGE, PLAGE], [SORTI, PLAGE]]),
    )


def test_les_instants_couvrent_la_plus_longue_evacuation():
    instants = instants_communs(10.0, 12.5, fps=2, vitesse=4.0)
    np.testing.assert_allclose(instants, [0, 2, 4, 6, 8, 10, 12, 12.5])


@pytest.mark.parametrize(("fps", "vitesse"), [(0, 1.0), (1.5, 1.0), (10, 0.0), (10, np.nan)])
def test_instants_parametres_invalides(fps, vitesse):
    with pytest.raises(ValueError, match="fps et vitesse"):
        instants_communs(1.0, 1.0, fps, vitesse)


def test_le_temoin_seche_tout_le_sol_et_garde_le_reste():
    config = lire_configuration(EXEMPLE)
    sec = configuration_temoin(config)
    p, q = config["parametres"], sec["parametres"]
    assert q["geometrie"]["largeur_mouillee"] == 0.0
    assert q["parametres_milieux"]["MOUILLE"] == p["parametres_milieux"]["SEC"]
    assert sec["graine"] == config["graine"]
    assert q["n_agents"] == p["n_agents"] and q.get("chutes") == p.get("chutes")
    assert config["parametres"]["geometrie"]["largeur_mouillee"] > 0  # original intact


def test_le_temoin_refuse_un_autre_scenario():
    with pytest.raises(ValueError, match="piscine"):
        configuration_temoin({"scenario": "couloir", "parametres": {}})


def test_gif_empile_les_deux_vues_et_fige_la_plus_courte(tmp_path):
    gif = tmp_path / "duel.gif"
    images = exporter_duel([archive(2.0), archive(4.0)], ["A", "B"], gif, fps=2, vitesse=2.0)
    assert images == 5  # 0, 1, 2, 3, 4 s : la vue A reste sur son dernier instant
    # Pillow fusionne les images identiques consecutives (les deux vues figees) en
    # allongeant leur duree : c'est la duree totale qui doit faire 5 x 500 ms.
    with Image.open(gif) as film:
        duree = 0
        for k in range(film.n_frames):
            film.seek(k)
            duree += film.info["duration"]
        largeur, hauteur = film.size
    assert duree == 2500
    assert largeur == 720 and hauteur == 2 * round(0.88 * 420)


def test_commande_complete_garde_les_archives_et_refuse_d_ecraser(tmp_path):
    config = lire_configuration(EXEMPLE)
    config["parametres"] |= {"n_agents": 3, "duree": 60.0}
    yaml_petit = tmp_path / "petit.yaml"
    yaml_petit.write_text(yaml.safe_dump(config))
    gif, archives = tmp_path / "duel.gif", tmp_path / "archives"
    args = [
        "duel",
        str(yaml_petit),
        "--gif",
        str(gif),
        "--vitesse",
        "40",
        "--garder",
        str(archives),
    ]
    assert main(args) == 0
    assert (archives / "haut.npz").exists() and (archives / "bas.npz").exists()
    with Image.open(gif) as film:
        assert film.n_frames >= 2
    original = gif.read_bytes()
    assert main(args) == 1
    assert gif.read_bytes() == original
