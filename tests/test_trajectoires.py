"""Une archive corrompue doit echouer avant de produire un observable."""

import numpy as np
import pytest

from viscocrowd.io.trajectoires import Trajectoire, ecrire_trajectoire, lire_trajectoire


def contenu():
    return {
        "version": np.array(1),
        "t": np.array([0.0, 0.1]),
        "x": np.zeros((2, 1, 2)),
        "v": np.zeros((2, 1, 2)),
        "rayons": np.array([0.1]),
        "metadonnees": np.array('{"graine": 7}'),
    }


@pytest.mark.parametrize(
    ("cle", "valeur"),
    [
        ("version", np.array(2)),
        ("version", np.array(True)),
        ("t", np.array([0.0, 0.0])),
        ("t", np.array([0.0, np.nan])),
        ("t", np.array([])),
        ("x", np.zeros((2, 2))),
        ("x", np.full((2, 1, 2), np.inf)),
        ("v", np.zeros((2, 2, 2))),
        ("rayons", np.array([-1.0])),
        ("rayons", np.ones(2)),
        ("metadonnees", np.array("[]")),
        ("metadonnees", np.array('{"x": NaN}')),
        ("x", np.array([object()], dtype=object)),
        ("etats", np.zeros((2, 2), dtype=np.int64)),  # forme (P, N) attendue : (2, 1)
        ("etats", np.zeros((2, 1))),  # codes flottants
        ("etats", np.array([[0], [-1]])),  # code negatif
        ("champ_inconnu", np.zeros(1)),
    ],
)
def test_archive_invalide_refusee(tmp_path, cle, valeur):
    archive = contenu()
    archive[cle] = valeur
    fichier = tmp_path / "invalide.npz"
    np.savez(fichier, **archive)
    with pytest.raises(ValueError):
        lire_trajectoire(fichier)


def test_champ_manquant_refuse(tmp_path):
    archive = contenu()
    del archive["x"]
    fichier = tmp_path / "incomplete.npz"
    np.savez(fichier, **archive)
    with pytest.raises(ValueError, match="champs"):
        lire_trajectoire(fichier)


def test_ecriture_controle_les_donnees_avant_de_creer_le_fichier(tmp_path):
    a = contenu()
    donnees = Trajectoire(t=a["t"], x=a["x"], v=a["v"], rayons=a["rayons"], metadonnees={})
    donnees.x[0, 0, 0] = np.nan
    with pytest.raises(ValueError, match="non finies"):
        ecrire_trajectoire(tmp_path / "a.npz", donnees)
    assert not (tmp_path / "a.npz").exists()


def test_etats_facultatifs_relus_a_l_identique(tmp_path):
    a = contenu()
    etats = np.array([[0], [3]])
    donnees = Trajectoire(
        t=a["t"], x=a["x"], v=a["v"], rayons=a["rayons"], metadonnees={}, etats=etats
    )
    ecrire_trajectoire(tmp_path / "avec.npz", donnees)
    np.testing.assert_array_equal(lire_trajectoire(tmp_path / "avec.npz").etats, etats)
    sans = Trajectoire(t=a["t"], x=a["x"], v=a["v"], rayons=a["rayons"], metadonnees={})
    ecrire_trajectoire(tmp_path / "sans.npz", sans)
    assert lire_trajectoire(tmp_path / "sans.npz").etats is None
