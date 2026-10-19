"""Tests du schema d'integration semi-implicite, sans contrainte."""

import numpy as np
import pytest

from viscocrowd.core.integrator import (
    chute_libre,
    pas_semi_implicite,
    simuler,
    trajectoire,
)
from viscocrowd.core.state import GRAVITE, State
from viscocrowd.geometry.grille import paires_candidates
from viscocrowd.geometry.projection import ProjectionExclusion

TOLERANCE = 1e-6


def chute_libre_exacte(x0, v0, g, dt, n):
    """Solution EXACTE du schema discret semi-implicite apres n pas.

    On ne compare pas a la parabole continue : le schema a sa propre solution
    fermee, et c'est elle qui doit etre reproduite au bit pres. Comparer a la
    solution continue melangerait erreur de discretisation et erreur de code,
    et le test ne saurait plus distinguer les deux.

        v_n = v0 + n dt g
        x_n = x0 + n dt v0 + dt^2 g n(n+1)/2
    """
    v = v0 + n * dt * g
    x = x0 + n * dt * v0 + dt**2 * g * (n * (n + 1) / 2.0)
    return x, v


class TestChuteLibre:
    def test_reproduit_la_solution_exacte_du_schema(self):
        dt, n_pas = 1e-3, 500
        x0 = np.array([0.3, 0.5])
        v0 = np.array([0.1, -0.2])

        etat = State(
            x=x0.reshape(1, 2).copy(),
            v=v0.reshape(1, 2).copy(),
            r=np.array([0.05]),
        )
        for _ in range(n_pas):
            etat = pas_semi_implicite(etat, dt, chute_libre(GRAVITE))

        x_attendu, v_attendu = chute_libre_exacte(x0, v0, GRAVITE, dt, n_pas)

        np.testing.assert_allclose(etat.x[0], x_attendu, rtol=0, atol=1e-12)
        np.testing.assert_allclose(etat.v[0], v_attendu, rtol=0, atol=1e-12)
        assert etat.t == pytest.approx(n_pas * dt)

    def test_la_masse_n_influence_pas_la_trajectoire(self):
        """La masse se simplifie dans la formulation par minimisation.

        Elle n'apparait nulle part dans le schema : c'est une propriete du
        modele, pas un detail d'implementation, donc elle merite un test.
        """
        etat = State.single((0.0, 1.0), (0.5, 0.0))
        _, x, _ = trajectoire(etat, 1e-3, 1.0, chute_libre(GRAVITE))

        # Aucune API ne permet de passer une masse a l'integrateur : la
        # trajectoire est donc identique quelle que soit la masse supposee.
        assert x.shape == (1001, 1, 2)

    def test_gravite_nulle_donne_un_mouvement_rectiligne_uniforme(self):
        etat = State.single((0.0, 0.0), (1.0, 2.0))
        t, x, v = trajectoire(etat, 1e-2, 1.0, chute_libre(np.zeros(2)))

        attendu = np.broadcast_to(np.array([1.0, 2.0]), (t.size, 2))
        np.testing.assert_allclose(v[:, 0, :], attendu, atol=1e-14)
        np.testing.assert_allclose(x[:, 0, 0], t * 1.0, atol=1e-12)
        np.testing.assert_allclose(x[:, 0, 1], t * 2.0, atol=1e-12)


class TestGardeFous:
    @pytest.mark.parametrize("dt", [0.0, -1e-3])
    def test_pas_de_temps_non_positif_rejete(self, dt):
        etat = State.single((0.0, 0.0))
        with pytest.raises(ValueError, match="strictement positif"):
            pas_semi_implicite(etat, dt, chute_libre(GRAVITE))

    def test_rayon_negatif_rejete(self):
        with pytest.raises(ValueError, match="rayons"):
            State(
                x=np.zeros((1, 2)),
                v=np.zeros((1, 2)),
                r=np.array([-0.1]),
            )

    def test_formes_incoherentes_rejetees(self):
        with pytest.raises(ValueError, match="meme forme"):
            State(
                x=np.zeros((3, 2)),
                v=np.zeros((2, 2)),
                r=np.ones(3),
            )

    @pytest.mark.parametrize("champ", ["x", "v", "r"])
    @pytest.mark.parametrize("valeur", [np.nan, np.inf])
    def test_etat_non_fini_rejete(self, champ, valeur):
        tableaux = {"x": np.zeros((2, 2)), "v": np.zeros((2, 2)), "r": np.full(2, 0.1)}
        tableaux[champ] = tableaux[champ].copy()
        tableaux[champ].flat[1] = valeur
        with pytest.raises(ValueError, match="non finies"):
            State(**tableaux)

    def test_rayon_nan_rejete_alors_que_nan_inferieur_a_zero_est_faux(self):
        """`NaN <= 0` est faux : l'ancien controle de signe laissait passer un rayon NaN."""
        with pytest.raises(ValueError, match="non finies"):
            State(x=np.zeros((1, 2)), v=np.zeros((1, 2)), r=np.array([np.nan]))

    def test_pas_libre_qui_diverge_est_arrete(self):
        """Sans projection, la position libre devient l'etat suivant : elle est controlee."""
        etat = State.single((0.0, 0.0))
        with pytest.raises(ValueError, match="non finies"):
            pas_semi_implicite(etat, 1e-3, lambda e, _dt: np.full_like(e.v, np.inf))


class TestParametresNonFinis:
    """Le pas de temps et la duree sont des entrees comme les autres.

    Trou trouve en relecture de la PR #21 : `if dt <= 0.0` laissait passer NaN et
    +inf, puisque toute comparaison avec un NaN est fausse. C'est exactement le
    piege que la PR corrige pour les rayons — `NaN <= 0` est faux — mais il
    restait sur le pas de temps, deux lignes plus haut dans le meme fichier.

    Le pas se deroulait, les positions devenaient non finies, et le refus tombait
    plus loin en accusant « la vitesse libre, le guidage ». Le diagnostic
    designait donc une cause fausse.
    """

    @staticmethod
    def _etat():
        return State(x=np.array([[0.0, 0.0], [1.0, 0.0]]), v=np.zeros((2, 2)), r=np.full(2, 0.1))

    @pytest.mark.parametrize("dt", [np.nan, np.inf, -np.inf, 0.0, -1e-3])
    @pytest.mark.parametrize("avec_projection", [False, True], ids=["sans_proj", "avec_proj"])
    def test_pas_de_temps_non_fini_ou_negatif_rejete(self, dt, avec_projection):
        projection = ProjectionExclusion(tolerance=TOLERANCE) if avec_projection else None

        with pytest.raises(ValueError, match="pas de temps"):
            pas_semi_implicite(self._etat(), float(dt), lambda e, _dt: e.v, projection)

    @pytest.mark.parametrize("dt", [np.nan, np.inf])
    def test_le_message_designe_le_pas_de_temps_et_non_les_positions(self, dt):
        """Le diagnostic doit nommer la vraie cause, pas celle qu'on voit en aval."""
        with pytest.raises(ValueError) as echec:
            pas_semi_implicite(self._etat(), float(dt), lambda e, _dt: e.v)

        assert "pas de temps" in str(echec.value)
        assert "vitesse libre" not in str(echec.value)

    @pytest.mark.parametrize("duree", [np.nan, np.inf, -1.0])
    def test_duree_invalide_rejetee(self, duree):
        """`duree = -1` rendait le seul etat initial, sans rien signaler."""
        with pytest.raises(ValueError, match="duree"):
            list(simuler(self._etat(), 1e-3, float(duree), lambda e, _dt: e.v))

    def test_duree_nulle_rend_le_seul_etat_initial(self):
        """Cas limite legitime, a distinguer d'une duree negative : il reste accepte."""
        etats = list(simuler(self._etat(), 1e-3, 0.0, lambda e, _dt: e.v))

        assert len(etats) == 1
        assert etats[0].t == 0.0


class TestInstantNonFini:
    """L'instant fait partie de l'etat, donc de ce qui peut etre corrompu.

    Trou trouve en relecture de la PR #21 : `State` controlait x, v et r mais pas
    t. Un `t` non fini rend la projection d'un domaine MOBILE non finie a son
    tour (la matrice de rotation depend de t), et le message accusait alors les
    positions. Meme famille que le pas de temps : le diagnostic designait l'aval.
    """

    @pytest.mark.parametrize("t", [np.nan, np.inf, -np.inf])
    def test_instant_non_fini_rejete(self, t):
        with pytest.raises(ValueError, match="t doit etre un nombre fini"):
            State(
                x=np.array([[0.0, 0.0]]),
                v=np.zeros((1, 2)),
                r=np.full(1, 0.1),
                t=float(t),
            )

    def test_un_etat_valide_garde_son_instant(self):
        etat = State(x=np.array([[0.0, 0.0]]), v=np.zeros((1, 2)), r=np.full(1, 0.1), t=2.5)

        assert etat.t == 2.5


class TestDiagnosticNommeLAgent:
    """Le message doit nommer l'agent fautif, pas seulement le tableau.

    Sur une campagne a plusieurs centaines d'agents, « x est non fini » n'apprend
    rien d'exploitable : il faut relancer en instrumentant pour trouver lequel a
    diverge. L'indice est la seule information qui fasse gagner du temps, et il
    est connu au moment ou l'erreur est levee.
    """

    @staticmethod
    def _nuage_avec_un_fautif(indice, n=600, valeur=np.nan):
        x = np.zeros((n, 2))
        x[:, 0] = np.arange(n) * 0.5  # agents bien separes, aucun recouvrement
        x[indice, 1] = valeur
        return x, np.full(n, 0.1)

    def test_la_projection_nomme_l_agent(self):
        x, r = self._nuage_avec_un_fautif(437)

        with pytest.raises(ValueError, match="437"):
            ProjectionExclusion(tolerance=TOLERANCE)(x, r, 0.0)

    def test_l_etat_nomme_l_agent(self):
        x, r = self._nuage_avec_un_fautif(437)

        with pytest.raises(ValueError, match="437"):
            State(x=x, v=np.zeros_like(x), r=r)

    def test_la_recherche_de_paires_nomme_l_agent(self):
        x, r = self._nuage_avec_un_fautif(12, n=20)

        with pytest.raises(ValueError, match="12"):
            paires_candidates(x, r)

    def test_le_tableau_fautif_est_nomme(self):
        """x, v et r sont distingues : on sait quelle grandeur a diverge."""
        x = np.zeros((3, 2))
        v = np.zeros((3, 2))
        v[1, 0] = np.nan

        with pytest.raises(ValueError, match=r"^v contient"):
            State(x=x, v=v, r=np.full(3, 0.1))

    def test_plusieurs_agents_fautifs_sont_comptes_sans_tout_lister(self):
        """Une divergence touche souvent toute la foule : le message doit rester lisible."""
        x = np.full((300, 2), np.nan)

        with pytest.raises(ValueError, match="et 295 autres") as echec:
            State(x=x, v=np.zeros_like(x), r=np.full(300, 0.1))

        assert "sur 300" in str(echec.value)


class TestImmuabiliteReelle:
    """`frozen=True` ne protege que les attributs, pas le CONTENU des tableaux.

    Issue #17. La docstring de `State` promettait qu'un etat produit ne peut plus
    changer, « ce qui evite les mutations accidentelles d'un historique de
    trajectoires, source classique de resultats faux et difficiles a
    diagnostiquer ». La promesse etait fausse : `etat.r[0] = 99` passait, et
    comme `advanced()` partage le tableau des rayons, toute la trajectoire
    changeait d'un seul coup.

    Le defaut etait silencieux tant que personne ne modifiait un tableau sur
    place. Il se serait reveille au premier scenario qui le fait — rayons
    variables, agents sortis retires — en corrompant l'historique sans rien
    signaler.
    """

    def test_ecrire_dans_un_etat_leve_au_lieu_de_corrompre(self):
        etat = State.single((0.0, 0.0), rayon=0.1)

        for tableau in (etat.x, etat.v, etat.r):
            with pytest.raises(ValueError, match="read-only"):
                tableau[0] = 99.0

    def test_modifier_un_etat_ulterieur_ne_touche_plus_au_precedent(self):
        """Le cas exact de l'issue : les rayons sont partages entre etats."""
        e0 = State.single((0.0, 0.0), rayon=0.1)
        e1 = e0.advanced(x=np.array([[1.0, 0.0]]), v=np.zeros((1, 2)), t=0.1)

        with pytest.raises(ValueError, match="read-only"):
            e1.r[0] = 99.0

        assert e0.r[0] == pytest.approx(0.1)

    def test_le_tableau_des_rayons_reste_partage_puisqu_il_est_gele(self):
        """On ne recopie pas les rayons a chaque pas : geler suffit a les proteger.

        C'est le point qui rend la correction gratuite en memoire sur une
        trajectoire longue.
        """
        e0 = State.single((0.0, 0.0), rayon=0.1)
        e1 = e0.advanced(x=np.array([[1.0, 0.0]]), v=np.zeros((1, 2)), t=0.1)

        assert e1.r is e0.r
        assert not e1.r.flags.writeable

    def test_modifier_le_tableau_donne_au_constructeur_ne_change_plus_l_etat(self):
        """Second cas de l'issue : l'appelant gardait une reference modifiable."""
        x_init = np.array([[0.0, 0.0]])
        v_init = np.zeros((1, 2))
        r_init = np.array([0.1])

        etat = State(x=x_init, v=v_init, r=r_init)
        x_init[0, 0] = 5.0
        v_init[0, 1] = 7.0
        r_init[0] = 0.9

        assert etat.x[0, 0] == pytest.approx(0.0)
        assert etat.v[0, 1] == pytest.approx(0.0)
        assert etat.r[0] == pytest.approx(0.1)

    @pytest.mark.parametrize("champ", ["x", "v", "r"])
    @pytest.mark.parametrize("non_contigue", [False, True])
    def test_une_vue_en_lecture_seule_reste_isolee_de_sa_base(self, champ, non_contigue):
        """Le drapeau de la vue ne protege pas la memoire detenue par l'appelant."""
        tableaux = {
            "x": np.array([[1.0, 2.0], [3.0, 4.0]]),
            "v": np.zeros((2, 2)),
            "r": np.array([0.1, 0.2]),
        }
        attendu = tableaux[champ].copy()
        origine = np.repeat(attendu, 2, axis=0) if non_contigue else attendu.copy()
        vue = origine[::2] if non_contigue else origine.view()
        vue.setflags(write=False)
        tableaux[champ] = vue

        etat = State(**tableaux)
        origine.flat[0] = 99.0

        np.testing.assert_array_equal(getattr(etat, champ), attendu)
        assert not getattr(etat, champ).flags.writeable

    def test_modifier_la_base_des_rayons_preserve_tout_l_historique(self):
        origine = np.array([0.1])
        vue = origine.view()
        vue.setflags(write=False)
        e0 = State(x=np.zeros((1, 2)), v=np.zeros((1, 2)), r=vue)
        e1 = e0.advanced(x=np.array([[1.0, 0.0]]), v=np.zeros((1, 2)), t=0.1)
        e2 = e1.advanced(x=np.array([[2.0, 0.0]]), v=np.zeros((1, 2)), t=0.2)

        origine[0] = 99.0

        for etat in (e0, e1, e2):
            np.testing.assert_array_equal(etat.r, [0.1])
        assert e0.r is e1.r is e2.r

    @pytest.mark.parametrize("champ", ["x", "v"])
    def test_advanced_isole_aussi_les_vues_externes(self, champ):
        e0 = State.single((0.0, 0.0))
        origine = np.array([[1.0, 2.0]])
        vue = origine.view()
        vue.setflags(write=False)
        tableaux = {"x": np.zeros((1, 2)), "v": np.zeros((1, 2))}
        tableaux[champ] = vue

        e1 = e0.advanced(**tableaux, t=0.1)
        origine[0, 0] = 99.0

        np.testing.assert_array_equal(getattr(e1, champ), [[1.0, 2.0]])

    def test_un_etat_reste_lisible_et_calculable(self):
        """Garde-fou : geler ne doit rien casser de l'usage normal."""
        etat = State.single((1.0, 2.0), vitesse=(3.0, 4.0), rayon=0.1)

        assert etat.n == 1
        assert float(np.sum(etat.v**2)) == pytest.approx(25.0)
        np.testing.assert_allclose(etat.x + etat.v, [[4.0, 6.0]])

    def test_une_trajectoire_complete_reste_gelee(self):
        """Chaque etat de l'historique est protege, pas seulement le dernier."""
        etats = list(
            simuler(
                State.single((0.0, 0.5)),
                dt=1e-3,
                duree=0.05,
                vitesse_libre=chute_libre(GRAVITE),
            )
        )

        assert len(etats) > 10
        for etat in etats:
            assert not etat.x.flags.writeable
            assert not etat.v.flags.writeable
            assert not etat.r.flags.writeable
