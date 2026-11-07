"""Balayages E3/E4 de la piscine (M6) : appariement, temoin, cache et commande.

La plupart des tests remplacent `mesurer` par une mesure factice qui lit les
parametres recus : on verifie ainsi ce que le balayage simule, et combien de fois,
sans payer une evacuation par cas. Les tests marques « simulation reelle » justifient
les deux raccourcis du module sur de vraies evacuations de quelques agents.
"""

import json
import math
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
import yaml

import viscocrowd.scenarios.balayage_piscine as balayage
from viscocrowd.cli import main
from viscocrowd.io.configuration import lire_configuration
from viscocrowd.model.milieu import Milieu
from viscocrowd.observables.sortie import Sorties
from viscocrowd.scenarios.piscine import ParametresPiscine, simuler_piscine

EXEMPLE = Path(__file__).parents[1] / "experiments/piscine.yaml"


@pytest.fixture
def configuration():
    config = lire_configuration(EXEMPLE)
    config["parametres"]["n_agents"] = 4
    return config


@pytest.fixture
def appels(monkeypatch):
    """Remplace `mesurer` : chaque mesure encode les parametres qui l'ont produite.

    t50 = graine, t90 = a_max du mouille, t100 = facteur de panique, debit = largeur
    mouillee, non_sortis = 0 : une erreur d'appariement ou de temoin se lit directement
    dans les ecarts.
    """
    recus = []

    def factice(p):
        recus.append(p)
        return {
            "t50": float(p.graine),
            "t90": p.parametres_milieux[Milieu.MOUILLE].acceleration_max,
            "t100": p.facteur_vitesse,
            "debit": p.piscine.largeur_mouillee,
            "non_sortis": 0.0,
        }

    monkeypatch.setattr(balayage, "mesurer", factice)
    return recus


class TestAppariement:
    def test_temoin_meme_graine_sol_entierement_sec(self, configuration, appels):
        (point,) = balayage.balayer(configuration, "adherence_mouille", [1.0], [7, 8])

        # Chaque ligne du temoin a la graine de la ligne du mouille (colonne t50).
        np.testing.assert_array_equal(point.temoin[:, 0], [7, 8])
        np.testing.assert_array_equal(point.mouille[:, 0], [7, 8])
        # Le temoin est tout sec : a_max du sec, bande de largeur nulle.
        np.testing.assert_array_equal(point.temoin[:, 1], [5.9, 5.9])
        np.testing.assert_array_equal(point.temoin[:, 3], [0.0, 0.0])
        np.testing.assert_array_equal(point.mouille[:, 1], [1.0, 1.0])
        np.testing.assert_array_equal(point.ecart[:, 1], [1.0 - 5.9] * 2)
        np.testing.assert_array_equal(point.ecart[:, 0], [0.0, 0.0])

    def test_seul_le_parametre_balaye_change(self, configuration, appels):
        balayage.balayer(configuration, "facteur_vitesse", [1.0, 2.0], [1])

        facteurs = sorted({p.facteur_vitesse for p in appels})
        assert facteurs == [1.0, 2.0]
        # Le mouille garde le reste du YAML : bande de 3 m, a_max de 3,3 m/s^2.
        mouilles = [p for p in appels if p.piscine.largeur_mouillee > 0]
        assert {p.piscine.largeur_mouillee for p in mouilles} == {3.0}
        assert {p.parametres_milieux[Milieu.MOUILLE].acceleration_max for p in mouilles} == {3.3}

    def test_balayage_temps_espacement_sur_le_yaml_de_reference(self, configuration, appels):
        """Le YAML de reference porte le champ : le balayage n'est pas refuse (revue de #100)."""
        assert configuration["parametres"]["temps_espacement"] is None
        balayage.balayer(configuration, "temps_espacement", [0.35, 0.5], [1])

        mouilles = [p for p in appels if p.piscine.largeur_mouillee > 0]
        temoins = [p for p in appels if p.piscine.largeur_mouillee == 0]
        assert {p.temps_espacement for p in mouilles} == {0.35, 0.5}
        # Le temoin garde le meme temps d'espacement : seul le sol differe.
        assert {p.temps_espacement for p in temoins} == {0.35, 0.5}

    def test_parametres_fixes_appliques_au_mouille_et_au_temoin(self, configuration, appels):
        balayage.balayer(
            configuration, "largeur_mouillee", [3.0, 20.0], [1], fixes={"facteur_vitesse": 1.5}
        )
        assert {p.facteur_vitesse for p in appels} == {1.5}

    def test_relaxation_commune_aux_trois_sols_et_au_temoin(self, configuration, appels):
        """tau est le meme partout (journal du 6 novembre) : le balayage le change partout.

        Sinon on comparerait un mouille a tau = 0,3 s a un temoin sec a tau = 0,5 s, et
        l'ecart melangerait l'effet de tau et celui du sol.
        """
        balayage.balayer(configuration, "relaxation", [0.3, 1.0], [1])

        assert len(appels) == 4  # deux valeurs, un mouille et un temoin chacune
        for p in appels:
            taus = {m: q.relaxation for m, q in p.parametres_milieux.items()}
            assert len(set(taus.values())) == 1, taus
        assert sorted({p.parametres_milieux[Milieu.SEC].relaxation for p in appels}) == [0.3, 1.0]
        # Seul tau change : l'adherence et la vitesse du mouille restent celles du YAML.
        mouilles = [p for p in appels if p.piscine.largeur_mouillee > 0]
        assert {p.parametres_milieux[Milieu.MOUILLE].acceleration_max for p in mouilles} == {3.3}

    def test_relaxation_plus_courte_que_dt_refusee_avant_calcul(self, configuration, appels):
        with pytest.raises(ValueError, match="relaxation"):
            balayage.balayer(configuration, "relaxation", [0.5, 0.005], [1])
        assert appels == []

    def test_configuration_d_entree_intacte(self, configuration, appels):
        avant = json.dumps(configuration, sort_keys=True)
        balayage.balayer(
            configuration, "largeur_mouillee", [10.0], [1], fixes={"facteur_vitesse": 1.5}
        )
        assert json.dumps(configuration, sort_keys=True) == avant

    def test_apres_point_dans_l_ordre_des_valeurs(self, configuration, appels):
        vus = []
        balayage.balayer(
            configuration, "largeur_porte", [1.6, 0.8], [1], apres_point=lambda p: vus.append(p)
        )
        assert [p.valeur for p in vus] == [1.6, 0.8]


class TestCache:
    def test_temoin_commun_calcule_une_fois(self, configuration, appels):
        """Ni la bande ni l'adherence ne changent une piscine seche : un temoin par graine."""
        balayage.balayer(configuration, "largeur_mouillee", [3.0, 10.0, 20.0], [1, 2])
        assert len(appels) == 2 + 3 * 2

    def test_temoin_recalcule_quand_il_depend_de_la_valeur(self, configuration, appels):
        balayage.balayer(configuration, "facteur_vitesse", [1.0, 1.5], [1, 2])
        assert len(appels) == 2 * 2 * 2

    @pytest.mark.parametrize(
        "parametre, valeur", [("adherence_mouille", 5.9), ("largeur_mouillee", 0.0)]
    )
    def test_mouille_equivalent_au_sec_reprend_son_temoin(
        self, configuration, appels, parametre, valeur
    ):
        (point,) = balayage.balayer(configuration, parametre, [valeur], [1, 2])

        assert point.equivaut_au_sec
        assert len(appels) == 2  # les temoins seulement
        np.testing.assert_array_equal(point.ecart, 0.0)


class TestRefus:
    @pytest.mark.parametrize(
        "parametre, valeurs, message",
        [
            ("inconnu", [1.0], "parametre inconnu"),
            ("facteur_vitesse", [], "au moins une valeur"),
            ("facteur_vitesse", [1.0, math.nan], "finis"),
            ("facteur_vitesse", [1.0, 1.0], "distinctes"),
            ("n_agents", [2.5], "entiers"),
            ("n_agents", [1.0], "au moins 2"),
            # Hors domaine au SECOND point : refuse quand meme avant tout calcul.
            ("largeur_porte", [1.2, 30.0], "porte"),
            ("facteur_vitesse", [1.0, -1.0], "facteur_vitesse"),
        ],
    )
    def test_valeurs_refusees_avant_calcul(
        self, configuration, appels, parametre, valeurs, message
    ):
        with pytest.raises(ValueError, match=message):
            balayage.balayer(configuration, parametre, valeurs, [1])
        assert appels == []

    @pytest.mark.parametrize("graines", [[], [1, 1], [-1], [1.5]])
    def test_graines_refusees(self, configuration, appels, graines):
        with pytest.raises(ValueError, match="graine"):
            balayage.balayer(configuration, "facteur_vitesse", [1.0], graines)

    def test_parametre_balaye_ne_peut_pas_etre_fixe(self, configuration, appels):
        with pytest.raises(ValueError, match="parametre balaye"):
            balayage.balayer(
                configuration, "facteur_vitesse", [1.0], [1], fixes={"facteur_vitesse": 2.0}
            )

    def test_scenario_autre_que_piscine(self, configuration, appels):
        with pytest.raises(ValueError, match="piscine"):
            balayage.balayer(configuration | {"scenario": "couloir"}, "n_agents", [2], [1])


class TestSimulationReelle:
    """Les raccourcis du module, verifies sur de vraies evacuations de 3 agents."""

    @staticmethod
    def evacuation(configuration, **changements):
        base = configuration["parametres"] | {"n_agents": 3, "facteur_vitesse": 1.5}
        base = base | changements
        return simuler_piscine(ParametresPiscine(**base, graine=1), archiver_tous=10_000)

    def test_temoin_sans_bande_identique_a_mouille_egal_au_sec(self, configuration):
        """Justifie le cache : avec mouille = sec, la largeur de la bande ne change aucun bit.

        Au facteur 1,5, la relance sature l'adherence du mouille (2,0 m/s > a_max tau =
        1,65 m/s) : si le temoin gardait le moindre carrelage mouille, ses sorties
        differeraient.
        """
        parametres = configuration["parametres"]
        sec_partout = parametres["parametres_milieux"] | {
            "MOUILLE": parametres["parametres_milieux"]["SEC"]
        }
        a = self.evacuation(configuration, parametres_milieux=sec_partout)
        temoin = balayage.temoin(parametres | {"n_agents": 3, "facteur_vitesse": 1.5})
        b = simuler_piscine(ParametresPiscine(**temoin, graine=1), archiver_tous=10_000)

        assert np.all(np.isfinite(a.sorties))
        np.testing.assert_array_equal(a.sorties, b.sorties)

    def test_bande_nulle_identique_au_temoin(self, configuration):
        """Justifie `mouille_equivaut_au_sec` : sans bande, l'adherence du mouille ne sert pas."""
        geometrie = configuration["parametres"]["geometrie"] | {"largeur_mouillee": 0.0}
        a = self.evacuation(configuration, geometrie=geometrie)
        temoin = balayage.temoin(configuration["parametres"] | {"n_agents": 3})
        b = simuler_piscine(
            ParametresPiscine(**(temoin | {"facteur_vitesse": 1.5}), graine=1),
            archiver_tous=10_000,
        )
        np.testing.assert_array_equal(a.sorties, b.sorties)

    def test_adherence_faible_ralentit_l_evacuation(self, configuration):
        """Le balayage voit un effet quand il existe : a_max = 1 m/s^2, relance saturee.

        Reintroduit a l'arret sur le mouille, un agent qui vise 1,34 m/s demande
        1,34 / 0,5 = 2,7 m/s^2 : a 1 m/s^2, il met plus longtemps a repartir.
        """
        config = configuration | {"parametres": configuration["parametres"] | {"n_agents": 3}}
        (point,) = balayage.balayer(config, "adherence_mouille", [1.0], [1])

        assert not point.equivaut_au_sec
        assert point.ecart[0, balayage.MESURES.index("t100")] > 0.1  # s

    def test_evacuation_inachevee_conservee_sans_debit(self, configuration):
        """5 s ne suffisent a personne : rien n'est moyenne sur les seuls agents sortis."""
        base = configuration["parametres"] | {"n_agents": 3, "duree": 5.0}
        mesures = balayage.mesurer(ParametresPiscine(**base, graine=1))

        assert mesures["non_sortis"] == 3.0
        assert mesures["t100"] == math.inf
        assert math.isnan(mesures["debit"])

    def test_pas_de_debit_sur_les_seuls_agents_sortis(self, configuration, monkeypatch):
        """Deux sortis sur trois suffiraient a `debit_seyfried` : le debit doit rester indefini."""
        resultat = SimpleNamespace(
            sorties=np.array([10.0, 12.0, np.nan]),
            projection=SimpleNamespace(verifier_convergence=lambda: None),
            temps_evacuation=lambda fraction: Sorties(
                np.array([10.0, 12.0, np.nan])
            ).temps_evacuation(fraction),
        )
        monkeypatch.setattr(balayage, "simuler_piscine", lambda p, **options: resultat)
        base = configuration["parametres"] | {"n_agents": 3}
        mesures = balayage.mesurer(ParametresPiscine(**base, graine=1))

        assert mesures["non_sortis"] == 1.0
        assert mesures["t50"] == 12.0 and mesures["t100"] == math.inf
        assert math.isnan(mesures["debit"])


class TestCommande:
    @pytest.fixture
    def fichier(self, configuration, tmp_path):
        chemin = tmp_path / "piscine.yaml"
        chemin.write_text(yaml.safe_dump(configuration), encoding="utf-8")
        return chemin

    def test_bilan_graine_par_graine(self, fichier, tmp_path, appels, capsys):
        sortie = tmp_path / "data" / "balayage.json"
        code = main(
            [
                "balayer-piscine",
                str(fichier),
                "--parametre",
                "adherence_mouille",
                "--valeurs",
                "1",
                "5.9",
                "--graines",
                "3",
                "4",
                "--fixer",
                "facteur_vitesse=1.5",
                "--sortie",
                str(sortie),
            ]
        )

        assert code == 0
        bilan = json.loads(sortie.read_text(encoding="utf-8"))
        assert bilan["parametre"] == "adherence_mouille"
        assert bilan["fixes"] == {"facteur_vitesse": 1.5}
        assert bilan["graines"] == [3, 4]
        assert bilan["contexte"]["code"]["source"] in ("git", "environnement", "indisponible")
        premier, second = bilan["points"]
        assert premier["valeur"] == 1.0 and not premier["equivaut_au_sec"]
        assert premier["mouille"] == [[3.0, 1.0, 1.5, 3.0, 0.0], [4.0, 1.0, 1.5, 3.0, 0.0]]
        assert premier["temoin"] == [[3.0, 5.9, 1.5, 0.0, 0.0], [4.0, 5.9, 1.5, 0.0, 0.0]]
        assert second["equivaut_au_sec"]
        assert "(= temoin)" in capsys.readouterr().out

    def test_evacuation_incomplete_affichee_jamais_moyennee(
        self, fichier, tmp_path, monkeypatch, capsys
    ):
        """Graine 2 inachevee au facteur 2 : la case dit « incomplet », le balayage continue."""

        def mesure(p):
            bouche = p.graine == 2 and p.facteur_vitesse == 2.0
            return {
                "t50": 10.0,
                "t90": 20.0,
                "t100": math.inf if bouche else 30.0,
                "debit": math.nan if bouche else 1.5,
                "non_sortis": 4.0 if bouche else 0.0,
            }

        monkeypatch.setattr(balayage, "mesurer", mesure)
        sortie = tmp_path / "incomplet.json"
        args = ["balayer-piscine", str(fichier), "--parametre", "facteur_vitesse"]
        options = ["--valeurs", "2", "1", "--graines", "1", "2", "--sortie", str(sortie)]
        assert main([*args, *options]) == 0

        bouche, normal = capsys.readouterr().out.strip().splitlines()[-4:-2]
        assert "incomplet 1/2" in bouche and "±" not in bouche.split()[1]
        assert "4/4" in bouche  # non sortis : mouille/temoin, total sur les graines
        assert "incomplet" not in normal
        bilan = json.loads(sortie.read_text(encoding="utf-8"))
        assert bilan["points"][0]["mouille"][1] == [10.0, 20.0, None, None, 4.0]
        assert [p["valeur"] for p in bilan["points"]] == [2.0, 1.0]

    @pytest.mark.parametrize(
        "options, message",
        [
            (["--fixer", "facteur_vitesse"], "NOM=VALEUR"),
            (["--fixer", "inconnu=1"], "NOM=VALEUR"),
            (["--fixer", "n_agents=5", "n_agents=6"], "deux fois"),
            (["--sortie", "bilan.txt"], ".json"),
        ],
    )
    def test_refus_de_la_commande(self, fichier, appels, capsys, options, message):
        args = ["balayer-piscine", str(fichier), "--parametre", "facteur_vitesse"]
        assert main([*args, "--valeurs", "1", "--graines", "1", *options]) == 1
        assert message in capsys.readouterr().err
        assert appels == []

    def test_bilan_existant_jamais_ecrase(self, fichier, tmp_path, appels):
        sortie = tmp_path / "deja.json"
        sortie.write_text("{}", encoding="utf-8")
        args = ["balayer-piscine", str(fichier), "--parametre", "facteur_vitesse"]
        assert main([*args, "--valeurs", "1", "--graines", "1", "--sortie", str(sortie)]) == 1
        assert sortie.read_text(encoding="utf-8") == "{}"
        assert appels == []
