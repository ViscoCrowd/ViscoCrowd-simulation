"""P6 : passages, blocages et absence de franchissements fantomes, hors de la reference.

`test_piscine_scenario.py` verifie le parcours EAU -> FRANCHISSEMENT -> PLAGE -> SORTI sur
la reference a 20 baigneurs. Les defauts que P6 doit exclure apparaissent pourtant ailleurs :
sans regulation (#127, nageurs bloques devant l'echelle), devant une porte etroite (#85,
arches aux montants), ou avec les options qui changent la cible et le rythme des nageurs
(navigation, choix du site, temps de reaction, chutes). Ce fichier rejoue donc le meme
controle complet, `verifier_parcours`, sur ces configurations.

Un franchissement est « fantome » s'il ne correspond a aucun passage physique : un agent
qui saisit un site hors de portee, qui change de cote sans occuper de site, qui reapparait
ailleurs qu'au point d'arrivee, ou qui sort par un mur. Un blocage est un agent qui ne sort
jamais. Chaque assertion ci-dessous ecarte l'un de ces cas.
"""

from __future__ import annotations

import numpy as np
import pytest

from utilitaires import parametres_reduits
from viscocrowd.model.chutes import ParametresChutes
from viscocrowd.observables.sortie import sorties_definitives
from viscocrowd.scenarios.piscine import (
    EAU,
    FRANCHISSEMENT,
    PLAGE,
    SORTI,
    ResultatPiscine,
    simuler_piscine,
)

# Deplacement maximal d'un agent entre deux pas archives sans changer d'etat, en m.
# A dt = 0,01 s, le plus rapide (2 m/s, x 1,45 avec la navigation) parcourt 0,03 m ; la
# projection peut y ajouter une correction de contact. Un quart de diametre laisse cette
# marge et reste dix fois sous le pas des sites de rebord (0,6 m) : un saut d'un cote a
# l'autre d'un mur ou du bassin ne peut pas s'y cacher.
SAUT_MAX = 0.1
# Distance parcourue en un pas avant le test de portee, en m (meme majoration).
PAS_MAX = 0.05


def verifier_parcours(r: ResultatPiscine) -> None:
    """Controle complet du parcours de chaque agent ; leve AssertionError au premier defaut."""
    p = r.parametres
    piscine = p.piscine
    etats, x, t = r.etats, r.x, r.t
    n = p.n_agents
    sites = piscine.sites()
    assert tuple(s.nature for s in sites) == r.natures
    position = np.array([s.position for s in sites])
    attente = np.array([s.attente(p.rayon) for s in sites])
    arrivee = np.array([s.arrivee(p.rayon) for s in sites])
    portee_bras = p.deblocage["portee"] if p.deblocage else p.portee

    # Murs, contacts et projection.
    assert r.projection.non_convergences == 0
    assert r.violation_paroi_max() <= 1e-12

    # Blocages : chacun sort, avant la duree maximale.
    assert np.all(etats[-1] == SORTI), f"{np.sum(etats[-1] != SORTI)} agent(s) jamais sortis"
    assert np.all(np.isfinite(r.sorties))
    assert t[-1] < p.duree

    # Etats a sens unique, sans etape sautee.
    sauts = np.diff(etats, axis=0)
    assert np.all((sauts >= 0) & (sauts <= 1))

    # Chaque cote du bord est le bon : l'eau dans le bassin, la plage dehors.
    for xi, ei in zip(x, etats, strict=True):
        assert np.all(piscine.dans_bassin(xi[ei == EAU]))
        assert not np.any(piscine.dans_bassin(xi[ei == PLAGE]))

    # Un franchissement par agent, par un site existant, d'une duree au moins egale a
    # celle du site, et jamais deux agents sur un site a la fois.
    f = r.franchissements
    agents, k_site = f[:, 0].astype(int), f[:, 1].astype(int)
    assert np.array_equal(np.sort(agents), np.arange(n))
    assert np.all((k_site >= 0) & (k_site < len(sites)))
    durees = np.array([p.durees[r.natures[k]] for k in k_site])
    assert np.all(f[:, 3] - f[:, 2] >= durees - 1e-9)
    for k in np.unique(k_site):
        intervalles = np.sort(f[k_site == k][:, 2:4], axis=0)
        assert np.all(intervalles[1:, 0] >= intervalles[:-1, 1] - 1e-12)

    a_bout_de_bras = 0
    for a, k, debut, fin in f:
        i, k = int(a), int(k)
        dans_eau = np.flatnonzero(etats[:, i] == EAU)
        pendant = np.flatnonzero(etats[:, i] == FRANCHISSEMENT)
        sur_plage = np.flatnonzero(etats[:, i] == PLAGE)
        assert pendant.size and sur_plage.size
        # Saisi a portee : la derniere position dans l'eau est pres du point d'attente.
        # Au-dela de la portee ordinaire, seule la regle de deblocage (#127) le permet.
        ecart = np.hypot(*(x[dans_eau[-1], i] - attente[k]))
        assert ecart <= portee_bras + PAS_MAX, f"agent {i} saisit le site {k} a {ecart:.2f} m"
        a_bout_de_bras += ecart > p.portee + PAS_MAX
        # Pendant le franchissement, l'agent est sur son site, et l'archive suit l'evenement.
        np.testing.assert_array_equal(
            x[pendant, i], np.broadcast_to(position[k], (pendant.size, 2))
        )
        assert t[pendant[0]] == pytest.approx(debut) and t[sur_plage[0]] == pytest.approx(fin)
        # Reintroduit au point d'arrivee de ce site, pas ailleurs.
        np.testing.assert_array_equal(x[sur_plage[0], i], arrivee[k])

    assert a_bout_de_bras <= r.deblocages

    # Aucun saut sans changement d'etat : on ne traverse ni un mur ni le bord du bassin.
    meme = (etats[1:] == etats[:-1]) & ((etats[1:] == EAU) | (etats[1:] == PLAGE))
    deplacements = np.hypot(*np.moveaxis(x[1:] - x[:-1], -1, 0))
    assert np.max(deplacements[meme]) <= SAUT_MAX

    # Sortie par la porte : la derniere position sur la plage est dans l'embrasure, et la
    # detection a posteriori sur les positions donne les memes instants.
    (_, y_bas), (_, y_haut) = piscine.porte
    for i in range(n):
        derniere = np.flatnonzero(etats[:, i] == PLAGE)[-1]
        assert y_bas - 1e-9 <= x[derniere, i, 1] <= y_haut + 1e-9
    porte_a, porte_b = piscine.porte
    obs = sorties_definitives(t, x, porte_a, porte_b)
    assert np.all(obs.sortis)
    assert np.max(np.abs(r.sorties - obs.instant)) < p.dt


# Configurations de 30 a 40 baigneurs : quelques secondes de calcul chacune.
RAPIDES = {
    "sans-regulation": dict(n_agents=40, temps_espacement=None),
    "porte-0.8": dict(n_agents=30, geometrie={"largeur_porte": 0.8}),
    "sans-echelle": dict(n_agents=30, geometrie={"echelles": []}),
    "navigation": dict(n_agents=30, navigation={}),
    "choix-site": dict(
        n_agents=30, choix_site={"portee": 3.0, "periode": 1.0, "marge": 1.0, "mode": "local"}
    ),
    "reaction": dict(n_agents=30, reaction={"mediane": 3.0, "dispersion": 0.5}),
    "chutes": dict(n_agents=30, chutes=ParametresChutes()),
}

# Effectifs pleins : reserves aux tests lents (Linux, macOS, Windows a chaque push sur dev).
LENTS = {
    # Le cas de #127 : sans regulation, 13 des 200 baigneurs de la graine 4 restaient
    # bloques sous l'echelle du haut. Au 24 novembre, ils sortent tous en 58 s, avec ou
    # sans la regle de deblocage (couverte par les arches de test_piscine_scenario.py).
    "200-sans-regulation-graine-4": dict(n_agents=200, temps_espacement=None, graine=4),
    "200-sans-regulation": dict(n_agents=200, temps_espacement=None),
    "reference-100": dict(n_agents=100),
    "100-toutes-options": dict(
        n_agents=100,
        navigation={},
        choix_site={"portee": 3.0, "periode": 1.0, "marge": 1.0, "mode": "local"},
        reaction={"mediane": 3.0, "dispersion": 0.5},
    ),
}


def _simuler(**surcharges) -> ResultatPiscine:
    return simuler_piscine(parametres_reduits(duree=180.0, **surcharges))


@pytest.mark.parametrize("surcharges", RAPIDES.values(), ids=RAPIDES.keys())
def test_parcours_sans_fantome_ni_blocage(surcharges):
    verifier_parcours(_simuler(**surcharges))


@pytest.mark.slow
@pytest.mark.parametrize("surcharges", LENTS.values(), ids=LENTS.keys())
def test_parcours_sans_fantome_ni_blocage_effectif_plein(surcharges):
    verifier_parcours(_simuler(**surcharges))


@pytest.fixture(scope="module")
def juste() -> ResultatPiscine:
    return _simuler(n_agents=8)


class TestLeControleDetecte:
    """Le controle doit echouer sur un parcours fausse : sinon il ne prouve rien."""

    def _fausser(self, r: ResultatPiscine, **champs) -> ResultatPiscine:
        from dataclasses import replace

        return replace(r, **champs)

    def test_parcours_juste_accepte(self, juste):
        verifier_parcours(juste)

    def test_saut_a_travers_le_bassin(self, juste):
        x = juste.x.copy()
        i = 0
        sur_plage = np.flatnonzero(juste.etats[:, i] == PLAGE)
        x[sur_plage[len(sur_plage) // 2], i, 1] += 1.0  # 1 m d'un coup, meme etat
        with pytest.raises(AssertionError):
            verifier_parcours(self._fausser(juste, x=x))

    def test_reintroduction_ailleurs_qu_a_l_arrivee(self, juste):
        x = juste.x.copy()
        i = int(juste.franchissements[0, 0])
        x[np.flatnonzero(juste.etats[:, i] == PLAGE)[0], i] += 0.05
        with pytest.raises(AssertionError):
            verifier_parcours(self._fausser(juste, x=x))

    def test_site_saisi_hors_de_portee(self, juste):
        f = juste.franchissements.copy()
        k = int(f[0, 1])
        f[0, 1] = (k + len(juste.natures) // 2) % len(juste.natures)  # un site lointain
        with pytest.raises(AssertionError):
            verifier_parcours(self._fausser(juste, franchissements=f))

    def test_agent_jamais_sorti(self, juste):
        etats = juste.etats.copy()
        etats[-1, 0] = PLAGE
        with pytest.raises(AssertionError):
            verifier_parcours(self._fausser(juste, etats=etats))
