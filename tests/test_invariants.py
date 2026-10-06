"""Invariants physiques du moteur.

Ces tests sont la garde rapprochee du projet : ils tournent a chaque pull
request et rendent une regression physique impossible a fusionner. Ils
correspondent aux criteres de validation exiges par les consignes du module —
non-sortie du domaine, comportement asymptotique, energie — et chacun produit
un NOMBRE, pas une impression visuelle.
"""

import numpy as np
import pytest

from viscocrowd.core.integrator import chute_libre, trajectoire
from viscocrowd.core.state import GRAVITE, State
from viscocrowd.geometry.boite import BoiteTournante
from viscocrowd.observables.energie import ecart_entrainement, energie_mecanique
from viscocrowd.scenarios.bille_boite import ParametresBille, simuler_bille

# Tolerance de la contrainte de confinement. La projection est exacte par
# construction, donc seule l'erreur d'arrondi flottant subsiste.
TOLERANCE_CONTRAINTE = 1e-14


@pytest.mark.invariant
class TestConfinement:
    """La bille ne peut pas sortir de la boite, quel que soit dt."""

    @pytest.mark.parametrize("dt", [1e-2, 1e-3, 1e-4])
    def test_contrainte_respectee_a_la_precision_machine(self, dt):
        resultat = simuler_bille(ParametresBille(dt=dt, duree=5.0))
        assert resultat.violation_max() < TOLERANCE_CONTRAINTE

    def test_confinement_tient_meme_a_pas_de_temps_grossier(self):
        """Propriete remarquable du schema par projection.

        Un schema a rebond explicite laisse une particule rapide traverser une
        paroi entre deux pas. Ici la position est projetee a chaque pas : le
        confinement ne depend pas de dt. On le verifie avec un dt volontairement
        absurde, dix fois trop grand.
        """
        resultat = simuler_bille(ParametresBille(dt=1e-1, duree=5.0))
        assert resultat.violation_max() < TOLERANCE_CONTRAINTE

    def test_vitesse_initiale_tres_grande_reste_confinee(self):
        boite = BoiteTournante(demi_largeur=1.0, omega=0.0)
        etat = State.single((0.0, 0.0), (500.0, 300.0), rayon=0.05)

        _, x, _ = trajectoire(
            etat,
            dt=1e-2,
            duree=2.0,
            vitesse_libre=chute_libre(GRAVITE),
            projection=boite.projeter,
        )

        rayons = np.array([0.05])
        violation = max(boite.violation(x[p], rayons, 0.0) for p in range(x.shape[0]))
        assert violation < TOLERANCE_CONTRAINTE


@pytest.mark.invariant
class TestEnergie:
    def test_energie_non_croissante_en_boite_fixe(self):
        """Avec omega = 0, aucune paroi ne travaille : l'energie ne peut que baisser.

        En vol libre le schema semi-implicite la fait decroitre de exactement
        (1/2) dt^2 |g|^2 par pas, et chaque choc mou en dissipe une part. Une
        remontee spontanee signalerait une erreur dans la relecture de la
        vitesse apres projection.
        """
        resultat = simuler_bille(ParametresBille(omega=0.0, dt=1e-3, duree=10.0))

        energie = energie_mecanique(resultat.x, resultat.v, masse=resultat.parametres.masse)
        variations = np.diff(energie)

        assert np.max(variations) < 1e-9, (
            f"l'energie remonte de {np.max(variations):.3e} J entre deux pas"
        )

    def test_energie_dissipee_par_les_chocs(self):
        """La dissipation doit etre substantielle, pas seulement non positive.

        Sans ce test, une implementation qui gelerait la bille sur place
        passerait le test precedent sans rien simuler.
        """
        resultat = simuler_bille(ParametresBille(omega=0.0, dt=1e-3, duree=10.0))
        energie = energie_mecanique(resultat.x, resultat.v, masse=resultat.parametres.masse)

        dissipation = energie[0] - energie[-1]
        assert dissipation > 0.1, f"dissipation negligeable : {dissipation:.3e} J"


@pytest.mark.invariant
class TestComportementAsymptotique:
    """Comportement en temps long, et son domaine de validite.

    Le sujet d'introduction annonce qu'apres dissipation « la bille doit se
    stabiliser dans un coin de la boite et tourner solidairement avec elle ».
    Nos simulations montrent que ce n'est vrai que dans le regime ou la force
    centrifuge domine la gravite, soit omega^2 R >~ g. Les parametres suggeres
    par le sujet (omega = 1 rad/s, R = 1 m) donnent omega^2 R / g = 0,10 : la
    gravite y domine d'un facteur dix, et la bille glisse le long des parois
    en degringolant de coin en coin au fil de la rotation.

    Les deux regimes sont testes separement : c'est la frontiere entre eux qui
    est la conclusion physique, pas l'un des deux pris isolement.
    """

    # omega^2 R / g = 2,55 : la force centrifuge l'emporte.
    OMEGA_CENTRIFUGE = 5.0
    # omega^2 R / g = 0,10 : la gravite l'emporte (valeur suggeree par le sujet).
    OMEGA_GRAVITAIRE = 1.0

    def _ecart_final(self, omega, dt=1e-3, duree=20.0):
        resultat = simuler_bille(ParametresBille(omega=omega, dt=dt, duree=duree))
        v_solide = np.stack(
            [resultat.boite.vitesse_entrainement(resultat.x[p]) for p in range(resultat.t.size)]
        )
        ecart = ecart_entrainement(resultat.v, v_solide)
        derniers = resultat.t >= resultat.t[-1] - 1.0
        return float(np.mean(ecart[derniers])), resultat

    def test_entrainement_en_regime_centrifuge(self):
        """A omega eleve, v converge vers omega * x_perpendiculaire."""
        ecart, _ = self._ecart_final(self.OMEGA_CENTRIFUGE)
        assert ecart < 0.05, f"ecart moyen a l'entrainement : {ecart:.3e} m/s"

    def test_pas_d_entrainement_en_regime_gravitaire(self):
        """A omega = 1 rad/s, la bille N'EST PAS entrainee.

        Ce test fixe une conclusion physique, pas une tolerance arbitraire :
        si une modification du moteur le faisait passer, c'est que la
        dissipation ou la gravite aurait ete cassee quelque part.
        """
        ecart, _ = self._ecart_final(self.OMEGA_GRAVITAIRE)
        assert ecart > 0.5, (
            f"la bille est entrainee a omega = 1 rad/s (ecart {ecart:.3e} m/s), "
            "ce qui contredit la domination de la gravite dans ce regime"
        )

    def test_position_finale_est_un_coin_en_regime_centrifuge(self):
        """En regime centrifuge, |x| final vaut exactement sqrt(2) * (R - r)."""
        _, resultat = self._ecart_final(self.OMEGA_CENTRIFUGE)

        p = resultat.parametres
        rayon_coin = np.sqrt(2.0) * (p.demi_largeur - p.rayon)
        rayon_final = float(np.linalg.norm(resultat.x[-1, 0]))

        assert abs(rayon_final - rayon_coin) < 1e-3, (
            f"|x| final = {rayon_final:.6f} m, coin attendu a {rayon_coin:.6f} m"
        )

    def test_les_deux_coordonnees_locales_sont_collees_aux_parois(self):
        """Un coin, c'est DEUX contraintes actives, pas une seule.

        Verifier qu'une seule coordonnee touche une paroi ne distingue pas un
        coin d'un simple glissement le long d'un bord.
        """
        _, resultat = self._ecart_final(self.OMEGA_CENTRIFUGE)

        theta_final = resultat.boite.theta(float(resultat.t[-1]))
        rotation = np.array(
            [
                [np.cos(-theta_final), -np.sin(-theta_final)],
                [np.sin(-theta_final), np.cos(-theta_final)],
            ]
        )
        position_locale = rotation @ resultat.x[-1, 0]

        p = resultat.parametres
        marge = p.demi_largeur - p.rayon
        ecarts = np.abs(np.abs(position_locale) - marge)

        assert np.max(ecarts) < 1e-3, (
            f"position locale {position_locale}, ecarts aux parois {ecarts}"
        )


@pytest.mark.invariant
class TestCasDegeneres:
    def test_gravite_nulle_boite_fixe_conserve_l_energie_entre_chocs(self):
        boite = BoiteTournante(demi_largeur=1.0, omega=0.0)
        etat = State.single((0.0, 0.0), (1.0, 0.3), rayon=0.05)

        _, x, v = trajectoire(
            etat,
            dt=1e-3,
            duree=0.5,
            vitesse_libre=chute_libre(np.zeros(2)),
            projection=boite.projeter,
        )

        energie = energie_mecanique(x, v, gravite=np.zeros(2))
        # Avant le premier choc, l'energie cinetique est strictement constante.
        np.testing.assert_allclose(energie[:100], energie[0], rtol=1e-12)

    def test_rayon_proche_de_la_demi_largeur_confine_la_bille_au_centre(self):
        """Si r -> R, l'espace admissible se reduit au voisinage du centre.

        Attention : il se reduit a un CARRE de demi-largeur (R - r), pas a un
        point. Le deplacement maximal depuis le centre vaut donc la diagonale
        de ce carre, sqrt(2) * (R - r). Exiger (R - r) ferait echouer un
        moteur pourtant correct.
        """
        rayon, demi_largeur = 0.999, 1.0
        resultat = simuler_bille(
            ParametresBille(
                rayon=rayon,
                demi_largeur=demi_largeur,
                duree=1.0,
                dt=1e-3,
                position_initiale=(0.0, 0.0),
            )
        )
        deplacement = np.max(np.linalg.norm(resultat.x[:, 0] - resultat.x[0, 0], axis=-1))
        diagonale = np.sqrt(2.0) * (demi_largeur - rayon)

        assert deplacement <= diagonale + 1e-12, (
            f"deplacement {deplacement:.6e} m au-dela de la diagonale {diagonale:.6e} m"
        )


@pytest.mark.invariant
def test_convergence_en_pas_de_temps():
    """Les conclusions qualitatives doivent etre stables quand dt diminue.

    On compare l'etat final a dt, dt/2 et dt/4. Les chocs sont des evenements
    discontinus, donc on ne peut pas exiger une convergence a la precision
    machine : on exige que la bille finisse au MEME coin, ce qui est la
    conclusion physique du scenario.
    """
    positions_finales = []
    for dt in (4e-3, 2e-3, 1e-3):
        resultat = simuler_bille(ParametresBille(dt=dt, duree=20.0))
        theta = resultat.boite.theta(float(resultat.t[-1]))
        rotation = np.array(
            [
                [np.cos(-theta), -np.sin(-theta)],
                [np.sin(-theta), np.cos(-theta)],
            ]
        )
        positions_finales.append(rotation @ resultat.x[-1, 0])

    signes = [np.sign(p) for p in positions_finales]
    assert all(np.array_equal(s, signes[0]) for s in signes), (
        f"le coin d'arrivee depend de dt : {positions_finales}"
    )
