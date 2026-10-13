"""Le verdict de `viscocrowd valider-moteur` et son code de retour.

La commande affichait ses mesures et rendait toujours 0 : une regression du
moteur aurait donc laisse la CI verte. Ces tests portent sur la decision
elle-meme, pas sur les quatorze secondes de simulation qui la precedent — le
parcours complet est exerce par le job « Reproductibilite des figures ».
"""

import numpy as np
import pytest

from viscocrowd.cli import conclure, hors_seuil


class TestHorsSeuil:
    def test_une_valeur_sous_le_seuil_ne_produit_aucun_message(self):
        assert hors_seuil("recouvrement", 1e-9, 1e-6) is None

    def test_une_valeur_egale_au_seuil_passe(self):
        """La tolerance est le recouvrement ACCEPTE, pas celui qui est refuse."""
        assert hors_seuil("recouvrement", 1e-6, 1e-6) is None

    def test_une_valeur_au_dessus_du_seuil_est_signalee(self):
        message = hors_seuil("recouvrement", 2e-6, 1e-6)

        assert message is not None
        assert "recouvrement" in message
        assert "2.000e-06" in message  # la valeur mesuree figure dans le message
        assert "1.0e-06" in message  # et le seuil qu'elle depasse

    def test_un_nan_compte_comme_un_echec(self):
        """Un NaN echoue toutes les comparaisons : il ne doit pas passer pour bon.

        C'est le piege de `if valeur > seuil` : NaN > seuil est faux, donc un
        critere devenu NaN aurait ete declare conforme.
        """
        assert hors_seuil("energie", float(np.nan), 1e-12, "J") is not None

    def test_un_infini_compte_comme_un_echec(self):
        assert hors_seuil("energie", float(np.inf), 1e-12, "J") is not None

    def test_l_unite_est_reprise_telle_quelle(self):
        message = hors_seuil("remontee d'energie", 1.0, 0.0, "J")

        assert message is not None
        assert message.endswith("J")


class TestConclure:
    def test_aucun_echec_rend_zero(self, capsys):
        assert conclure([]) == 0
        assert "reussie" in capsys.readouterr().out

    def test_un_seul_echec_rend_un(self, capsys):
        assert conclure(["recouvrement : 2.000e-06 m > seuil 1.0e-06 m"]) == 1

        sortie = capsys.readouterr().out
        assert "ECHEC" in sortie
        assert "recouvrement" in sortie  # le critere fautif est nomme

    @pytest.mark.parametrize("nombre", [1, 2, 5])
    def test_tous_les_echecs_sont_rapportes_pas_seulement_le_premier(self, nombre, capsys):
        """On veut la liste complete : corriger un critere a la fois ferait perdre du temps."""
        echecs = [f"critere {k}" for k in range(nombre)]

        assert conclure(echecs) == 1

        sortie = capsys.readouterr().out
        for echec in echecs:
            assert echec in sortie
        assert f"{nombre} critere(s)" in sortie
