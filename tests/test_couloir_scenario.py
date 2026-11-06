"""Validation G1/G5 : guidage, contacts et archives sur le banc de couloir."""

from copy import deepcopy
from pathlib import Path

import numpy as np
import pytest
import yaml

from viscocrowd.io.configuration import lire_configuration
from viscocrowd.io.trajectoires import lire_trajectoire
from viscocrowd.observables.debit import franchissements
from viscocrowd.scenarios.couloir import ParametresCouloir, simuler_couloir
from viscocrowd.scenarios.experience import executer_configuration

EXEMPLE = Path(__file__).parents[1] / "experiments/couloir.yaml"
AVEC_OBSTACLE = Path(__file__).parents[1] / "experiments/couloir_obstacle.yaml"


def parametres(fichier=EXEMPLE, **changements):
    config = lire_configuration(fichier)
    return ParametresCouloir(**(config["parametres"] | changements), graine=config["graine"])


@pytest.fixture(scope="module")
def demonstration():
    return simuler_couloir(parametres())


def test_agent_isole_converge_vers_la_solution_analytique():
    erreurs = []
    for dt in (0.02, 0.01, 0.005):
        p = parametres(
            n_agents=1,
            colonnes=1,
            bruit=0.0,
            frontieres=[],
            milieux=["SEC"],
            parametres_milieux={
                "SEC": {"relaxation": 0.5, "acceleration_max": 100.0, "vitesse": 1.0}
            },
            dt=dt,
            duree=2.0,
        )
        r = simuler_couloir(p)
        exact = p.origine_x + 2.0 - 0.5 * (1 - np.exp(-2.0 / 0.5))
        erreurs.append(abs(r.x[-1, 0, 0] - exact))
        np.testing.assert_array_equal(r.x[:, 0, 1], 0.0)
    assert erreurs[0] < 0.021  # m ; l'erreur doit decroitre a l'ordre 1
    np.testing.assert_allclose(np.array(erreurs[:-1]) / erreurs[1:], 2.0, rtol=0.02)


@pytest.mark.invariant
def test_groupe_reste_confine_et_sans_recouvrement(demonstration):
    r = demonstration
    assert r.x.shape == (1401, 24, 2)
    assert r.projection.non_convergences == 0
    assert r.violation_paroi_max() <= 1e-14
    i, j = np.triu_indices(r.parametres.n_agents, 1)
    distances = np.linalg.norm(r.x[:, i] - r.x[:, j], axis=2)
    recouvrement = 2 * r.parametres.rayon - distances
    assert np.max(recouvrement) <= r.parametres.tolerance * (1 + 1e-8)
    assert np.min(distances) < 2 * r.parametres.rayon + 1e-6  # de vrais contacts ont eu lieu


def test_tous_les_agents_franchissent_la_section_sans_retrait(demonstration):
    r = demonstration
    passages = franchissements(r.t, r.x, *r.domaine.section_sortie)
    assert passages.nombre == r.parametres.n_agents
    assert len(np.unique(passages.agent)) == r.parametres.n_agents
    assert np.all(passages.sens == 1)
    assert np.all(r.x[-1, :, 0] > r.domaine.longueur)
    assert r.x.shape[1] == r.parametres.n_agents  # ce n'est pas un etat absorbant


def test_egalite_exacte_des_sols_supprime_l_effet_de_frontiere():
    p = parametres(n_agents=1, colonnes=1, origine_x=3.9, bruit=0.0, duree=2.0)
    sols = {"SEC": p.parametres_milieux["SEC"], "MOUILLE": p.parametres_milieux["SEC"]}
    a = simuler_couloir(
        parametres(
            n_agents=1, colonnes=1, origine_x=3.9, bruit=0.0, duree=2.0, parametres_milieux=sols
        )
    )
    b = simuler_couloir(
        parametres(
            n_agents=1,
            colonnes=1,
            origine_x=3.9,
            bruit=0.0,
            duree=2.0,
            frontieres=[],
            milieux=["SEC"],
        )
    )
    np.testing.assert_array_equal(a.x, b.x)


def test_archive_rejouable_et_graine_preservee(tmp_path):
    config = lire_configuration(EXEMPLE)
    config["parametres"]["duree"] = 0.1
    fichier = tmp_path / "couloir.yaml"
    fichier.write_text(yaml.safe_dump(config))
    a = executer_configuration(fichier, tmp_path / "a.npz")
    relue = lire_trajectoire(tmp_path / "a.npz")
    assert a.metadonnees == relue.metadonnees
    fichier.write_text(yaml.safe_dump(relue.metadonnees["configuration"]))
    b = executer_configuration(fichier, tmp_path / "b.npz")
    np.testing.assert_array_equal(a.x, b.x)
    config["graine"] += 1
    fichier.write_text(yaml.safe_dump(config))
    autre = executer_configuration(fichier, tmp_path / "autre.npz")
    assert not np.array_equal(a.x[0], autre.x[0])


@pytest.mark.parametrize(
    "changement",
    [
        {"n_agents": True},
        {"n_agents": 0},
        {"colonnes": 0},
        {"dt": np.nan},
        {"bruit": -1.0},
        {"espacement": 0.2},
        {"largeur": 0.5},
        {"origine_x": 11.0},
        {"frontieres": [15.0]},
        {"milieux": ["INCONNU"]},
        {"parametres_milieux": {}},
        {"dt": 0.5},
        {"dt": 0.1},
        {"duree": -1.0},
        {"guidage": "droit"},
        {"pas_guidage": 0.3},  # plus grand que le rayon : la marge n'est pas resolue
        {"pas_guidage": np.nan},
        {"obstacles": [[6.0, 7.0, -0.5, 0.5]]},  # l'aval traverserait l'obstacle
        {"guidage": "eikonal", "obstacles": [[6.0, 7.0, -0.5]]},
        {"guidage": "eikonal", "obstacles": [[6.0, 7.0, -0.5, 1.3]]},  # passage < diametre
        {"guidage": "eikonal", "obstacles": [[11.5, 12.5, -0.5, 0.5]]},  # au-dela de la sortie
        {"guidage": "eikonal", "obstacles": [[1.0, 2.0, -0.5, 0.5]]},  # sur la population
        {"guidage": "eikonal", "obstacles": [[5.0, 6.0, -0.5, 0.5], [6.2, 7.0, -0.5, 0.5]]},
    ],
)
def test_parametres_invalides(changement):
    with pytest.raises(ValueError):
        parametres(**changement)


@pytest.fixture(scope="module")
def contournement():
    return simuler_couloir(parametres(AVEC_OBSTACLE))


@pytest.mark.invariant
def test_pilier_respecte_sans_recouvrement(contournement):
    """La projection impose le pilier comme une paroi ; les agents le touchent sans y entrer."""
    r = contournement
    p = r.parametres
    pilier = p.rectangles[0]
    assert r.projection.non_convergences == 0
    assert r.violation_paroi_max() <= 1e-14  # mesure : 5,6e-17 m
    i, j = np.triu_indices(p.n_agents, 1)
    distances = np.linalg.norm(r.x[:, i] - r.x[:, j], axis=2)
    assert np.max(2 * p.rayon - distances) <= p.tolerance * (1 + 1e-8)
    au_pilier = np.min(pilier.distance(r.x.reshape(-1, 2)))
    assert au_pilier == pytest.approx(p.rayon, abs=1e-6)  # contact effectif avec le pilier


def test_la_foule_contourne_le_pilier_des_deux_cotes_et_sort(contournement):
    r = contournement
    pilier = r.parametres.rectangles[0]
    passages = franchissements(r.t, r.x, *r.domaine.section_sortie)
    assert passages.nombre == 24 and len(np.unique(passages.agent)) == 24
    assert np.all(passages.sens == 1)
    # Cote de contournement : signe de y quand l'agent atteint le milieu du pilier.
    milieu = 0.5 * (pilier.x_min + pilier.x_max)
    rang = np.argmax(r.x[:, :, 0] >= milieu, axis=0)
    cotes = np.sign(r.x[rang, np.arange(24), 1])
    assert np.sum(cotes > 0) >= 6 and np.sum(cotes < 0) >= 6  # mesure : 12 et 12
    # Le pilier retarde la sortie, sans la bloquer : dernier passage 9,380 s contre 9,228 s.
    assert passages.instant.max() == pytest.approx(9.380, abs=1e-3)


def test_guidage_eikonal_sans_obstacle_identique_a_l_aval():
    """G1 et G2 se recoupent au niveau du scenario, bit a bit."""
    p = dict(n_agents=6, colonnes=3, duree=8.0)
    aval = simuler_couloir(parametres(**p))
    eikonal = simuler_couloir(parametres(guidage="eikonal", **p))
    np.testing.assert_array_equal(aval.x, eikonal.x)


def test_yaml_exige_tous_les_parametres_du_banc(tmp_path):
    config = deepcopy(lire_configuration(EXEMPLE))
    del config["parametres"]["longueur"]
    fichier = tmp_path / "incomplet.yaml"
    fichier.write_text(yaml.safe_dump(config))
    with pytest.raises(ValueError, match="manquants ou inconnus"):
        executer_configuration(fichier, tmp_path / "a.npz")
    assert not (tmp_path / "a.npz").exists()
