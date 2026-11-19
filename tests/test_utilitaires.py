"""Utilitaires de test partages : configurations reduites de la piscine."""

from utilitaires import (
    EXEMPLE,
    EXEMPLE_GOULOT,
    parametres_reduits,
    piscine_reduite,
    reference,
    simuler_archive_reduite,
)
from viscocrowd.io.configuration import lire_configuration
from viscocrowd.io.trajectoires import lire_trajectoire


def test_exemples_existent():
    assert EXEMPLE.name == "piscine.yaml" and EXEMPLE.exists()
    assert EXEMPLE_GOULOT.name == "goulot.yaml" and EXEMPLE_GOULOT.exists()


def test_reference_est_la_table_des_parametres():
    assert reference() == lire_configuration(EXEMPLE)["parametres"]


def test_parametres_reduits_par_defaut():
    p = parametres_reduits()
    assert p.n_agents == 6 and p.duree == 10.0
    assert p.graine == lire_configuration(EXEMPLE)["graine"]


def test_geometrie_fusionnee_et_non_remplacee():
    p = parametres_reduits(geometrie={"largeur_porte": 0.9}, n_agents=8)
    assert p.piscine.largeur_porte == 0.9
    assert p.piscine.longueur_bassin == reference()["geometrie"]["longueur_bassin"]
    assert p.n_agents == 8


def test_piscine_reduite_ecrit_un_yaml_lisible(tmp_path):
    chemin = piscine_reduite(tmp_path, n_agents=4)
    assert chemin == tmp_path / "piscine.yaml"
    config = lire_configuration(chemin)
    assert config["scenario"] == "piscine"
    assert config["parametres"]["n_agents"] == 4 and config["parametres"]["duree"] == 10.0


def test_simuler_archive_reduite(tmp_path):
    archive = simuler_archive_reduite(tmp_path / "a.npz", duree=1.0)
    donnees = lire_trajectoire(archive)
    assert donnees.x.shape[1] == 6 and donnees.t[-1] <= 1.0 + 1e-9
