"""Figure faster-is-slower : relecture des bilans de balayage de la panique."""

import json

import numpy as np
import pytest
from PIL import Image

from viscocrowd.cli import main
from viscocrowd.viz.panique import series_t100

MESURES = ["t50", "t90", "t100", "debit"]


def bilan(t100_mouille, t100_temoin, facteurs=(2.0, 1.0)):
    def lignes(valeurs):
        return [[0.0, 0.0, v, 1.0] for v in valeurs]

    return {
        "parametre": "facteur_vitesse",
        "mesures": MESURES,
        "graines": [1, 2],
        "fixes": {"largeur_porte": 0.8, "dt": 0.005},
        "points": [
            {"valeur": f, "mouille": lignes(m), "temoin": lignes(t)}
            for f, m, t in zip(facteurs, t100_mouille, t100_temoin, strict=True)
        ],
    }


def test_moyennes_ecarts_et_tri_par_facteur():
    facteurs, series = series_t100(bilan([[60, 62], [100, 104]], [[59, 61], [99, 101]]))
    np.testing.assert_array_equal(facteurs, [1.0, 2.0])
    np.testing.assert_allclose(series["mouille"][0], [102, 61])
    np.testing.assert_allclose(series["mouille"][1], [2, 1])
    np.testing.assert_allclose(series["temoin"][0], [100, 60])


def test_les_evacuations_bouchees_sont_comptees_a_part():
    _, series = series_t100(bilan([[60, None], [None, None]], [[59, 61], [99, 101]]))
    moyenne, ecart, bouches = series["mouille"]
    # facteur 1 : aucune terminee ; facteur 2 : une seule, 60 s
    assert np.isnan(moyenne[0]) and moyenne[1] == 60.0 and ecart[1] == 0.0
    np.testing.assert_array_equal(bouches, [2, 1])
    np.testing.assert_array_equal(series["temoin"][2], [0, 0])


def test_figure_avec_evacuations_bouchees(tmp_path):
    chemin = tmp_path / "b.json"
    chemin.write_text(json.dumps(bilan([[60, None], [None, None]], [[59, 61], [99, 101]])))
    assert main(["figure-panique", str(chemin), "--image", str(tmp_path / "b.png")]) == 0


def test_autre_parametre_refuse():
    with pytest.raises(ValueError, match="facteur_vitesse"):
        series_t100(bilan([[1, 1], [1, 1]], [[1, 1], [1, 1]]) | {"parametre": "n_agents"})


def test_commande(tmp_path):
    chemin = tmp_path / "panique.json"
    chemin.write_text(json.dumps(bilan([[60, 62], [100, 104]], [[59, 61], [99, 101]])))
    png = tmp_path / "panique.png"
    assert main(["figure-panique", str(chemin), "--image", str(png)]) == 0
    with Image.open(png) as image:
        assert image.format == "PNG"
    assert main(["figure-panique", str(chemin), "--image", str(png)]) == 1


def test_fusion_des_bilans_d_une_meme_campagne():
    from viscocrowd.viz.panique import fusionner

    a = bilan([[60, 62]], [[59, 61]], facteurs=(1.0,))
    b = bilan([[50, 52]], [[49, 51]], facteurs=(2.0,))
    facteurs, series = series_t100(fusionner([b, a]))
    np.testing.assert_array_equal(facteurs, [1.0, 2.0])
    np.testing.assert_allclose(series["mouille"][0], [61, 51])
    with pytest.raises(ValueError, match="deux bilans"):
        fusionner([a, a])
    with pytest.raises(ValueError, match="graines"):
        fusionner([a, b | {"graines": [7]}])


def test_commande_fusionne_par_etiquette(tmp_path):
    chemins = []
    for k, f in enumerate((1.0, 2.0)):
        chemin = tmp_path / f"b{k}.json"
        chemin.write_text(json.dumps(bilan([[60, 62]], [[59, 61]], facteurs=(f,))))
        chemins.append(str(chemin))
    png = tmp_path / "fusion.png"
    args = ["figure-panique", *chemins, "--etiquettes", "serie", "serie", "--image", str(png)]
    assert main(args) == 0
