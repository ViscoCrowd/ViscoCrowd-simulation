"""Menu de parametrage : questions, valeurs de reference par defaut, lancement."""

import pytest

from utilitaires import EXEMPLE, piscine_reduite, reference
from viscocrowd.cli import main
from viscocrowd.io.configuration import lire_configuration
from viscocrowd.io.trajectoires import lire_trajectoire
from viscocrowd.scenarios.balayage_piscine import appliquer_fixes
from viscocrowd.ui.lanceur import PREREGLAGES, QUESTIONS, demander, valeur_actuelle


def repondre(*reponses):
    suite = iter(reponses)
    return lambda _invite: next(suite)


def test_questions_portent_sur_des_parametres_connus():
    assert [q.nom for q in QUESTIONS] == [
        "n_agents",
        "echelles",
        "largeur_porte",
        "facteur_vitesse",
        "largeur_mouillee",
    ]


def test_valeur_actuelle_compte_les_echelles_d_une_liste():
    assert valeur_actuelle(reference(), "echelles") == 2
    assert valeur_actuelle(reference(), "largeur_porte") == 1.2


def test_reponse_vide_garde_la_reference():
    assert demander(reference(), lire=repondre("", "", "", "", ""), ecrire=lambda _: None) == {}


def test_saisie_invalide_reposee_puis_acceptee():
    fixes = demander(
        reference(), lire=repondre("150", "", "abc", "0.8", "", ""), ecrire=lambda _: None
    )
    assert fixes == {"n_agents": 150, "largeur_porte": 0.8}
    assert type(fixes["n_agents"]) is int


def test_trois_saisies_invalides_abandonnent():
    with pytest.raises(ValueError, match="saisies invalides"):
        demander(reference(), lire=lambda _: "abc", ecrire=lambda _: None)


def test_la_question_affiche_la_reference():
    vus = []
    demander(reference(), lire=repondre("", "", "", "", ""), ecrire=vus.append)
    assert any("Baigneurs" in ligne and "100" in ligne for ligne in vus)


def test_prereglage_olympique():
    parametres = appliquer_fixes(reference(), PREREGLAGES["olympique"])
    assert parametres["geometrie"]["longueur_bassin"] == 50.0
    assert parametres["geometrie"]["largeur_bassin"] == 25.0
    assert parametres["n_agents"] == 200


def test_menu_ecrit_configuration_et_archive(tmp_path, monkeypatch):
    monkeypatch.setattr("builtins.input", repondre("4", "", "0.9", "", ""))
    config = piscine_reduite(tmp_path, duree=1.0)
    assert main(["menu", str(config), "--dossier", str(tmp_path / "s"), "--sans-relecture"]) == 0
    (lancement,) = (tmp_path / "s").iterdir()
    effective = lire_configuration(lancement / "configuration.yaml")["parametres"]
    assert effective["n_agents"] == 4 and effective["geometrie"]["largeur_porte"] == 0.9
    assert lire_trajectoire(lancement / "trajectoire.npz").x.shape[1] == 4


def test_menu_refuse_une_population_trop_grande(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr("builtins.input", repondre("100000", "", "", "", ""))
    commande = ["menu", str(EXEMPLE), "--dossier", str(tmp_path), "--sans-relecture"]
    assert main(commande) == 1
    assert "loge" in capsys.readouterr().err


def test_retaper_la_reference_ne_surcharge_pas():
    fixes = demander(reference(), lire=repondre("100", "2", "1.2", "", ""), ecrire=lambda _: None)
    assert fixes == {}


def test_la_bande_mouillee_affiche_la_longueur_de_la_plage():
    vus = []
    demander(reference(), lire=repondre("", "", "", "", ""), ecrire=vus.append)
    plage = reference()["geometrie"]["plage_sortie"]
    assert any(
        "Bande mouillée" in ligne and f"{plage:g} = jusqu'à la porte" in ligne for ligne in vus
    )


@pytest.mark.parametrize("erreur", [EOFError, KeyboardInterrupt])
def test_menu_abandonne_proprement(erreur, tmp_path, monkeypatch, capsys):
    def interrompre(_invite):
        raise erreur

    monkeypatch.setattr("builtins.input", interrompre)
    assert main(["menu", str(EXEMPLE), "--dossier", str(tmp_path), "--sans-relecture"]) == 1
    assert "Menu abandonné" in capsys.readouterr().err
