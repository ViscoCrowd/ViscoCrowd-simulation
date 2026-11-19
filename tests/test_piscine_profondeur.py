"""Profondeur variable dans la piscine : nageurs et guidage de l'eau (option)."""

import numpy as np
import pytest

from utilitaires import parametres_reduits
from viscocrowd.model.guidage_piscine import GuidagePiscine
from viscocrowd.model.profondeur import facteur_profondeur, profondeur
from viscocrowd.scenarios.piscine import EAU, simuler_piscine

GRAND_BAIN = {"gauche": 1.0, "droite": 1.0}


def test_profondeur_constante_de_reference_identique_a_sans_profondeur():
    a = simuler_piscine(parametres_reduits())
    b = simuler_piscine(parametres_reduits(profondeur={"gauche": 0.7, "droite": 0.7}))
    np.testing.assert_array_equal(a.x, b.x)
    np.testing.assert_array_equal(a.etats, b.etats)


def vitesse_nageur(**surcharges) -> float:
    """Plus grande vitesse des nageurs apres 2,5 s (regime etabli : 5 tau = 2,5 s).

    Six nageurs plutot qu'un : un nageur seul, tire pres du bord, sort parfois de l'eau
    avant la fenetre. A profondeur uniforme, tous ont le meme facteur.
    """
    r = simuler_piscine(parametres_reduits(duree=3.0, **surcharges))
    fenetre = (r.t >= 2.5)[:, None] & (r.etats == EAU)
    assert fenetre.sum() > 10
    return float(np.hypot(r.v[..., 0], r.v[..., 1])[fenetre].max())


def test_nageur_plus_lent_au_grand_bain():
    rapport = vitesse_nageur(profondeur=GRAND_BAIN) / vitesse_nageur()
    assert rapport == pytest.approx(float(facteur_profondeur(np.array([1.0]))[0]), rel=0.01)


def temps_eau_au_centre(p, facteur_eau=None) -> float:
    guidage = GuidagePiscine(
        p.piscine,
        p.parametres_milieux,
        p.rayon,
        p.pas_guidage,
        p.durees,
        p.facteur_vitesse,
        facteur_eau=facteur_eau,
    )
    b = p.piscine.bassin
    return float(guidage.temps(np.array([[(b.x_min + b.x_max) / 2, (b.y_min + b.y_max) / 2]]))[0])


def test_guidage_plus_long_au_grand_bain():
    p = parametres_reduits()

    def profond(points):
        return facteur_profondeur(profondeur(points, p.piscine.bassin, 1.0, 1.0))

    assert temps_eau_au_centre(p, profond) > temps_eau_au_centre(p)


@pytest.mark.parametrize(
    "valeur", [{"gauche": 3.0, "droite": 0.7}, {"gauche": 1.0}, {"gauche": 0.1, "droite": 0.7}]
)
def test_profondeur_mal_formee_ou_hors_domaine_refusee(valeur):
    with pytest.raises(ValueError, match="profondeur"):
        parametres_reduits(profondeur=valeur)


def test_profondeur_ecrite_dans_le_dictionnaire():
    p = parametres_reduits(profondeur={"gauche": 1.0, "droite": 0.7})
    assert p.en_dictionnaire()["profondeur"] == {"gauche": 1.0, "droite": 0.7}
