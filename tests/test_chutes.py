"""Tests du modele de chutes, effet domino, contournement et relevage."""

import numpy as np
import pytest

from viscocrowd.model.chutes import (
    GestionnaireChutes,
    ParametresChutes,
)


def test_parametres_chutes_valides():
    p = ParametresChutes()
    assert p.lambda_chute == 2.0
    assert p.lambda_domino == 4.0
    assert p.facteur_rayon_terre == 1.5
    assert p.mediane_relevage == 3.7


@pytest.mark.parametrize(
    ("champ", "valeur"),
    [
        ("lambda_chute", 0.0),
        ("lambda_chute", -1.0),
        ("lambda_domino", -0.5),
        ("facteur_rayon_terre", 0.9),  # < 1.0 refuse
        ("mediane_relevage", np.nan),
        ("sigma_relevage", np.inf),
        ("distance_perception", 0.0),
        ("force_contournement", -2.0),
    ],
)
def test_parametres_chutes_invalides_refuses(champ, valeur):
    with pytest.raises(ValueError):
        ParametresChutes(**{champ: valeur})


def test_initialisation_gestionnaire():
    g = GestionnaireChutes(n_agents=10, parametres=ParametresChutes(), graine=42)
    assert g.nombre_a_terre == 0
    assert len(g.historique) == 0
    assert g.a_terre.shape == (10,)
    assert not np.any(g.a_terre)

    with pytest.raises(ValueError, match="entier strictement positif"):
        GestionnaireChutes(n_agents=0, parametres=ParametresChutes(), graine=42)


def test_rayons_effectifs_augmentes_au_sol():
    p = ParametresChutes(facteur_rayon_terre=1.5)
    g = GestionnaireChutes(n_agents=3, parametres=p, graine=1)
    r_nom = np.array([0.2, 0.2, 0.2])

    np.testing.assert_array_equal(g.rayons_effectifs(r_nom), r_nom)

    g.faire_tomber(agent=1, instant=2.0, cause="glissade", position=(1.0, 2.0))
    r_eff = g.rayons_effectifs(r_nom)
    assert r_eff[0] == pytest.approx(0.2)
    assert r_eff[1] == pytest.approx(0.3)  # 1.5 * 0.2
    assert r_eff[2] == pytest.approx(0.2)
    assert g.nombre_a_terre == 1


def test_vitesse_desiree_nulle_pour_agent_au_sol():
    g = GestionnaireChutes(n_agents=2, parametres=ParametresChutes(), graine=1)
    x = np.array([[0.0, 0.0], [5.0, 0.0]])
    vd = np.array([[1.34, 0.0], [1.34, 0.0]])
    r_nom = np.array([0.2, 0.2])

    g.faire_tomber(agent=1, instant=1.0, cause="glissade", position=(5.0, 0.0))
    vd_eff = g.vitesses_desirees_effectives(x, vd, r_nom)
    np.testing.assert_array_equal(vd_eff[1], [0.0, 0.0])


def test_contournement_reactif_si_assez_eloigne():
    """Un agent debout en approche d'un agent au sol devie tangentiellement sa vitesse."""
    p = ParametresChutes(distance_perception=3.0, force_contournement=1.5)
    g = GestionnaireChutes(n_agents=2, parametres=p, graine=1)
    # Agent 0 debout a (0, 0), agent 1 au sol a (2, 0)
    x = np.array([[0.0, 0.0], [2.0, 0.0]])
    vd = np.array([[1.34, 0.0], [0.0, 0.0]])
    r_nom = np.array([0.2, 0.2])

    g.faire_tomber(agent=1, instant=0.0, cause="glissade", position=(2.0, 0.0))
    vd_eff = g.vitesses_desirees_effectives(x, vd, r_nom)

    # L'agent 0 doit avoir acquis une composante laterale (contournement)
    assert abs(vd_eff[0, 1]) > 0.1
    # La norme de la vitesse desiree reste inchangee (1.34 m/s)
    assert abs(np.linalg.norm(vd_eff[0]) - 1.34) < 1e-12


def test_pas_de_contournement_si_l_obstacle_est_derriere():
    """Un obstacle situe dans le dos de l'agent ne genere aucune deviation."""
    p = ParametresChutes(distance_perception=3.0)
    g = GestionnaireChutes(n_agents=2, parametres=p, graine=1)
    # Agent 0 debout a (3, 0) avancant vers +x, agent 1 au sol a (1, 0)
    x = np.array([[3.0, 0.0], [1.0, 0.0]])
    vd = np.array([[1.34, 0.0], [0.0, 0.0]])
    r_nom = np.array([0.2, 0.2])

    g.faire_tomber(agent=1, instant=0.0, cause="glissade", position=(1.0, 0.0))
    vd_eff = g.vitesses_desirees_effectives(x, vd, r_nom)

    # Aucune composante laterale
    assert vd_eff[0, 1] == 0.0
    assert vd_eff[0, 0] == 1.34


def test_chute_par_glissade_sur_exces_adherence():
    """Une acceleration demandee trop forte sur sol glissant declenche la glissade."""
    p = ParametresChutes(lambda_chute=100.0)  # Taux eleve pour certitude statistique
    g = GestionnaireChutes(n_agents=1, parametres=p, graine=42)

    x = np.array([[0.0, 0.0]])
    v = np.array([[0.0, 0.0]])
    vd = np.array([[2.5, 0.0]])  # Vitesse voulue 2.5 m/s
    tau = np.array([0.5])
    a_max = np.array([1.0])  # Sol glissant : a_max = 1.0 m/s^2, demande = 5.0 m/s^2
    r_nom = np.array([0.2])

    chutes = g.mettre_a_jour(
        instant=0.1,
        dt=0.1,
        x=x,
        v=v,
        vitesse_desiree=vd,
        a_max=a_max,
        tau=tau,
        rayons_nominaux=r_nom,
    )
    assert len(chutes) == 1
    assert chutes[0].agent == 0
    assert chutes[0].cause == "glissade"
    assert g.nombre_a_terre == 1


def test_effet_domino_si_trop_proche_pour_s_arreter():
    """Un agent rapide trop proche d'une personne a terre trebuche sur lui (effet domino)."""
    p = ParametresChutes(lambda_domino=100.0)  # Taux eleve pour declenchement quasi certain
    g = GestionnaireChutes(n_agents=2, parametres=p, graine=7)

    # Agent 0 au sol a (1.0, 0.0)
    g.faire_tomber(agent=0, instant=0.0, cause="glissade", position=(1.0, 0.0))

    # Agent 1 arrive a v = 2.0 m/s a x = 0.6 m (distance de bord 0.4 m - 0.2 - 0.3 = -0.1 m)
    # d_arret = v^2 / (2 * a_max) = 4 / (2 * 2.0) = 1.0 m > distance restante
    x = np.array([[1.0, 0.0], [0.6, 0.0]])
    v = np.array([[0.0, 0.0], [2.0, 0.0]])
    vd = np.array([[0.0, 0.0], [2.0, 0.0]])
    a_max = np.array([2.0, 2.0])
    tau = np.array([0.5, 0.5])
    r_nom = np.array([0.2, 0.2])

    chutes = g.mettre_a_jour(
        instant=0.05,
        dt=0.05,
        x=x,
        v=v,
        vitesse_desiree=vd,
        a_max=a_max,
        tau=tau,
        rayons_nominaux=r_nom,
    )
    assert any(c.agent == 1 and c.cause == "domino" for c in chutes)
    assert g.nombre_a_terre == 2


def test_relevage_apres_duree_ecoulee():
    """Un agent au sol se releve des que son temps de relevage est depasse."""
    g = GestionnaireChutes(n_agents=1, parametres=ParametresChutes(), graine=123)
    g.faire_tomber(agent=0, instant=1.0, cause="glissade", position=(0.0, 0.0))
    duree = g.historique[0].duree_relevage

    x = np.array([[0.0, 0.0]])
    v = np.array([[0.0, 0.0]])
    vd = np.array([[1.34, 0.0]])
    a_max = np.array([5.0])
    tau = np.array([0.5])
    r_nom = np.array([0.2])

    # Avant expiration : toujours a terre
    g.mettre_a_jour(
        instant=1.0 + duree / 2,
        dt=0.01,
        x=x,
        v=v,
        vitesse_desiree=vd,
        a_max=a_max,
        tau=tau,
        rayons_nominaux=r_nom,
    )
    assert g.nombre_a_terre == 1

    # Apres expiration : releve
    g.mettre_a_jour(
        instant=1.0 + duree + 0.01,
        dt=0.01,
        x=x,
        v=v,
        vitesse_desiree=vd,
        a_max=a_max,
        tau=tau,
        rayons_nominaux=r_nom,
    )
    assert g.nombre_a_terre == 0
    assert not g.a_terre[0]


def test_distribution_relevage_mediane_sourcer_becker():
    """La mediane empirique des durees de relevage retrouve 3,7 s (Becker et al. 2016)."""
    p = ParametresChutes(mediane_relevage=3.7, sigma_relevage=0.5)
    g = GestionnaireChutes(n_agents=1, parametres=p, graine=999)

    durees = []
    for k in range(300):
        # Forcer des chutes pour accumuler des tirages
        g._a_terre[0] = False
        g.faire_tomber(agent=0, instant=float(k), cause="test", position=(0.0, 0.0))
        durees.append(g.historique[-1].duree_relevage)

    mediane_observee = float(np.median(durees))
    # Ecart relatif inferieur a 10 % avec 300 tirages
    assert abs(mediane_observee - 3.7) < 0.35


def test_reproductibilite_stochastique_avec_graine():
    """Deux gestionnaires a meme graine tirent exactement les memes durees."""
    g1 = GestionnaireChutes(n_agents=3, parametres=ParametresChutes(), graine=2026)
    g2 = GestionnaireChutes(n_agents=3, parametres=ParametresChutes(), graine=2026)

    g1.faire_tomber(agent=0, instant=0.0, cause="glissade", position=(0.0, 0.0))
    g2.faire_tomber(agent=0, instant=0.0, cause="glissade", position=(0.0, 0.0))

    assert g1.historique[0].duree_relevage == g2.historique[0].duree_relevage
