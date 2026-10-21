"""Sol mouille, un parametre a la fois : chaque variante isole bien un mecanisme."""

from dataclasses import asdict
from pathlib import Path

import pytest
import yaml

from viscocrowd.cli import main
from viscocrowd.io.configuration import lire_configuration
from viscocrowd.model.milieu import ParametresMilieu
from viscocrowd.scenarios.comparaison_mouille import (
    MESURES,
    VARIANTES,
    ProtocoleIncomplet,
    comparer,
    mesurer,
    mouille_de_variante,
)
from viscocrowd.scenarios.couloir import ParametresCouloir

EXEMPLE = Path(__file__).parents[1] / "experiments/couloir.yaml"
SEC = ParametresMilieu(relaxation=0.3, acceleration_max=3.0, vitesse=1.5)
MOUILLE = ParametresMilieu(relaxation=0.6, acceleration_max=0.7, vitesse=1.0)


@pytest.mark.parametrize("nom", list(VARIANTES))
def test_chaque_variante_ne_reprend_que_ses_parametres(nom):
    variante = asdict(mouille_de_variante(nom, SEC, MOUILLE))
    for champ, valeur in variante.items():
        attendu = getattr(MOUILLE if champ in VARIANTES[nom] else SEC, champ)
        assert valeur == attendu


def test_variante_inconnue_refusee():
    with pytest.raises(ValueError, match="variante inconnue"):
        mouille_de_variante("glace", SEC, MOUILLE)


@pytest.fixture(scope="module")
def banc():
    """Le demonstrateur complet (24 agents), pour sa graine : 6 simulations, ~3 s."""
    config = lire_configuration(EXEMPLE)
    resultats = comparer(config, [config["graine"]])
    return {nom: dict(zip(MESURES, valeurs[0], strict=True)) for nom, valeurs in resultats.items()}


def test_relaxation_ou_adherence_seule_sans_effet_a_vitesse_constante(banc):
    """tau et a_max n'agissent que si la vitesse doit changer : ici, elle ne change pas."""
    reference = banc["reference"]
    for nom in ("relaxation", "adherence"):
        assert abs(banc[nom]["t50"] - reference["t50"]) < 0.01  # mesure : 0,001 s au plus
        assert banc[nom]["contacts"] == 0.0
    assert reference["contacts"] == 0.0


def test_seule_la_vitesse_souhaitee_retarde_et_comprime(banc):
    retard = banc["vitesse"]["t50"] - banc["reference"]["t50"]
    # Mesure : 1,29 s, sous le retard en vitesse etablie (4 / 1 - 4 / 1,5 = 1,33 s).
    assert 1.0 < retard < 4.0 / 1.0 - 4.0 / 1.5
    assert banc["vitesse"]["contacts"] > 30.0  # mesure : 65 paires.s


def test_l_inertie_allonge_le_freinage_et_reduit_la_compression(banc):
    """Moins d'adherence, puis une relaxation plus lente : on freine plus loin, on se tasse moins."""
    freinage = [banc[n]["freinage"] for n in ("vitesse", "vitesse+adherence", "complet")]
    contacts = [banc[n]["contacts"] for n in ("vitesse", "vitesse+adherence", "complet")]
    assert freinage[0] < freinage[1] < freinage[2]  # mesure : 0,53 ; 0,73 ; 1,86 m
    assert contacts[0] > contacts[1] > contacts[2]  # mesure : 65 ; 63 ; 55 paires.s
    assert banc["complet"]["t50"] < banc["vitesse"]["t50"]  # traverse plus vite, avec son elan


def _petit_banc(**changements):
    """Six agents, pour les contrats ; la duree par defaut laisse finir le protocole."""
    config = lire_configuration(EXEMPLE)
    config["parametres"].update({"n_agents": 6, "colonnes": 3, "duree": 12.0} | changements)
    return config


@pytest.mark.parametrize(("facteur", "duree"), [(0.5, 26.0), (2.0, 8.0)])
def test_le_freinage_vise_la_consigne_reelle_du_moteur(facteur, duree):
    """Revue #50 : le moteur vise facteur x s ; le seuil de freinage aussi.

    Facteur 0,5 : on entre a 0,75 m/s vers 0,5 m/s, il faut freiner (l'ancien seuil
    de 1,05 m/s declarait l'agent deja freine). Facteur 2 : on entre a 3 m/s vers
    2 m/s, l'ancien seuil n'etait jamais atteint.
    """
    base = _petit_banc(facteur_vitesse=facteur, duree=duree)["parametres"]

    def freinage(variante):
        p = ParametresCouloir(
            **(
                base
                | {
                    "parametres_milieux": {
                        "SEC": SEC,
                        "MOUILLE": mouille_de_variante(variante, SEC, MOUILLE),
                    }
                }
            ),
            graine=1,
        )
        return mesurer(p)["freinage"]

    assert freinage("vitesse") > 0.1  # il faut bien ralentir de 0,25 ou 1 m/s
    assert freinage("reference") < 0.05  # rien a freiner quand le mouille egale le sec


def test_freinage_plus_long_que_la_bande_refuse():
    """Facteur 2, adherence et relaxation du mouille : on ne revient pas a 2 m/s en 4 m."""
    p = ParametresCouloir(
        **(
            _petit_banc(facteur_vitesse=2.0, duree=8.0)["parametres"]
            | {"parametres_milieux": {"SEC": SEC, "MOUILLE": MOUILLE}}
        ),
        graine=1,
    )
    with pytest.raises(ProtocoleIncomplet, match="plus long que la bande"):
        mesurer(p)


def test_duree_insuffisante_refusee_sans_figure(tmp_path, capsys):
    """Revue #50 : pas de moyenne silencieuse sur les seuls agents arrives."""
    config = _petit_banc(duree=5.0)
    with pytest.raises(ProtocoleIncomplet, match="allonger la duree"):
        comparer(config, [1])
    fichier = tmp_path / "court.yaml"
    fichier.write_text(yaml.safe_dump(config))
    assert (
        main(["comparer-mouille", str(fichier), "--graines", "1", "--figure", str(tmp_path)]) == 1
    )
    assert "allonger la duree" in capsys.readouterr().err
    assert not (tmp_path / "fig07_mouille_un_parametre.png").exists()


@pytest.mark.parametrize(
    ("frontieres", "milieux"),
    [
        ([3.0, 5.0, 7.0, 9.0], ["SEC", "MOUILLE", "SEC", "MOUILLE", "SEC"]),  # deux bandes
        ([4.0, 8.0], ["SEC", "MOUILLE", "EAU"]),  # pas encadree de sec
    ],
)
def test_protocole_hors_domaine_refuse(frontieres, milieux):
    config = _petit_banc(frontieres=frontieres, milieux=milieux)
    config["parametres"]["parametres_milieux"]["EAU"] = {
        "relaxation": 0.3,
        "acceleration_max": 3.0,
        "vitesse": 0.5,
    }
    with pytest.raises(ValueError, match="MOUILLE"):
        comparer(config, [1])


def test_configuration_sans_bande_mouillee_refusee():
    config = lire_configuration(EXEMPLE)
    config["parametres"].update(frontieres=[], milieux=["SEC"])
    with pytest.raises(ValueError, match="MOUILLE"):
        comparer(config, [1])
    with pytest.raises(ValueError, match="graine"):
        comparer(lire_configuration(EXEMPLE), [])


def test_commande_tableau_et_figure(tmp_path, capsys):
    config = lire_configuration(EXEMPLE)
    config["parametres"].update(n_agents=6, colonnes=3, duree=10.0)
    fichier = tmp_path / "petit.yaml"
    fichier.write_text(yaml.safe_dump(config))
    assert (
        main(["comparer-mouille", str(fichier), "--graines", "1", "2", "--figure", str(tmp_path)])
        == 0
    )
    sortie = capsys.readouterr().out
    assert all(nom in sortie for nom in VARIANTES)
    assert (tmp_path / "fig07_mouille_un_parametre.png").stat().st_size > 0


def test_commande_refuse_un_autre_scenario(capsys):
    racine = Path(__file__).parents[1]
    assert main(["comparer-mouille", str(racine / "experiments/tassement.yaml")]) == 1
    assert "couloir" in capsys.readouterr().err
