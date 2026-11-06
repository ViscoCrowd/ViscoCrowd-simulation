"""Refus des archives espacees pour les calculs d'observables (issue #73).

Depuis la PR #70, `simuler --archiver-tous K` permet d'alleger les trajectoires piscine en
n'enregistrant qu'une image tous les K pas physiques.
Ce module verifie que toute fonction calculant une observable depuis une archive
(debit, franchissements, sorties definitives, densite et vitesse de Voronoi,
comptage de densite, energie mecanique) :
  1. Accepte et calcule correctement les grandeurs pour une archive complete (K = 1) ;
  2. Ne conserve que les baigneurs actifs (EAU ou PLAGE) pour les mesures de densite
     et de Voronoi lorsque l'archive porte des etats ;
  3. Refuse explicitement avec ValueError une archive espacee (K >= 2), une trajectoire
     sans dt_simulation_s ou une trajectoire sous-echantillonnee (t[::5]).
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
from viscocrowd.scenarios.piscine import EAU, FRANCHISSEMENT, NOMS_ETATS, PLAGE, SORTI


def _creer_trajectoire(k: int | None = 1, *, p: int = 20, dt: float = 0.05) -> Trajectoire:
    """Cree une trajectoire simple de 2 agents se deplacant vers +x."""
    t = np.arange(p, dtype=float) * dt
    x = np.zeros((p, 2, 2), dtype=float)
    x[:, 0, 0] = 0.5 + t * 1.0
    x[:, 0, 1] = 2.0
    x[:, 1, 0] = 0.5 + t * 1.0
    x[:, 1, 1] = 3.0

    v = np.zeros((p, 2, 2), dtype=float)
    v[:, :, 0] = 1.0

    rayons = np.array([0.2, 0.2])
    metadonnees: dict = {
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
    assert traj_complete.dt_simulation == pytest.approx(0.05)
    assert traj_complete.est_complete is True
    traj_complete.exiger_complete("test")

    traj_espacee = _creer_trajectoire(k=2)
    assert traj_espacee.pas_archivage == 2
    assert traj_espacee.est_complete is False
    with pytest.raises(ValueError, match=r"refuse une archive espacee.*tous les 2 pas"):
        traj_espacee.exiger_complete("mon observable")

    # Sans cle archivage : pas_archivage vaut 1 par defaut mais exiger_complete refuse
    # l'absence de dt_simulation_s permettant de certifier les pas
    traj_sans_archivage = _creer_trajectoire(k=None)
    assert traj_sans_archivage.pas_archivage == 1
    assert traj_sans_archivage.est_complete is False
    with pytest.raises(ValueError, match=r"dt_simulation_s"):
        traj_sans_archivage.exiger_complete("test")

    # Trajectoire sous-echantillonnee (t[::5]) deguisee avec metadonnees K = 1
    traj_tronquee = Trajectoire(
        t=traj_complete.t[::5],
        x=traj_complete.x[::5],
        v=traj_complete.v[::5],
        rayons=traj_complete.rayons,
        metadonnees=traj_complete.metadonnees,
    )
    assert traj_tronquee.est_complete is False
    with pytest.raises(ValueError, match=r"ecart temporel max"):
        traj_tronquee.exiger_complete("test")

    for valeur_invalide in (0, -1, True, False, 2.0, "2"):
        with pytest.raises(ValueError, match="tous_les_pas"):
            _creer_trajectoire(k=valeur_invalide)  # type: ignore[arg-type]

    for dt_invalide in (0.0, -0.01, True, "0.01", float("nan")):
        with pytest.raises(ValueError, match="dt_simulation_s"):
            Trajectoire(
                t=traj_complete.t,
                x=traj_complete.x,
                v=traj_complete.v,
                rayons=traj_complete.rayons,
                metadonnees={"archivage": {"tous_les_pas": 1, "dt_simulation_s": dt_invalide}},
            )

    base = _creer_trajectoire(k=None)
    with pytest.raises(ValueError, match="archivage"):
        Trajectoire(
            t=base.t,
            x=base.x,
            v=base.v,
            rayons=base.rayons,
            metadonnees={"archivage": "invalide"},
        )


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

        # K = 1 : via Trajectoire et via fichier
        f_obj = franchissements_trajectoire(traj_1, self.a_porte, self.b_porte)
        assert f_obj.nombre == f_direct.nombre
        np.testing.assert_array_equal(f_obj.instant, f_direct.instant)

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
            franchissements_trajectoire(traj_2, self.a_porte, self.b_porte)
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

        # K = 1 : via objet et via fichier
        s_obj = sorties_definitives_trajectoire(traj_1, self.a_porte, self.b_porte)
        np.testing.assert_array_equal(s_obj.instant, s_direct.instant)

        chemin_1 = tmp_path / "sorties1.npz"
        ecrire_trajectoire(chemin_1, traj_1)
        s_fichier = sorties_definitives_trajectoire(chemin_1, self.a_porte, self.b_porte)
        np.testing.assert_array_equal(s_fichier.instant, s_direct.instant)

        # K = 2 : refuse
        chemin_2 = tmp_path / "sorties2.npz"
        ecrire_trajectoire(chemin_2, traj_2)
        with pytest.raises(ValueError, match=r"refuse une archive espacee.*tous les 2 pas"):
            sorties_definitives_trajectoire(traj_2, self.a_porte, self.b_porte)
        with pytest.raises(ValueError, match=r"refuse une archive espacee.*tous les 2 pas"):
            sorties_definitives_trajectoire(chemin_2, self.a_porte, self.b_porte)

    def test_mesures_et_densites_voronoi(self):
        traj_1 = _creer_trajectoire(k=1)
        traj_2 = _creer_trajectoire(k=2)

        x0, v0 = traj_1.x[0], traj_1.v[0]
        dens_direct, vit_direct = mesures_voronoi(x0, v0, self.salle, self.zone)
        cpt_direct = densite_comptage(x0, self.zone)

        # K = 1 : succes avec instant, int Python et np.int64
        d_res, v_res = mesures_voronoi_trajectoire(traj_1, self.salle, self.zone, instant=0.0)
        assert d_res == pytest.approx(dens_direct)
        assert v_res == pytest.approx(vit_direct)

        assert densite_voronoi_trajectoire(
            traj_1, self.salle, self.zone, indice=np.int64(0)
        ) == pytest.approx(dens_direct)
        assert vitesse_voronoi_trajectoire(
            traj_1, self.salle, self.zone, indice=0
        ) == pytest.approx(vit_direct)
        assert densite_comptage_trajectoire(traj_1, self.zone, indice=np.int64(0)) == pytest.approx(
            cpt_direct
        )

        t_serie, d_serie = serie_densite_comptage_trajectoire(traj_1, self.zone)
        assert len(t_serie) == len(traj_1.t)
        assert d_serie[0] == pytest.approx(cpt_direct)

        # Tolerance sur instant avec une seule image et dt = 0,01 s
        traj_une_image = _creer_trajectoire(k=1, p=1, dt=0.01)
        with pytest.raises(ValueError, match=r"aucun instantane enregistre a t = 0.45 s"):
            densite_comptage_trajectoire(traj_une_image, self.zone, instant=0.45)

        # Erreurs de parametres d'instant / indice
        with pytest.raises(ValueError, match=r"specifier exactement un parametre"):
            mesures_voronoi_trajectoire(traj_1, self.salle, self.zone)
        with pytest.raises(ValueError, match=r"specifier exactement un parametre"):
            mesures_voronoi_trajectoire(traj_1, self.salle, self.zone, instant=0.0, indice=0)
        with pytest.raises(ValueError, match=r"indice doit etre un entier"):
            densite_comptage_trajectoire(traj_1, self.zone, indice=True)  # type: ignore[arg-type]
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

    def test_filtrage_etats_actifs_piscine(self):
        """Verifie que les agents SORTI (empiles dehors) et FRANCHISSEMENT sont exclus."""
        # 4 agents sur 2 instants :
        # - agents 0 et 1 : actifs sur la PLAGE en (1.0, 2.0) et (1.5, 3.0)
        # - agent 2 : en FRANCHISSEMENT dans la zone en (1.2, 2.5)
        # - agents 3 et 4 : SORTI empiles au meme point dehors (49.0, 10.25)
        t = np.array([0.0, 0.01])
        x = np.array(
            [
                [[1.0, 2.0], [1.5, 3.0], [1.2, 2.5], [49.0, 10.25], [49.0, 10.25]],
                [[1.1, 2.0], [1.6, 3.0], [1.2, 2.5], [49.0, 10.25], [49.0, 10.25]],
            ]
        )
        v = np.zeros_like(x)
        v[:, 0, 0] = 1.0
        v[:, 1, 0] = 1.0
        etats = np.array(
            [
                [EAU, PLAGE, FRANCHISSEMENT, SORTI, SORTI],
                [EAU, PLAGE, FRANCHISSEMENT, SORTI, SORTI],
            ],
            dtype=np.int64,
        )
        traj = Trajectoire(
            t=t,
            x=x,
            v=v,
            rayons=np.full(5, 0.2),
            metadonnees={
                "etats": list(NOMS_ETATS),
                "archivage": {"tous_les_pas": 1, "dt_simulation_s": 0.01},
            },
            etats=etats,
        )

        # Seuls les agents 0 et 1 (EAU et PLAGE) doivent etre retenus
        d_attendue, v_attendue = mesures_voronoi(x[0, :2], v[0, :2], self.salle, self.zone)
        d_mes, v_mes = mesures_voronoi_trajectoire(traj, self.salle, self.zone, indice=0)
        assert d_mes == pytest.approx(d_attendue)
        assert v_mes == pytest.approx(v_attendue)

        # Comptage : l'agent 2 (FRANCHISSEMENT) bien que dans la zone ne doit pas etre compte
        cpt_attendu = densite_comptage(x[0, :2], self.zone)
        assert densite_comptage_trajectoire(traj, self.zone, indice=0) == pytest.approx(cpt_attendu)
        _, serie = serie_densite_comptage_trajectoire(traj, self.zone)
        np.testing.assert_allclose(serie, [cpt_attendu, cpt_attendu])

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


@pytest.mark.parametrize("legende", [None, ["a", "b"], "eau plage"])
def test_etats_sans_legende_refuses(legende):
    """Sans legende, les codes ne disent rien : on refuse plutot que de deviner."""
    metadonnees = {"archivage": {"tous_les_pas": 1, "dt_simulation_s": 0.01}}
    if legende is not None:
        metadonnees["etats"] = legende
    traj = Trajectoire(
        t=np.array([0.0]),
        x=np.array([[[1.0, 1.0]]]),
        v=np.zeros((1, 1, 2)),
        rayons=np.array([0.2]),
        metadonnees=metadonnees,
        etats=np.array([[0]], dtype=np.int64),
    )
    zone = Rectangle(0.0, 2.0, 0.0, 2.0)
    with pytest.raises(ValueError, match="sans legende"):
        densite_comptage_trajectoire(traj, zone, indice=0)
    with pytest.raises(ValueError, match="sans legende"):
        serie_densite_comptage_trajectoire(traj, zone)
