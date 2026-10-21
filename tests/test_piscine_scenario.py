"""Jalon 4 : scenario piscine complet, franchissements a capacite unitaire et sortie absorbante."""

from pathlib import Path

import numpy as np
import pytest
import yaml

from viscocrowd.io.configuration import lire_configuration
from viscocrowd.io.trajectoires import lire_trajectoire
from viscocrowd.scenarios.experience import executer_configuration
from viscocrowd.scenarios.piscine import (
    EAU,
    FRANCHISSEMENT,
    PLAGE,
    SORTI,
    ParametresPiscine,
    simuler_piscine,
)

EXEMPLE = Path(__file__).parents[1] / "experiments/piscine.yaml"


def parametres(**changements):
    config = lire_configuration(EXEMPLE)
    return ParametresPiscine(**(config["parametres"] | changements), graine=config["graine"])


@pytest.fixture(scope="module")
def evacuation():
    """20 agents, parametres de reference : environ 3 s de calcul."""
    return simuler_piscine(parametres(n_agents=20))


@pytest.mark.invariant
def test_exclusion_murs_et_cotes_a_chaque_instant(evacuation):
    r = evacuation
    p = r.parametres
    assert r.projection.non_convergences == 0
    assert r.violation_paroi_max() <= 1e-14  # mesure : 7,2e-16 m
    for x, e in zip(r.x, r.etats, strict=True):
        eau, plage = e == EAU, e == PLAGE
        np.testing.assert_array_equal(p.piscine.dans_bassin(x[eau]), True)
        np.testing.assert_array_equal(p.piscine.dans_bassin(x[plage]), False)
        actifs = np.flatnonzero(eau | plage)
        if actifs.size > 1:
            i, j = np.triu_indices(actifs.size, 1)
            distances = np.hypot(*(x[actifs][i] - x[actifs][j]).T)
            assert np.min(distances) >= 2 * p.rayon - p.tolerance * (1 + 1e-8)


@pytest.mark.invariant
def test_etats_a_sens_unique_et_conservation(evacuation):
    """EAU -> FRANCHISSEMENT -> PLAGE -> SORTI, sans retour ; N toujours conserve."""
    etats = evacuation.etats
    assert np.all(np.diff(etats, axis=0) >= 0)
    assert np.all(np.diff(etats, axis=0) <= 1)  # aucune etape sautee
    assert np.all(np.bincount(etats.ravel(), minlength=4).sum() == etats.size)
    assert np.all(etats[-1] == SORTI)  # tous sortis avant la duree maximale


def test_franchissements_un_par_agent_capacite_et_duree(evacuation):
    """Pas de franchissement fantome : un seul par agent, par un site, d'une duree >= T."""
    r = evacuation
    f = r.franchissements
    agents, sites = f[:, 0].astype(int), f[:, 1].astype(int)
    assert np.array_equal(np.sort(agents), np.arange(r.parametres.n_agents))
    durees = np.array([r.parametres.durees[r.natures[k]] for k in sites])
    assert np.all(f[:, 3] - f[:, 2] >= durees - 1e-9)
    for k in np.unique(sites):  # capacite 1 : les occupations d'un site ne se chevauchent pas
        intervalles = np.sort(f[sites == k][:, 2:4], axis=0)
        assert np.all(intervalles[1:, 0] >= intervalles[:-1, 1] - 1e-12)
    # L'etat archive confirme les dates des evenements.
    for a, _, debut, fin in f:
        i = int(a)
        pendant = (r.t > debut + 1e-9) & (r.t < fin - 1e-9)
        assert np.all(r.etats[pendant, i] == FRANCHISSEMENT)


def test_sortie_definitive_par_la_porte(evacuation):
    r = evacuation
    fins = {int(a): fin for a, _, _, fin in r.franchissements}
    porte_x = r.parametres.piscine.longueur_emprise
    for i, instant in enumerate(r.sorties):
        assert np.isfinite(instant) and instant > fins[i]
        apres = r.t > instant + 1e-9
        assert np.all(r.etats[apres, i] == SORTI)
        assert np.all(r.x[apres, i, 0] > porte_x)  # retire, il ne revient pas
    assert r.temps_evacuation(0.5) <= r.temps_evacuation(0.9) <= r.temps_evacuation()


def test_le_partage_vers_les_echelles_suit_leur_duree():
    """Echelles plus rapides : plus d'agents les choisissent (partage emergent, spec 2.6)."""
    nombre = {}
    for duree in (8.0, 0.5):
        r = simuler_piscine(parametres(n_agents=30, durees={"rebord": 4.0, "echelle": duree}))
        nombre[duree] = sum(r.natures[int(k)] == "echelle" for k in r.franchissements[:, 1])
    assert nombre[0.5] > nombre[8.0]


@pytest.mark.parametrize(
    "changement",
    [
        {"n_agents": 0},
        {"portee": 0.3},  # au moins la moitie de pas_rebord : deux sites se disputeraient un agent
        {"pas_guidage": 0.3},
        {"dt": 0.2},
        {"espacement": 0.3},
        {"n_agents": 10_000},  # le bassin ne loge pas autant d'agents
        {"durees": {"rebord": 4.0}},
        {
            "parametres_milieux": {
                "SEC": {"relaxation": 0.5, "acceleration_max": 5.9, "vitesse": 1.34}
            }
        },
        {"geometrie": {"longueur_bassin": 25.0}},
    ],
)
def test_parametres_invalides(changement):
    with pytest.raises(ValueError):
        parametres(**changement)


def test_archive_avec_evenements(tmp_path):
    config = lire_configuration(EXEMPLE)
    config["parametres"].update(n_agents=6, duree=5.0)
    fichier = tmp_path / "piscine.yaml"
    fichier.write_text(yaml.safe_dump(config))
    donnees = executer_configuration(fichier, tmp_path / "piscine.npz")
    relue = lire_trajectoire(tmp_path / "piscine.npz")
    assert relue.metadonnees == donnees.metadonnees
    evenements = relue.metadonnees["evenements"]
    assert len(evenements["sorties"]) == 6
    assert all(s is None for s in evenements["sorties"])  # 5 s ne suffisent pas pour sortir
    assert relue.metadonnees["validation"]["violation_paroi_max_m"] <= 1e-14


@pytest.mark.slow
def test_evacuation_de_reference():
    """100 agents (experiments/piscine.yaml) : tous sortent, sans non-convergence.

    La foule etant chaotique (PR #48), on ne fige pas l'instant exact, qui depend
    des arrondis : seules ses bornes physiques sont testees. Mesures sur cinq
    graines dans le journal du 21 octobre 2026.
    """
    r = simuler_piscine(parametres())
    assert np.all(np.isfinite(r.sorties))
    assert r.projection.non_convergences == 0
    # Borne basse : nager, franchir et marcher sans attendre ; borne haute : file a la porte.
    assert 30.0 < r.temps_evacuation() < 90.0  # mesure : 45,6 s
