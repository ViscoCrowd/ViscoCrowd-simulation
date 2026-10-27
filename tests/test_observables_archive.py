"""Refus des archives espacees pour les calculs d'observables (issue #73).

Depuis la PR #70, `simuler --archiver-tous K` permet d'alleger les trajectoires piscine en
n'enregistrant qu'une image tous les K pas physiques.
Ce module verifie que toute fonction calculant une observable (debit, franchissement,
sorties definitives, densite et vitesse de Voronoi, energie mecanique) :
  1. Accepte et calcule correctement les grandeurs pour une archive complete (K = 1) ;
  2. Accepte les archives historiques sans cle 'archivage' en considerant K = 1 ;
  3. Refuse explicitement avec ValueError une archive espacee (K >= 2), pour eviter
     les interpolations fausses ou les franchissements manques.
"""

from pathlib import Path

import numpy as np
import pytest
import yaml

from viscocrowd.cli import main
from viscocrowd.io.configuration import lire_configuration
from viscocrowd.io.trajectoires import (
    Trajectoire,
    charger_et_valider_complete,
    ecrire_trajectoire,
)
from viscocrowd.observables import (
    Rectangle,
    debit_specifique,
    debit_specifique_trajectoire,
    densite_comptage,
    densite_comptage_trajectoire,
    densite_voronoi_trajectoire,
    energie_mecanique,
    energie_mecanique_trajectoire,
    franchissements,
    franchissements_trajectoire,
    mesures_voronoi,
    mesures_voronoi_trajectoire,
    serie_densite_comptage_trajectoire,
    sorties_definitives,
    sorties_definitives_trajectoire,
    vitesse_voronoi_trajectoire,
)


def _creer_trajectoire(k: int | None = 1) -> Trajectoire:
    """Cree une trajectoire simple de 2 agents se deplacant vers +x."""
    p = 20
    dt = 0.05
    t = np.arange(p, dtype=float) * dt
    # Agent 0 demarre en (0.5, 2.0), agent 1 en (0.5, 3.0), vitesse vx = 1.0 m/s
    x = np.zeros((p, 2, 2), dtype=float)
    x[:, 0, 0] = 0.5 + t * 1.0
    x[:, 0, 1] = 2.0
    x[:, 1, 0] = 0.5 + t * 1.0
    x[:, 1, 1] = 3.0

    v = np.zeros((p, 2, 2), dtype=float)
    v[:, :, 0] = 1.0

    rayons = np.array([0.2, 0.2])
    metadonnees = {
        "scenario": "test",
        "unites": {"t": "s", "x": "m", "v": "m/s", "rayons": "m"},
    }
    if k is not None:
        metadonnees["archivage"] = {
            "tous_les_pas": k,
            "dt_simulation_s": dt,
            "premier_et_dernier_instants": True,
            "validation_tous_les_pas": True,
        }
    return Trajectoire(t=t, x=x, v=v, rayons=rayons, metadonnees=metadonnees)


def test_proprietes_archive_complete_et_espacee():
    traj_complete = _creer_trajectoire(k=1)
    assert traj_complete.pas_archivage == 1
    assert traj_complete.est_complete is True
    traj_complete.exiger_complete("test")  # ne leve pas

    traj_espacee = _creer_trajectoire(k=2)
    assert traj_espacee.pas_archivage == 2
    assert traj_espacee.est_complete is False
    with pytest.raises(ValueError, match=r"refuse une archive espacee.*tous les 2 pas"):
        traj_espacee.exiger_complete("mon observable")

    traj_leguee = _creer_trajectoire(k=None)
    assert traj_leguee.pas_archivage == 1
    assert traj_leguee.est_complete is True
    traj_leguee.exiger_complete("test")


def test_charger_et_valider_complete(tmp_path):
    fichier_complet = tmp_path / "complet.npz"
    ecrire_trajectoire(fichier_complet, _creer_trajectoire(k=1))

    fichier_espace = tmp_path / "espace.npz"
    ecrire_trajectoire(fichier_espace, _creer_trajectoire(k=5))

    relue = charger_et_valider_complete(fichier_complet)
    assert relue.est_complete is True

    with pytest.raises(ValueError, match=r"refuse une archive espacee.*tous les 5 pas"):
        charger_et_valider_complete(fichier_espace, "verification")

    with pytest.raises(TypeError, match=r"source de trajectoire invalide"):
        charger_et_valider_complete(123)  # type: ignore[arg-type]


class TestConsommateursObservables:
    """Verifie chaque consommateur d'archive sur K=1 (identique) et K=2 (refuse)."""

    a_porte = np.array([1.0, 1.0])
    b_porte = np.array([1.0, 4.0])
    salle = Rectangle(x_min=0.0, x_max=5.0, y_min=0.0, y_max=5.0)
    zone = Rectangle(x_min=0.5, x_max=2.5, y_min=1.0, y_max=4.0)

    def test_debit_et_franchissements(self, tmp_path):
        traj_1 = _creer_trajectoire(k=1)
        traj_2 = _creer_trajectoire(k=2)
        f_direct = franchissements(traj_1.t, traj_1.x, self.a_porte, self.b_porte)
        d_direct = debit_specifique(f_direct, largeur=3.0, debut=0.0, fin=1.0)

        # K = 1 : via objet Trajectoire direct
        f_obj = franchissements(traj_1, self.a_porte, self.b_porte)
        assert f_obj.nombre == f_direct.nombre
        np.testing.assert_array_equal(f_obj.instant, f_direct.instant)

        # K = 1 : via fonction specifique et chemin fichier
        chemin_1 = tmp_path / "traj1.npz"
        ecrire_trajectoire(chemin_1, traj_1)
        f_fichier = franchissements_trajectoire(chemin_1, self.a_porte, self.b_porte)
        assert f_fichier.nombre == f_direct.nombre
        d_fichier = debit_specifique_trajectoire(
            chemin_1, self.a_porte, self.b_porte, largeur=3.0, debut=0.0, fin=1.0
        )
        assert d_fichier == pytest.approx(d_direct)

        # K = 2 : refuse
        chemin_2 = tmp_path / "traj2.npz"
        ecrire_trajectoire(chemin_2, traj_2)
        with pytest.raises(ValueError, match=r"refuse une archive espacee.*tous les 2 pas"):
            franchissements(traj_2, self.a_porte, self.b_porte)
        with pytest.raises(ValueError, match=r"refuse une archive espacee.*tous les 2 pas"):
            franchissements_trajectoire(chemin_2, self.a_porte, self.b_porte)
        with pytest.raises(ValueError, match=r"refuse une archive espacee.*tous les 2 pas"):
            debit_specifique_trajectoire(
                chemin_2, self.a_porte, self.b_porte, largeur=3.0, debut=0.0, fin=1.0
            )

    def test_sorties_definitives(self, tmp_path):
        traj_1 = _creer_trajectoire(k=1)
        traj_2 = _creer_trajectoire(k=2)
        s_direct = sorties_definitives(traj_1.t, traj_1.x, self.a_porte, self.b_porte)

        # K = 1 : via objet direct
        s_obj = sorties_definitives(traj_1, self.a_porte, self.b_porte)
        np.testing.assert_array_equal(s_obj.instant, s_direct.instant)

        # K = 1 : via fichier
        chemin_1 = tmp_path / "sorties1.npz"
        ecrire_trajectoire(chemin_1, traj_1)
        s_fichier = sorties_definitives_trajectoire(chemin_1, self.a_porte, self.b_porte)
        np.testing.assert_array_equal(s_fichier.instant, s_direct.instant)

        # K = 2 : refuse
        chemin_2 = tmp_path / "sorties2.npz"
        ecrire_trajectoire(chemin_2, traj_2)
        with pytest.raises(ValueError, match=r"refuse une archive espacee.*tous les 2 pas"):
            sorties_definitives(traj_2, self.a_porte, self.b_porte)
        with pytest.raises(ValueError, match=r"refuse une archive espacee.*tous les 2 pas"):
            sorties_definitives_trajectoire(chemin_2, self.a_porte, self.b_porte)

    def test_mesures_et_densites_voronoi(self, tmp_path):
        traj_1 = _creer_trajectoire(k=1)
        traj_2 = _creer_trajectoire(k=2)

        # Comparaison directe a l'instant indice 0 (t = 0.0)
        x0, v0 = traj_1.x[0], traj_1.v[0]
        dens_direct, vit_direct = mesures_voronoi(x0, v0, self.salle, self.zone)
        cpt_direct = densite_comptage(x0, self.zone)

        # K = 1 : succes
        d_res, v_res = mesures_voronoi_trajectoire(
            traj_1, self.salle, self.zone, instant=0.0
        )
        assert d_res == pytest.approx(dens_direct)
        assert v_res == pytest.approx(vit_direct)

        assert densite_voronoi_trajectoire(
            traj_1, self.salle, self.zone, indice=0
        ) == pytest.approx(dens_direct)
        assert vitesse_voronoi_trajectoire(
            traj_1, self.salle, self.zone, indice=0
        ) == pytest.approx(vit_direct)
        assert densite_comptage_trajectoire(
            traj_1, self.zone, instant=0.0
        ) == pytest.approx(cpt_direct)

        t_serie, d_serie = serie_densite_comptage_trajectoire(traj_1, self.zone)
        assert len(t_serie) == len(traj_1.t)
        assert d_serie[0] == pytest.approx(cpt_direct)

        # Erreurs de parametres d'instant / indice
        with pytest.raises(ValueError, match=r"specifier exactement un parametre"):
            mesures_voronoi_trajectoire(traj_1, self.salle, self.zone)
        with pytest.raises(ValueError, match=r"specifier exactement un parametre"):
            mesures_voronoi_trajectoire(traj_1, self.salle, self.zone, instant=0.0, indice=0)
        with pytest.raises(ValueError, match=r"aucun instantane enregistre a t = 999.0 s"):
            mesures_voronoi_trajectoire(traj_1, self.salle, self.zone, instant=999.0)

        # K = 2 : refuse
        with pytest.raises(ValueError, match=r"refuse une archive espacee.*tous les 2 pas"):
            mesures_voronoi_trajectoire(traj_2, self.salle, self.zone, instant=0.0)
        with pytest.raises(ValueError, match=r"refuse une archive espacee.*tous les 2 pas"):
            densite_voronoi_trajectoire(traj_2, self.salle, self.zone, indice=0)
        with pytest.raises(ValueError, match=r"refuse une archive espacee.*tous les 2 pas"):
            vitesse_voronoi_trajectoire(traj_2, self.salle, self.zone, indice=0)
        with pytest.raises(ValueError, match=r"refuse une archive espacee.*tous les 2 pas"):
            densite_comptage_trajectoire(traj_2, self.zone, instant=0.0)
        with pytest.raises(ValueError, match=r"refuse une archive espacee.*tous les 2 pas"):
            serie_densite_comptage_trajectoire(traj_2, self.zone)

    def test_energie_mecanique(self):
        traj_1 = _creer_trajectoire(k=1)
        traj_2 = _creer_trajectoire(k=2)
        nrj_direct = energie_mecanique(traj_1.x, traj_1.v)

        # K = 1 : succes
        nrj_res = energie_mecanique_trajectoire(traj_1)
        np.testing.assert_allclose(nrj_res, nrj_direct)

        # K = 2 : refuse par defaut
        with pytest.raises(ValueError, match=r"refuse une archive espacee.*tous les 2 pas"):
            energie_mecanique_trajectoire(traj_2)

        # K = 2 : autorise si autoriser_espace=True explicite
        nrj_espace = energie_mecanique_trajectoire(traj_2, autoriser_espace=True)
        assert nrj_espace.shape == (traj_2.t.size,)


@pytest.fixture
def configuration_piscine(tmp_path):
    config = lire_configuration(Path(__file__).parents[1] / "experiments/piscine.yaml")
    config["parametres"].update(n_agents=4, duree=0.055)
    fichier = tmp_path / "piscine.yaml"
    fichier.write_text(yaml.safe_dump(config))
    return fichier


def test_simulation_reelle_espacee_refusee_par_observables(configuration_piscine, tmp_path):
    archive_espace = tmp_path / "espacee.npz"
    archive_complete = tmp_path / "complete.npz"

    code_espace = main(
        [
            "simuler",
            str(configuration_piscine),
            "--sortie",
            str(archive_espace),
            "--archiver-tous",
            "2",
        ]
    )
    assert code_espace == 0

    code_complet = main(
        [
            "simuler",
            str(configuration_piscine),
            "--sortie",
            str(archive_complete),
            "--archiver-tous",
            "1",
        ]
    )
    assert code_complet == 0

    porte_a = np.array([28.0, 4.0])
    porte_b = np.array([28.0, 5.2])

    # K = 1 fonctionne directement
    passages = franchissements_trajectoire(archive_complete, porte_a, porte_b)
    assert isinstance(passages.nombre, int)

    # K = 2 est refuse
    with pytest.raises(ValueError, match=r"refuse une archive espacee.*tous les 2 pas"):
        franchissements_trajectoire(archive_espace, porte_a, porte_b)
