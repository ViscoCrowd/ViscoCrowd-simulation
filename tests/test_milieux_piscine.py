"""G3 sur la geometrie C6 : chaque sol de la piscine impose ses parametres (issue #26).

`test_milieu.py` et `test_milieux_assemblage.py` verifient l'adherence et l'assemblage
sur des pieces factices. Ici, on observe le pas libre PENDANT une evacuation reelle,
avec la carte et les valeurs de `experiments/piscine.yaml`, et on le compare a un calcul
independant : la carte y est recalculee a la main a partir du rectangle du bassin, et
l'acceleration bornee reecrite en trois lignes. Une erreur de branchement (milieux
permutes, carte decalee, facteur de panique oublie, milieu lu en fin de pas) change
le pas libre et fait echouer ces tests.
"""

from pathlib import Path

import numpy as np
import pytest

import viscocrowd.scenarios.piscine as scenario
from viscocrowd.core.integrator import trajectoire
from viscocrowd.core.state import State
from viscocrowd.io.configuration import lire_configuration
from viscocrowd.model.carte import CartePiscine
from viscocrowd.model.milieu import Milieu, pas_libre_milieux

EXEMPLE = Path(__file__).parents[1] / "experiments/piscine.yaml"


def parametres(**changements):
    config = lire_configuration(EXEMPLE)
    return scenario.ParametresPiscine(
        **(config["parametres"] | changements), graine=config["graine"]
    )


def zone_a_la_main(p, x):
    """Milieu sous chaque centre, sans `CartePiscine` : rectangle et distance euclidienne."""
    b = p.piscine.bassin
    dx = np.maximum(np.maximum(b.x_min - x[:, 0], x[:, 0] - b.x_max), 0.0)
    dy = np.maximum(np.maximum(b.y_min - x[:, 1], x[:, 1] - b.y_max), 0.0)
    dedans = (x[:, 0] > b.x_min) & (x[:, 0] < b.x_max) & (x[:, 1] > b.y_min) & (x[:, 1] < b.y_max)
    mouille = np.hypot(dx, dy) <= p.piscine.largeur_mouillee
    return np.where(dedans, Milieu.EAU, np.where(mouille, Milieu.MOUILLE, Milieu.SEC))


def pas_libre_attendu(p, zone, x, v, e, dt):
    """a = (U - v) / tau, ramenee a a_max ; U = facteur * s * e (spec § 2.4)."""
    milieux = [p.parametres_milieux[Milieu(m)] for m in zone]
    tau = np.array([q.relaxation for q in milieux])
    a_max = np.array([q.acceleration_max for q in milieux])
    u = p.facteur_vitesse * np.array([q.vitesse for q in milieux])[:, None] * e
    a = (u - v) / tau[:, None]
    norme = np.linalg.norm(a, axis=1)
    return v + dt * a * np.minimum(1.0, a_max / np.where(norme > 0, norme, np.inf))[:, None]


def observer(p):
    """Evacue toute la piscine et rend chaque appel au pas libre : (x, v, e, v_libre, dt)."""
    appels = []

    def espion(direction, zone, milieux, **options):
        reel = pas_libre_milieux(direction, zone, milieux, **options)

        def _vitesse(etat, dt):
            v_libre = reel(etat, dt)
            appels.append((etat.x.copy(), etat.v.copy(), direction(etat), v_libre, dt))
            return v_libre

        return _vitesse

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(scenario, "pas_libre_milieux", espion)
        resultat = scenario.simuler_piscine(p)
    assert np.all(np.isfinite(resultat.sorties))  # evacuation complete : tous les sols vus
    return appels


@pytest.fixture(scope="module", params=[1.0, 1.5], ids=["panique-1", "panique-1.5"])
def observation(request):
    """Evacuation de 20 agents, environ 6 s de calcul par facteur de panique.

    Le facteur 1,5 fait saturer l'adherence du mouille (seuil a_max * tau = 1,65 m/s),
    que le facteur de reference 1 n'atteint presque jamais.
    """
    p = parametres(n_agents=20, facteur_vitesse=request.param)
    return p, observer(p)


@pytest.mark.invariant
def test_pas_libre_identique_au_calcul_independant(observation):
    """Carte, parametres et facteur de panique branches comme le dit la spec.

    Mesure : 0,0 m/s au facteur 1 (4 230 pas), 2,8e-17 m/s au facteur 1,5 (3 005 pas).
    """
    p, appels = observation
    ecart = max(
        np.max(np.abs(pas_libre_attendu(p, zone_a_la_main(p, x), x, v, e, dt) - v_libre))
        for x, v, e, v_libre, dt in appels
    )
    assert ecart <= 1e-12


@pytest.mark.invariant
def test_adherence_bornee_dans_chaque_milieu(observation):
    """|a| <= a_max du sol sous l'agent, dans l'eau, sur le mouille et sur le sec.

    La borne porte sur le pas libre : apres projection, un contact peut accelerer
    davantage, comme une force de contact. Part des pas agent ou l'adherence sature
    (20 agents) : au facteur 1, eau 0 %, mouille 0,03 % (5 sur 19 597), sec 0 % ; au
    facteur 1,5, eau 8,9 %, mouille 1,9 %, sec 0 %.
    """
    p, appels = observation
    vus = dict.fromkeys(Milieu, 0)
    for x, v, _, v_libre, dt in appels:
        zone = zone_a_la_main(p, x)
        a = np.linalg.norm((v_libre - v) / dt, axis=1)
        for m in Milieu:
            sous = zone == m
            vus[m] += int(sous.sum())
            if sous.any():
                a_max = p.parametres_milieux[m].acceleration_max
                assert np.max(a[sous]) <= a_max * (1 + 1e-12), m.name
    assert all(n > 0 for n in vus.values()), vus


def test_vitesse_visee_selon_le_sol(observation):
    """Hors saturation, U = v + tau * a se relit : |U| = facteur * s du sol sous l'agent.

    Dans l'eau, l'agent vise 0,69 m/s (petit bain, eau calme, d'apres shirvani2020) ;
    sur les plages, 1,34 m/s (Weidmann 1993), le tout multiplie par le facteur de panique.
    """
    p, appels = observation
    relus = dict.fromkeys(Milieu, 0)
    for x, v, e, v_libre, dt in appels:
        zone = zone_a_la_main(p, x)
        for m in Milieu:
            q = p.parametres_milieux[m]
            a = (v_libre - v) / dt
            libres = (
                (zone == m)
                & (np.linalg.norm(e, axis=1) > 0)
                & (np.linalg.norm(a, axis=1) < q.acceleration_max * (1 - 1e-9))
            )
            if libres.any():
                u = v[libres] + q.relaxation * a[libres]
                np.testing.assert_allclose(
                    np.linalg.norm(u, axis=1), p.facteur_vitesse * q.vitesse, rtol=1e-9
                )
                relus[m] += int(libres.sum())
    assert all(n > 0 for n in relus.values()), relus


def test_milieu_lu_au_debut_du_pas():
    """Un pas qui chevauche une frontiere garde les parametres du sol de depart.

    C'est le choix consigne au journal du 21 octobre (erreur d'ordre 1 en dt). Avec les
    valeurs de C6, il est INVISIBLE : mouille et sec ont meme s et meme tau, et un agent
    lance ne sature pas a_max, donc les deux sols donnent le meme pas libre (mesure :
    aucun pas discriminant sur 20 agents). On donne donc au mouille le « tau long » de la
    spec § 2.4 (1 s, valeur illustrative) pour que le test puisse echouer, et on verifie
    qu'il DISCRIMINE : sur ces pas, le sol d'arrivee donnerait un autre pas libre.
    """
    milieux = lire_configuration(EXEMPLE)["parametres"]["parametres_milieux"]
    milieux = milieux | {"MOUILLE": milieux["MOUILLE"] | {"relaxation": 1.0}}
    p = parametres(n_agents=5, parametres_milieux=milieux)
    appels = observer(p)
    chevauchements, discriminants = 0, 0
    for x, v, e, v_libre, dt in appels:
        depart, arrivee = zone_a_la_main(p, x), zone_a_la_main(p, x + dt * v_libre)
        bord = depart != arrivee
        if not bord.any():
            continue
        chevauchements += int(bord.sum())
        args = (x[bord], v[bord], e[bord], dt)
        np.testing.assert_allclose(
            pas_libre_attendu(p, depart[bord], *args), v_libre[bord], rtol=0, atol=1e-12
        )
        ecart = np.abs(pas_libre_attendu(p, arrivee[bord], *args) - v_libre[bord])
        discriminants += int(np.sum(np.max(ecart, axis=1) > 1e-9))
    assert chevauchements > 0
    assert discriminants > 0


@pytest.fixture(scope="module")
def plages():
    """Valeurs de reference et deux departs a droite du bassin : mouille, puis sec."""
    p = parametres()
    b = p.piscine.bassin
    y = b.y_min + 1.0
    mouille = (b.x_max + 1.5, y)  # au milieu de la bande de 3 m
    sec = (b.x_max + 10.0, y)
    assert list(zone_a_la_main(p, np.array([mouille, sec]))) == [Milieu.MOUILLE, Milieu.SEC]
    return p, mouille, sec


class TestFreinageSurLesPlages:
    """Freinage d'un agent seul, sur la vraie carte et avec les valeurs de C6.

    Freiner sans saturer prend une distance v0 * tau, quel que soit a_max ; l'adherence
    ne compte qu'au-dela de v0 = a_max * tau, soit 1,65 m/s sur le mouille et 2,95 m/s
    sur le sec. Au-dela, d = v0^2 / (2 a_max) + a_max tau^2 / 2 (cf. `test_milieu.py`).
    """

    @staticmethod
    def freiner(p, x0, v0):
        """Lance un agent selon +y, sans guidage, et rend la distance parcourue en m."""
        libre = pas_libre_milieux(
            lambda etat: np.zeros((etat.n, 2)), CartePiscine(p.piscine), p.parametres_milieux
        )
        etat = State(x=np.array([x0]), v=np.array([[0.0, v0]]), r=np.array([p.rayon]))
        _, x, v = trajectoire(etat, p.dt, 6.0, libre, p.piscine.projeter)
        assert np.linalg.norm(v[-1]) < 1e-4  # arrete
        return x[-1, 0, 1] - x0[1]

    def test_a_la_vitesse_de_reference_le_mouille_freine_comme_le_sec(self, plages):
        """A 1,34 m/s, sous le seuil de 1,65 m/s : meme distance d'arret, au calcul pres.

        C'est pourquoi l'effet inertiel du mouille ne peut pas apparaitre au facteur de
        panique 1 hors des virages serres (commentaire du 25 octobre dans #26).
        Mesure : 0,6566 m sur les deux sols, soit v0 * (tau - dt), le schema semi-implicite.
        """
        p, mouille, sec = plages
        v0 = p.parametres_milieux[Milieu.MOUILLE].vitesse
        tau = p.parametres_milieux[Milieu.MOUILLE].relaxation
        d_mouille, d_sec = self.freiner(p, mouille, v0), self.freiner(p, sec, v0)
        assert d_mouille == pytest.approx(d_sec, abs=1e-12)
        assert d_mouille == pytest.approx(v0 * tau, abs=1.01 * v0 * p.dt)

    def test_au_dela_du_seuil_le_mouille_freine_plus_loin(self, plages):
        """A 2,5 m/s, l'adherence du mouille sature, pas celle du sec.

        Mesure : 1,339 m sur le mouille contre 1,225 m sur le sec, soit 9 % de plus.
        L'ecart reste modeste avec tau = 0,5 s : la relaxation pese autant que l'adherence.
        """
        p, mouille, sec = plages
        v0 = 2.5
        q_mouille, q_sec = p.parametres_milieux[Milieu.MOUILLE], p.parametres_milieux[Milieu.SEC]
        d_mouille, d_sec = self.freiner(p, mouille, v0), self.freiner(p, sec, v0)
        assert v0 > q_mouille.acceleration_max * q_mouille.relaxation
        assert v0 < q_sec.acceleration_max * q_sec.relaxation
        attendu = v0**2 / (2 * q_mouille.acceleration_max) + (
            q_mouille.acceleration_max * q_mouille.relaxation**2 / 2
        )
        assert d_mouille == pytest.approx(attendu, abs=v0 * p.dt)
        assert d_sec == pytest.approx(v0 * q_sec.relaxation, abs=1.01 * v0 * p.dt)
        assert d_mouille > d_sec
