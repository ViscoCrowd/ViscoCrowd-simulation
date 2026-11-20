"""Comparer 2 a 4 variantes d'une configuration piscine dans un meme GIF."""

import matplotlib

matplotlib.use("Agg")
import numpy as np
import pytest
from PIL import Image

from utilitaires import piscine_reduite, simuler_archive_reduite
from viscocrowd.cli import main
from viscocrowd.io.trajectoires import lire_trajectoire
from viscocrowd.viz.duel import exporter_comparaison, instants_communs, instants_communs_n


def test_instants_communs_n_suit_la_plus_longue():
    np.testing.assert_allclose(
        instants_communs_n([2.0, 4.0, 3.0], fps=2, vitesse=2.0),
        instants_communs(2.0, 4.0, fps=2, vitesse=2.0),
    )


@pytest.fixture(scope="module")
def archive(tmp_path_factory):
    dossier = tmp_path_factory.mktemp("variantes")
    return lire_trajectoire(simuler_archive_reduite(dossier / "a.npz", duree=1.0))


@pytest.mark.parametrize("n", [1, 5])
def test_nombre_de_vues_refuse(n, archive, tmp_path):
    with pytest.raises(ValueError, match="2 a 4"):
        exporter_comparaison([archive] * n, ["v"] * n, tmp_path / "x.gif")


def test_quatre_vues_en_deux_colonnes(archive, tmp_path):
    deux, quatre = tmp_path / "deux.gif", tmp_path / "quatre.gif"
    exporter_comparaison([archive] * 2, ["a", "b"], deux, vitesse=4.0)
    exporter_comparaison([archive] * 4, ["a", "b", "c", "d"], quatre, vitesse=4.0)
    with Image.open(deux) as a, Image.open(quatre) as b:
        assert b.width == 2 * a.width and b.height == a.height


def test_commande_trois_variantes(tmp_path, capsys):
    gif = tmp_path / "v.gif"
    commande = ["comparer-variantes", str(piscine_reduite(tmp_path, duree=1.0)), "--gif", str(gif)]
    for valeur in ("3.3", "2", "1"):
        commande += ["--variante", f"adherence_mouille={valeur}"]
    assert main(commande) == 0
    with Image.open(gif) as image:
        assert image.n_frames > 1
    sortie = capsys.readouterr().out
    assert "adherence_mouille=1" in sortie


def test_commande_refuse_une_seule_variante(tmp_path, capsys):
    commande = [
        "comparer-variantes",
        str(piscine_reduite(tmp_path)),
        "--gif",
        str(tmp_path / "v.gif"),
    ]
    assert main([*commande, "--variante", "n_agents=4"]) == 1
    assert "2 a 4" in capsys.readouterr().err
