"""Tests de la mesure du debit, sur des positions construites a la main."""

import numpy as np
import pytest

from viscocrowd.observables import weidmann
from viscocrowd.observables.debit import (
    Franchissements,
    cote,
    debit_specifique,
    franchissements,
)

# Une porte horizontale de 1 m, de (0, 0) a (1, 0). En marchant de a vers b,
# la gauche est vers le haut (y > 0) et la droite vers le bas (y < 0).
A = np.array([0.0, 0.0])
B = np.array([1.0, 0.0])


class TestCote:
    def test_point_au_dessus_est_a_gauche(self):
        assert cote(np.array([0.5, 2.0]), A, B) > 0

    def test_point_en_dessous_est_a_droite(self):
        assert cote(np.array([0.5, -2.0]), A, B) < 0

    def test_point_sur_la_droite_donne_zero(self):
        assert cote(np.array([0.5, 0.0]), A, B) == 0

    def test_inverser_a_et_b_inverse_les_cotes(self):
        """Gauche et droite dependent du sens de marche, pas du segment seul."""
        x = np.array([0.5, 2.0])
        assert cote(x, A, B) == -cote(x, B, A)

    def test_valeur_proportionnelle_a_la_distance(self):
        """Divise par la longueur du segment, le resultat est la distance a la droite."""
        a, b = np.array([0.0, 0.0]), np.array([3.0, 0.0])  # segment de 3 m
        assert cote(np.array([1.0, 2.0]), a, b) / 3.0 == 2.0

    def test_trajectoire_complete_traitee_d_un_coup(self):
        """Forme (P, N, 2) en entree, (P, N) en sortie : aucune boucle Python."""
        x = np.zeros((5, 3, 2))
        x[..., 1] = np.array([1.0, -1.0, 0.0])  # trois agents : dessus, dessous, sur
        signes = np.sign(cote(x, A, B))

        assert signes.shape == (5, 3)
        np.testing.assert_array_equal(signes, np.broadcast_to([1.0, -1.0, 0.0], (5, 3)))


def trajectoire_par_points(points: list[list[tuple[float, float]]], dt: float = 0.1):
    """Construit (t, x) a partir des positions successives de chaque agent.

    points[k] est la liste des positions de l'agent k, une par instant.
    """
    x = np.array(points, dtype=float).transpose(1, 0, 2)  # (N, P, 2) -> (P, N, 2)
    t = dt * np.arange(x.shape[0])
    return t, x


class TestFranchissements:
    def test_dix_agents_en_ligne_droite(self):
        """Cas de reference : on connait d'avance le nombre ET l'instant des passages.

        Dix agents repartis le long de la porte descendent a 1 m/s depuis
        y = 0,55 m : ils croisent y = 0 a t = 0,55 s exactement, au milieu d'un
        pas de temps. L'interpolation doit retrouver cet instant.
        """
        dt, n_pas = 0.1, 11
        t = dt * np.arange(n_pas)
        abscisses = np.linspace(0.05, 0.95, 10)
        x = np.zeros((n_pas, 10, 2))
        x[..., 0] = abscisses
        x[..., 1] = 0.55 - 1.0 * t[:, None]

        passages = franchissements(t, x, A, B)

        assert passages.nombre == 10
        np.testing.assert_allclose(passages.instant, 0.55, atol=1e-12)
        np.testing.assert_array_equal(passages.sens, 1)  # du haut (gauche) vers le bas (droite)
        assert sorted(passages.agent.tolist()) == list(range(10))

    def test_agent_qui_passe_a_cote_de_la_porte_n_est_pas_compte(self):
        """Il traverse la DROITE, mais a x = 2 m, hors du segment [0, 1]."""
        t, x = trajectoire_par_points([[(2.0, 0.5), (2.0, -0.5)]])
        assert franchissements(t, x, A, B).nombre == 0

    def test_diagonale_qui_croise_dans_le_mur_n_est_pas_comptee(self):
        """Pourquoi on calcule la fraction du pas : savoir OU l'agent a croise la droite.

        Sur la seconde photo, l'agent est en face de la porte (x = 0,5). Mais il
        marche en diagonale : il croise y = 0 a 1/5 du trajet, donc a x = 1,3,
        dans le mur. Regarder seulement les photos le compterait a tort.
        """
        t, x = trajectoire_par_points([[(1.5, 0.2), (0.5, -0.8)]])
        assert franchissements(t, x, A, B).nombre == 0

    def test_diagonale_qui_croise_dans_la_porte_est_comptee(self):
        """Le cas inverse : les deux photos sont HORS de la porte (x = -0,4 puis 1,6),
        mais l'agent croise y = 0 a mi-trajet, a x = 0,6, en pleine porte."""
        t, x = trajectoire_par_points([[(-0.4, 0.5), (1.6, -0.5)]])
        passages = franchissements(t, x, A, B)

        assert passages.nombre == 1
        np.testing.assert_allclose(passages.instant, [0.05])  # mi-chemin entre 0 et 0,1 s

    def test_demi_tour_avant_la_ligne_n_est_pas_compte(self):
        t, x = trajectoire_par_points([[(0.5, 0.5), (0.5, 0.1), (0.5, 0.5)]])
        assert franchissements(t, x, A, B).nombre == 0

    def test_aller_retour_donne_deux_passages_de_sens_opposes(self):
        """Un agent repousse en arriere par la foule repasse la ligne dans l'autre sens."""
        t, x = trajectoire_par_points([[(0.5, 0.5), (0.5, -0.5), (0.5, 0.5)]])
        passages = franchissements(t, x, A, B)

        assert passages.nombre == 2
        np.testing.assert_array_equal(passages.sens, [1, -1])

    def test_arret_pile_sur_la_ligne_compte_une_seule_fois(self):
        t, x = trajectoire_par_points([[(0.5, 0.5), (0.5, 0.0), (0.5, 0.0), (0.5, -0.5)]])
        assert franchissements(t, x, A, B).nombre == 1

    def test_passages_tries_par_instant(self):
        """L'agent 0 passe apres l'agent 1 : la liste suit l'ordre du temps, pas des agents."""
        t, x = trajectoire_par_points(
            [
                [(0.5, 0.5), (0.5, 0.2), (0.5, -0.1)],  # passe entre t = 0,1 et 0,2 s
                [(0.3, 0.1), (0.3, -0.1), (0.3, -0.3)],  # passe entre t = 0 et 0,1 s
            ]
        )
        passages = franchissements(t, x, A, B)

        np.testing.assert_array_equal(passages.agent, [1, 0])
        assert np.all(np.diff(passages.instant) > 0)

    def test_aucun_agent_ne_bouge(self):
        t, x = trajectoire_par_points([[(0.5, 0.5)] * 5, [(0.5, -0.5)] * 5])
        assert franchissements(t, x, A, B).nombre == 0


def passages_construits(instants, sens=None) -> Franchissements:
    """Liste de passages ecrite a la main, pour tester le calcul du debit seul."""
    instants = np.asarray(instants, dtype=float)
    sens = np.ones(instants.size, dtype=int) if sens is None else np.asarray(sens)
    return Franchissements(agent=np.arange(instants.size), instant=instants, sens=sens)


class TestDebitSpecifique:
    def test_un_passage_par_seconde_par_une_porte_de_un_metre(self):
        """10 passages en 10 s par une porte de 1 m : 1 pers/m/s."""
        passages = passages_construits(np.arange(10) + 0.5)
        assert debit_specifique(passages, largeur=1.0, debut=0.0, fin=10.0) == 1.0

    def test_porte_deux_fois_plus_large_divise_le_debit_par_deux(self):
        """Memes 10 personnes, porte deux fois plus large : chaque metre de porte en
        fait passer deux fois moins, la porte est sous-utilisee.

        Le debit TOTAL (1 pers/s) ne change pas : seul le debit par metre baisse.
        En evacuation reelle, une porte plus large attire plus de monde et le debit
        par metre reste du meme ordre, d'ou l'interet de cette grandeur pour
        comparer des portes de largeurs differentes.
        """
        passages = passages_construits(np.arange(10) + 0.5)
        assert debit_specifique(passages, largeur=2.0, debut=0.0, fin=10.0) == 0.5

    def test_seuls_les_passages_de_la_fenetre_comptent(self):
        """Fenetre [2, 5[ : on garde 2,5 3,5 et 4,5 s, soit 3 passages en 3 s."""
        passages = passages_construits(np.arange(10) + 0.5)
        assert debit_specifique(passages, largeur=1.0, debut=2.0, fin=5.0) == 1.0

    def test_un_passage_en_marche_arriere_annule_un_passage(self):
        """4 sorties et 1 retour en arriere en 4 s : 3 personnes sont reellement sorties."""
        passages = passages_construits([0.5, 1.5, 2.5, 3.0, 3.5], sens=[1, 1, 1, -1, 1])
        assert debit_specifique(passages, largeur=1.0, debut=0.0, fin=4.0) == 3 / 4

    def test_chaine_complete_depuis_les_positions(self):
        """Des positions jusqu'au debit : 10 agents passent une porte de 1 m en 1,1 s."""
        dt, n_pas = 0.1, 11
        t = dt * np.arange(n_pas)
        x = np.zeros((n_pas, 10, 2))
        x[..., 0] = np.linspace(0.05, 0.95, 10)
        x[..., 1] = 0.55 - t[:, None]

        passages = franchissements(t, x, A, B)
        largeur = float(np.linalg.norm(B - A))

        assert debit_specifique(passages, largeur, debut=0.0, fin=1.0) == 10.0

    @pytest.mark.parametrize("largeur", [0.0, -1.0, np.nan, np.inf])
    def test_largeur_non_positive_rejetee(self, largeur):
        """Une largeur NaN rendait un debit NaN ; une largeur infinie, un debit nul."""
        with pytest.raises(ValueError, match="largeur"):
            debit_specifique(passages_construits([0.5]), largeur, 0.0, 1.0)

    def test_fenetre_vide_rejetee(self):
        with pytest.raises(ValueError, match="fenetre"):
            debit_specifique(passages_construits([0.5]), 1.0, debut=2.0, fin=2.0)

    @pytest.mark.parametrize(("debut", "fin"), [(np.nan, 1.0), (0.0, np.nan), (0.0, np.inf)])
    def test_fenetre_non_finie_rejetee(self, debut, fin):
        """Une borne NaN passait `fin <= debut` et rendait un debit NaN ou nul."""
        with pytest.raises(ValueError, match="fenetre"):
            debit_specifique(passages_construits([0.5]), 1.0, debut=debut, fin=fin)


class TestWeidmann:
    def test_vitesse_libre_a_faible_densite(self):
        """Presque seul, on marche a sa vitesse libre v0 = 1,34 m/s."""
        assert weidmann.vitesse(0.0) == pytest.approx(weidmann.V0)
        assert weidmann.vitesse(0.01) == pytest.approx(weidmann.V0, rel=1e-6)

    def test_plus_personne_n_avance_a_la_densite_maximale(self):
        assert weidmann.vitesse(weidmann.RHO_MAX) == 0.0
        assert weidmann.vitesse(7.0) == 0.0  # au-dela, pas de vitesse negative

    def test_la_vitesse_baisse_quand_la_foule_se_densifie(self):
        rho = np.linspace(0.1, weidmann.RHO_MAX, 50)
        assert np.all(np.diff(weidmann.vitesse(rho)) < 0)

    def test_le_debit_forme_une_colline(self):
        """Nul aux deux extremites, maximum d'environ 1,22 pers/m/s vers 1,75 pers/m^2.

        C'est la valeur publiee pour le diagramme de Weidmann, et elle tombe
        dans la fourchette de debit de goulot de la spec (1,2 a 1,4 pers/m/s).
        """
        rho = np.linspace(0.0, weidmann.RHO_MAX, 10_001)
        debit = weidmann.debit_specifique(rho)
        sommet = int(np.argmax(debit))

        assert debit[0] == 0.0
        assert debit[-1] == 0.0
        assert debit[sommet] == pytest.approx(1.22, abs=0.01)
        assert rho[sommet] == pytest.approx(1.75, abs=0.01)


class TestContactSansTraversee:
    """Toucher la ligne n'est pas la traverser.

    Repond a la relecture de la PR #9. La version precedente rangeait un agent
    pile sur la droite du cote DROIT : un agent venant de gauche qui touchait la
    ligne et repartait a gauche comptait donc deux faux passages, de sens
    opposes. Ils s'annulaient dans le debit net, mais faussaient le nombre brut
    de passages — et un agent dont la trajectoire se terminait sur la ligne
    comptait un faux passage positif, qui ne s'annulait pas, lui.

    Le defaut etait asymetrique : le cote droit, lui, ne produisait rien. Ces
    tests couvrent donc systematiquement les deux sens.
    """

    @pytest.mark.parametrize(
        ("nom", "y_depart"),
        [("depuis la gauche", 0.5), ("depuis la droite", -0.5)],
    )
    def test_toucher_la_ligne_et_repartir_du_meme_cote(self, nom, y_depart):
        t, x = trajectoire_par_points([[(0.5, y_depart), (0.5, 0.0), (0.5, y_depart)]])

        assert franchissements(t, x, A, B).nombre == 0, nom

    @pytest.mark.parametrize("y_depart", [0.5, -0.5])
    def test_toucher_la_ligne_et_s_y_arreter(self, y_depart):
        """La trajectoire se termine sur la ligne : l'agent ne l'a pas traversee."""
        t, x = trajectoire_par_points([[(0.5, y_depart), (0.5, 0.0)]])

        assert franchissements(t, x, A, B).nombre == 0

    @pytest.mark.parametrize("y_depart", [0.5, -0.5])
    def test_stationner_longuement_sur_la_ligne_sans_la_traverser(self, y_depart):
        t, x = trajectoire_par_points(
            [[(0.5, y_depart), (0.5, 0.0), (0.5, 0.0), (0.5, 0.0), (0.5, y_depart)]]
        )

        assert franchissements(t, x, A, B).nombre == 0

    def test_s_immobiliser_sur_la_ligne_avant_de_traverser_de_droite_a_gauche(self):
        """Le sens oppose du test deja present : un seul passage, vers la gauche."""
        t, x = trajectoire_par_points([[(0.5, -0.5), (0.5, 0.0), (0.5, 0.0), (0.5, 0.5)]])

        passages = franchissements(t, x, A, B)

        assert passages.nombre == 1
        np.testing.assert_array_equal(passages.sens, [-1])

    def test_l_instant_tombe_dans_l_intervalle_de_stationnement(self):
        """Interpolation sur tout l'intervalle : le passage est place a l'interieur."""
        t, x = trajectoire_par_points([[(0.5, 0.5), (0.5, 0.0), (0.5, 0.0), (0.5, -0.5)]], dt=1.0)

        passages = franchissements(t, x, A, B)

        assert passages.nombre == 1
        assert 0.0 < passages.instant[0] < 3.0

    def test_un_agent_pose_sur_la_ligne_au_depart_n_a_pas_de_cote_d_origine(self):
        """On ne sait pas d'ou il vient : on ne peut pas lui compter de passage."""
        t, x = trajectoire_par_points([[(0.5, 0.0), (0.5, 0.5)]])

        assert franchissements(t, x, A, B).nombre == 0

    def test_une_vraie_traversee_reste_comptee(self):
        """Garde-fou : la correction ne doit pas rendre la detection trop stricte."""
        t, x = trajectoire_par_points(
            [[(0.5, 0.5), (0.5, 0.0), (0.5, -0.5)], [(0.5, -0.5), (0.5, 0.0), (0.5, 0.5)]]
        )

        passages = franchissements(t, x, A, B)

        assert passages.nombre == 2
        np.testing.assert_array_equal(np.sort(passages.sens), [-1, 1])

    def test_toucher_la_ligne_hors_de_la_porte_ne_compte_pas_davantage(self):
        """Le contact a lieu dans le mur : ni faux passage, ni vrai."""
        t, x = trajectoire_par_points([[(2.0, 0.5), (2.0, 0.0), (2.0, -0.5)]])

        assert franchissements(t, x, A, B).nombre == 0


class TestPassageParLaDroiteHorsDeLaPorte:
    """Passer pile sur la droite, mais a cote de la porte, n'est pas franchir la porte.

    Repond a la seconde relecture de la PR #9. Ignorer l'echantillon pose sur la
    droite pour interpoler entre ses voisins strictement de part et d'autre
    fabriquait un croisement fictif DANS la porte, alors que l'agent avait
    traverse la droite en dehors. La porte va de (0, 0) a (1, 0).
    """

    @pytest.mark.parametrize(
        ("y_avant", "y_apres"),
        [(0.01, -0.01), (-0.01, 0.01)],
        ids=["de gauche a droite", "de droite a gauche"],
    )
    @pytest.mark.parametrize("x_hors", [1.01, -0.01], ids=["cote de b", "cote de a"])
    def test_passer_par_l_extremite_hors_de_la_porte_ne_compte_pas(self, y_avant, y_apres, x_hors):
        # Le premier et le dernier echantillon sont DANS l'aplomb de la porte.
        x_dedans = 0.99 if x_hors > 0.5 else 0.01
        t, x = trajectoire_par_points([[(x_dedans, y_avant), (x_hors, 0.0), (x_dedans, y_apres)]])

        assert franchissements(t, x, A, B).nombre == 0

    @pytest.mark.parametrize("y_avant", [0.01, -0.01])
    def test_meme_chose_apres_un_stationnement_hors_de_la_porte(self, y_avant):
        t, x = trajectoire_par_points(
            [[(0.99, y_avant), (1.01, 0.0), (1.01, 0.0), (1.02, 0.0), (0.99, -y_avant)]]
        )

        assert franchissements(t, x, A, B).nombre == 0

    @pytest.mark.parametrize("y_avant", [0.01, -0.01])
    def test_passer_par_un_point_de_la_porte_compte_une_fois(self, y_avant):
        """Garde-fou : le meme trajet, mais par l'interieur de la porte."""
        t, x = trajectoire_par_points([[(0.99, y_avant), (0.99, 0.0), (0.99, -y_avant)]], dt=1.0)

        passages = franchissements(t, x, A, B)

        assert passages.nombre == 1
        assert passages.instant[0] == pytest.approx(1.0)  # l'instant de l'echantillon sur la droite
        np.testing.assert_array_equal(passages.sens, [1 if y_avant > 0 else -1])

    def test_glisser_sur_la_droite_depuis_le_mur_jusque_dans_la_porte_compte(self):
        """L'agent touche la droite hors de la porte, la suit, puis la quitte dans la porte."""
        t, x = trajectoire_par_points([[(-0.5, 0.1), (-0.5, 0.0), (0.5, 0.0), (0.5, -0.1)]], dt=1.0)

        passages = franchissements(t, x, A, B)

        assert passages.nombre == 1
        # Il entre dans la porte en a = (0, 0), au quart du glissement de t=1 a t=2.
        assert passages.instant[0] == pytest.approx(1.5)

    def test_glisser_sur_la_droite_d_un_mur_a_l_autre_en_traversant_la_porte_compte(self):
        """Aucun echantillon dans la porte, mais le glissement la traverse entierement."""
        t, x = trajectoire_par_points([[(0.5, 0.1), (-0.5, 0.0), (1.5, 0.0), (0.5, -0.1)]], dt=1.0)

        passages = franchissements(t, x, A, B)

        assert passages.nombre == 1
        assert passages.instant[0] == pytest.approx(1.25)  # entre en a : (0 - (-0,5)) / 2 = 1/4

    def test_glisser_sur_la_droite_a_cote_de_la_porte_ne_compte_pas(self):
        t, x = trajectoire_par_points([[(1.2, 0.1), (1.2, 0.0), (2.0, 0.0), (2.0, -0.1)]])

        assert franchissements(t, x, A, B).nombre == 0

    def test_trajectoire_sans_contact_avec_la_droite_inchangee(self):
        """Pour une trajectoire qui ne tombe jamais pile sur la droite, le calcul est celui d'avant."""
        t, x = trajectoire_par_points([[(0.5, 0.3), (0.5, -0.1)]], dt=1.0)

        passages = franchissements(t, x, A, B)

        assert passages.instant[0] == pytest.approx(0.75)  # 0,3 / (0,3 + 0,1)


class TestSegmentInvalide:
    """Une ligne de mesure mal configuree doit se signaler, pas rendre zero passage.

    Repond a la relecture de la PR #9 : avec a == b, `cote` valait zero partout,
    aucun changement de cote n'etait detecte, et la mesure rendait une liste vide
    meme pour une trajectoire qui traverse. Resultat indiscernable d'une porte
    que personne n'emprunte.
    """

    def test_segment_de_longueur_nulle_rejete(self):
        t, x = trajectoire_par_points([[(0.5, 0.5), (0.5, -0.5)]])

        with pytest.raises(ValueError, match="longueur nulle"):
            franchissements(t, x, A, A)

    def test_segment_de_longueur_nulle_rejete_aussi_par_cote(self):
        with pytest.raises(ValueError, match="longueur nulle"):
            cote(np.array([0.5, 0.5]), A, A)

    @pytest.mark.parametrize("mauvais", [[np.nan, 0.0], [np.inf, 0.0], [0.0, -np.inf]])
    def test_extremite_non_finie_rejetee(self, mauvais):
        """Sans ce controle, tous les cotes deviennent NaN et aucun passage n'est vu."""
        t, x = trajectoire_par_points([[(0.5, 0.5), (0.5, -0.5)]])

        with pytest.raises(ValueError, match="finies"):
            franchissements(t, x, A, np.array(mauvais))


class TestDensiteInvalide:
    """Les fonctions de Weidmann rejettent ce qui n'est pas une densite.

    Repond a la relecture de la PR #9. Le masque `where=rho > 0` traitait toute
    densite NEGATIVE comme la limite a densite nulle : `vitesse(-1)` rendait la
    vitesse libre 1,34 m/s et `debit_specifique(-1)` rendait -1,34, deux valeurs
    d'apparence plausible pour une entree fautive. Un NaN ressortait en vitesse
    nulle, donc indiscernable d'une foule bloquee, et +inf declenchait un
    avertissement numerique en rendant NaN.
    """

    FONCTIONS = (weidmann.vitesse, weidmann.debit_specifique)

    @pytest.mark.parametrize("fonction", FONCTIONS)
    @pytest.mark.parametrize("rho", [-1.0, -1e-9, -1e3])
    def test_densite_negative_rejetee(self, fonction, rho):
        with pytest.raises(ValueError, match="positive"):
            fonction(rho)

    @pytest.mark.parametrize("fonction", FONCTIONS)
    @pytest.mark.parametrize("rho", [np.nan, np.inf, -np.inf])
    def test_densite_non_finie_rejetee(self, fonction, rho):
        """-inf est bien rejete, par le controle de finitude et non par celui de signe."""
        with pytest.raises(ValueError, match="finie"):
            fonction(rho)

    @pytest.mark.parametrize("fonction", FONCTIONS)
    def test_un_seul_element_fautif_dans_un_tableau_suffit(self, fonction):
        """Sinon une campagne entiere passerait avec une valeur aberrante au milieu."""
        with pytest.raises(ValueError):
            fonction(np.array([1.0, 2.0, -0.5, 3.0]))

    @pytest.mark.parametrize("fonction", FONCTIONS)
    def test_un_nan_dans_un_tableau_suffit(self, fonction):
        with pytest.raises(ValueError):
            fonction(np.array([1.0, np.nan, 3.0]))

    def test_les_densites_valides_gardent_leur_comportement(self):
        """La correction ne doit rien changer aux cas deja couverts par la PR."""
        assert weidmann.vitesse(0.0) == pytest.approx(weidmann.V0)
        assert weidmann.debit_specifique(0.0) == pytest.approx(0.0)
        assert weidmann.vitesse(weidmann.RHO_MAX) == 0.0
        assert weidmann.vitesse(2.0 * weidmann.RHO_MAX) == 0.0
        assert weidmann.debit_specifique(2.0 * weidmann.RHO_MAX) == 0.0

    def test_un_tableau_valide_est_traite_d_un_coup(self):
        rho = np.array([0.0, 1.0, 1.75, 5.4, 10.0])

        v = weidmann.vitesse(rho)

        assert v.shape == rho.shape
        assert np.all(np.isfinite(v))
        assert np.all(v >= 0.0)
