"""Trainee d'eau : les baigneurs mouillent la plage, un seul ne suffit pas, beaucoup si."""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import numpy as np
import pytest
import yaml
from PIL import Image

from viscocrowd.cli import main
from viscocrowd.io.configuration import lire_configuration
from viscocrowd.model.carte import CartePiscine
from viscocrowd.model.egouttage import ChampEgouttage, debit_egouttage
from viscocrowd.model.milieu import Milieu
from viscocrowd.scenarios.piscine import ParametresPiscine, simuler_piscine

EXEMPLE = Path(__file__).parents[1] / "experiments/piscine.yaml"
EGOUTTAGE = {"volume": 0.4, "duree": 30.0, "seuil": 0.05, "pas": 0.1}


def parametres(**changements):
    config = lire_configuration(EXEMPLE)
    return ParametresPiscine(**(config["parametres"] | changements), graine=config["graine"])


def tout_sec(x):
    return np.full(len(x), int(Milieu.SEC))


def test_le_depot_conserve_le_volume():
    champ = ChampEgouttage(tout_sec, 10.0, 5.0, 0.25, 0.05)
    x = np.array([[1.0, 1.0], [1.1, 1.05], [7.3, 2.2]])
    champ.deposer(x, np.array([0.01, 0.02, 0.03]))
    assert champ.eau.sum() * 0.25**2 == pytest.approx(0.06)
    assert champ.eau[4, 4] == pytest.approx(0.03 / 0.0625)  # deux depots dans la meme case


def test_seule_une_case_seche_au_dessus_du_seuil_devient_mouillee():
    def carte(x):
        return np.array([int(Milieu.SEC), int(Milieu.EAU), int(Milieu.SEC)])[: len(x)]

    champ = ChampEgouttage(carte, 10.0, 5.0, 0.25, 0.05)
    x = np.array([[1.0, 1.0], [3.0, 1.0], [5.0, 1.0]])
    champ.deposer(x[:2], np.array([0.05 * 0.0625, 1.0]))  # juste au seuil, et beaucoup
    champ.deposer(x[2:], np.array([0.049 * 0.0625]))  # juste sous le seuil
    np.testing.assert_array_equal(champ(x), [Milieu.MOUILLE, Milieu.EAU, Milieu.SEC])


def test_l_egouttage_rend_tout_le_volume():
    t = np.linspace(0.0, 600.0, 600_001)
    debit = debit_egouttage(0.4, 30.0, t)
    assert np.trapezoid(debit, t) == pytest.approx(0.4, rel=1e-6)
    assert debit[0] == pytest.approx(0.4 / 30.0)


@pytest.mark.parametrize(
    "egouttage",
    [
        {"volume": 0.4, "duree": 30.0, "seuil": 0.05},
        EGOUTTAGE | {"seuil": 0.0},
        EGOUTTAGE | {"volume": np.nan},
        "oui",
    ],
)
def test_parametres_d_egouttage_invalides(egouttage):
    with pytest.raises(ValueError, match="egouttage"):
        parametres(egouttage=egouttage)


def test_sans_egouttage_rien_n_est_enregistre():
    r = simuler_piscine(parametres(n_agents=3, duree=40.0))
    assert r.eau_sol is None and r.fraction_mouillee is None


def test_un_baigneur_seul_ne_mouille_rien_trente_mouillent_leur_chemin():
    """L'intuition du module : une trace isolee reste sous le seuil, des traces superposees non.

    Un baigneur seul depasse le seuil a un seul endroit : la ou il sort de l'eau, pose a
    l'arret et encore lent (0,07 L/m^2). C'est dans la bande deja mouillee du bassin ;
    sur la plage seche, sa trace reste sous le seuil.
    """
    p = parametres(n_agents=1, duree=60.0, egouttage=EGOUTTAGE)
    seul = simuler_piscine(p)
    champ = ChampEgouttage(tout_sec, 1.0, 1.0, EGOUTTAGE["pas"], EGOUTTAGE["seuil"])
    champ.eau = seul.eau_sol[-1]
    sec = CartePiscine(p.piscine)(champ.centres().reshape(-1, 2)).reshape(champ.eau.shape) == (
        Milieu.SEC
    )
    assert champ.eau[sec].max() > 0
    assert champ.eau[sec].max() < EGOUTTAGE["seuil"]
    assert seul.fraction_mouillee[-1] == 0.0

    foule = simuler_piscine(parametres(n_agents=30, duree=90.0, egouttage=EGOUTTAGE))
    assert foule.fraction_mouillee[-1] > 0.01
    assert np.all(np.diff(foule.fraction_mouillee) >= 0)  # l'eau ne seche pas
    depose = foule.eau_sol[-1].sum() * EGOUTTAGE["pas"] ** 2
    assert 0 < depose < 30 * EGOUTTAGE["volume"]
    assert foule.violation_paroi_max() <= 1e-14


def test_commande_png_et_configuration_sans_egouttage_refusee(tmp_path):
    config = lire_configuration(EXEMPLE)
    config["parametres"] |= {"n_agents": 4, "duree": 60.0}
    sans = tmp_path / "sans.yaml"
    sans.write_text(yaml.safe_dump(config))
    config["parametres"]["egouttage"] = EGOUTTAGE
    avec = tmp_path / "avec.yaml"
    avec.write_text(yaml.safe_dump(config))
    png = tmp_path / "trainee.png"
    assert main(["trainee", str(sans), "--image", str(png)]) == 1
    assert main(["trainee", str(avec), "--image", str(png), "--instant", "20"]) == 0
    with Image.open(png) as image:
        assert image.format == "PNG" and image.width > 1000


def _film_d_un_passage(pas: float) -> np.ndarray:
    """Un baigneur seul traverse 3 m de plage seche a 2 m/s, juste apres sa sortie de l'eau."""
    q, v, dt, rayon = 0.4 / 30.0, 2.0, 0.01, 0.2
    champ = ChampEgouttage(tout_sec, 4.0, 2.0, pas, 0.05)
    for k in range(150):
        x = np.array([[0.5 + v * dt * k, 1.0]])
        champ.deposer(x, np.array([q * dt]), rayons=np.array([rayon]))
    return champ.eau


def test_film_independant_de_la_taille_des_cases():
    """Revue de #165 : le film ne doit pas dependre de `pas`, un parametre numerique.

    Deposer tout le volume d'un pas sur la seule case sous le centre donnait un film en
    q / (v pas) : 0,027 L/m^2 a 0,25 m, mais 0,053 a 0,125 m. Reparti sur l'empreinte du
    baigneur (disque de rayon r), le film vaut environ 2 q / (pi r v) = 0,021 L/m^2, des
    que la case est assez petite (au plus r / 2, controle par ParametresPiscine).
    """
    grossier, fin = _film_d_un_passage(0.1).max(), _film_d_un_passage(0.05).max()
    assert fin == pytest.approx(grossier, rel=0.1)
    assert grossier == pytest.approx(2 * (0.4 / 30.0) / (np.pi * 0.2 * 2.0), rel=0.3)
    assert grossier < 0.05  # un seul baigneur ne mouille rien, quelle que soit la grille


def test_depot_sur_l_empreinte_conserve_le_volume():
    for pas in (0.25, 0.125, 0.5):
        eau = _film_d_un_passage(pas)
        assert eau.sum() * pas**2 == pytest.approx(150 * 0.01 * 0.4 / 30.0, rel=1e-12)


def test_case_trop_grande_refusee():
    config = lire_configuration(EXEMPLE)
    parametres = config["parametres"] | {"egouttage": EGOUTTAGE | {"pas": 0.25}}
    with pytest.raises(ValueError, match="rayon / 2"):
        ParametresPiscine(**parametres, graine=config["graine"])
