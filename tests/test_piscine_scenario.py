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
    NOMS_ETATS,
    PLAGE,
    SORTI,
    ParametresPiscine,
    _attribuer_sites,
    simuler_piscine,
    verifier_coherence,
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
def test_etats_a_sens_unique(evacuation):
    """EAU -> FRANCHISSEMENT -> PLAGE -> SORTI, sans retour ni etape sautee."""
    etats = evacuation.etats
    assert np.all((etats >= EAU) & (etats <= SORTI))
    assert np.all(np.diff(etats, axis=0) >= 0)
    assert np.all(np.diff(etats, axis=0) <= 1)  # aucune etape sautee
    assert np.all(etats[-1] == SORTI)  # tous sortis avant la duree maximale
    # Jamais plus d'agents en franchissement que de sites.
    assert np.max(np.sum(etats == FRANCHISSEMENT, axis=1)) <= len(evacuation.natures)


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
        {"durees": [4.0, 2.0]},  # liste au lieu d'une table YAML
        {"parametres_milieux": [1, 2, 3]},
        {"geometrie": [25.0]},
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


class TestCoherence:
    """Chaque incoherence leve une erreur : le controle peut vraiment echouer."""

    @pytest.fixture
    def coherent(self):
        p = parametres(n_agents=4)
        b = p.piscine.bassin
        x = np.array(
            [
                [b.x_min + 2.0, b.y_min + 2.0],  # eau
                [b.x_min + 3.0, b.y_min],  # franchissement, pose sur le bord
                [b.x_min - 1.5, b.y_min - 1.0],  # plage
                [100.0, 10.0],  # sorti
            ]
        )
        etat = np.array([EAU, FRANCHISSEMENT, PLAGE, SORTI])
        occupant = np.full(len(p.piscine.sites()), -1)
        occupant[7] = 1
        site_agent = np.array([-1, 7, 3, 5])
        return etat, occupant, site_agent, x, p.piscine

    def test_etat_coherent_accepte(self, coherent):
        verifier_coherence(*coherent)

    @pytest.mark.parametrize(
        "corruption",
        [
            lambda e, o, s, x: e.__setitem__(0, 4),  # etat inconnu
            lambda e, o, s, x: o.__setitem__(7, -1),  # franchissement sans site
            lambda e, o, s, x: o.__setitem__(8, 0),  # site occupe par un agent dans l'eau
            lambda e, o, s, x: o.__setitem__(8, 1),  # un agent sur deux sites
            lambda e, o, s, x: s.__setitem__(1, 6),  # l'agent designe un autre site
            lambda e, o, s, x: x.__setitem__(0, x[2]),  # agent de l'eau sur la plage
            lambda e, o, s, x: x.__setitem__(2, x[0]),  # agent de la plage dans l'eau
        ],
    )
    def test_incoherence_detectee(self, coherent, corruption):
        etat, occupant, site_agent, x, piscine = coherent
        corruption(etat, occupant, site_agent, x)
        with pytest.raises(RuntimeError):
            verifier_coherence(etat, occupant, site_agent, x, piscine)


class TestAttribution:
    def test_le_plus_proche_servi_d_abord(self):
        """L'agent 0 a le plus petit indice, mais l'agent 1 est plus pres du site 0."""
        distances = np.array([[0.2, 0.1], [0.05, 0.3]])
        assert sorted(_attribuer_sites(distances, 0.25)) == [(0, 1), (1, 0)]
        distances = np.array([[0.2, 0.5], [0.05, 0.6]])
        assert _attribuer_sites(distances, 0.25) == [(1, 0)]  # l'agent 0 attend

    def test_independant_de_la_numerotation(self):
        rng = np.random.default_rng(0)
        distances = rng.uniform(0.0, 0.3, size=(6, 5))
        couples = set(_attribuer_sites(distances, 0.25))
        ordre = rng.permutation(6)
        permutes = {(ordre[a], s) for a, s in _attribuer_sites(distances[ordre], 0.25)}
        assert permutes == couples

    def test_un_agent_a_portee_de_deux_sites_n_en_prend_qu_un(self):
        """Cas des coins du bassin : deux points d'attente a 0,15 m."""
        assert _attribuer_sites(np.array([[0.1, 0.12]]), 0.25) == [(0, 0)]


def test_coins_du_bassin_sites_a_plus_d_un_diametre():
    """Valeurs de reference : sites des coins a 0,437 m sur le bord ; un rayon de 0,22 m est refuse."""
    p = parametres()
    bords = np.array([s.position for s in p.piscine.sites()])
    i, j = np.triu_indices(len(bords), 1)
    assert np.min(np.hypot(*(bords[i] - bords[j]).T)) == pytest.approx(0.4366, abs=1e-4)
    with pytest.raises(ValueError, match="diametre"):
        parametres(rayon=0.22)


def test_deplacement_mesure_trop_grand_refuse(monkeypatch):
    """Une correction de contact qui deplace un agent de plus de r/5 arrete le calcul."""
    import viscocrowd.scenarios.piscine as module

    vrai_pas = module.pas_semi_implicite

    def pas_pousse(etat, *args):
        nouveau = vrai_pas(etat, *args)
        return type(nouveau)(
            x=nouveau.x + np.array([0.05, 0.0]), v=nouveau.v, r=nouveau.r, t=nouveau.t
        )

    monkeypatch.setattr(module, "pas_semi_implicite", pas_pousse)
    with pytest.raises(ValueError, match="deplacement mesure"):
        simuler_piscine(parametres(n_agents=3, duree=1.0))


@pytest.mark.parametrize("fraction", [0.0, -1.0, 1.5, np.nan])
def test_temps_evacuation_refuse_une_fraction_invalide(evacuation, fraction):
    with pytest.raises(ValueError, match="fraction"):
        evacuation.temps_evacuation(fraction)


def test_archive_conserve_les_etats(tmp_path):
    config = lire_configuration(EXEMPLE)
    config["parametres"].update(n_agents=4, duree=12.0)
    fichier = tmp_path / "piscine.yaml"
    fichier.write_text(yaml.safe_dump(config))
    executer_configuration(fichier, tmp_path / "piscine.npz")
    relue = lire_trajectoire(tmp_path / "piscine.npz")
    assert relue.etats.shape == relue.x.shape[:2]
    assert relue.metadonnees["etats"] == list(NOMS_ETATS)
    assert np.any(relue.etats == FRANCHISSEMENT)  # les poses sur le bord sont reperables
