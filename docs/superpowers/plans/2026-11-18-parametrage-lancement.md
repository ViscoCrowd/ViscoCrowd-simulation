# Paramétrage au lancement : plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal :** choisir la population, la porte, le nombre d'échelles, la panique et le sol au
moment de lancer une simulation, sans éditer de YAML, et sans perdre la reproductibilité.

**Architecture :** on réutilise la table `PARAMETRES` et le mécanisme `--fixer` de
`balayer-piscine` (`scenarios/balayage_piscine.py`), qu'on rend publics et qu'on branche sur
`executer_configuration`. L'archive garde la configuration *effective*. Le menu (E3) n'est
qu'une façon de remplir ces surcharges.

**Tech Stack :** Python 3.12, argparse, PyYAML, pytest.

**Spec :** [`2026-11-18-feuille-de-route.md`](2026-11-18-feuille-de-route.md) (E1, E2, E3).

## Global Constraints

Celles de la feuille de route, plus :

- Une configuration surchargée n'est **jamais** une configuration de référence : les résultats du rapport ne viennent que de YAML versionnés dans `experiments/`.
- Les noms acceptés par `--fixer` sont exactement les clés de `PARAMETRES` ; aucun second vocabulaire.
- Paramètres entiers (`ENTIERS = {"n_agents", "echelles"}`) : convertis en `int`, refusés s'ils ne sont pas entiers.

## Review Focus

1. `--fixer n_agents=150` doit produire `int` 150, sinon `ParametresPiscine` refuse (`type(n_agents) is not int`) : Task 1.
2. Le diagnostic de non-convergence relit le YAML et le compare à la configuration en mémoire ; avec des surcharges, il doit comparer au fichier lu, sinon il croit le fichier modifié : Task 2, test dédié.
3. `--fixer` sur un scénario autre que la piscine : refus clair, pas une `KeyError` : Task 2.
4. Plus de baigneurs que d'emplacements de départ (300 pour la référence) : refus à la construction des paramètres, avec le maximum dans le message : E3 Task 1.
5. Saisie vide, texte non numérique, valeur hors domaine dans le menu : valeur de référence, nouvelle question, puis message de validation : E3 Task 2.

---

## E1 : `feat(cli): surcharger une configuration au lancement`

Branche `feat/simuler-fixer`. Taille : une demi-journée.

### Task 1 : rendre publiques la lecture et l'application des surcharges

**Files :**
- Modify : `src/viscocrowd/scenarios/balayage_piscine.py:205-211` (`_appliquer`), `:439-448` (`_lire_fixes`), et ses appels dans `planifier` / `commande_balayer`
- Test : `tests/test_balayage_piscine.py`

**Interfaces :**
- Produces : `ENTIERS: frozenset[str]` ; `lire_fixes(textes: list[str]) -> dict[str, float | int]` ; `appliquer_fixes(parametres: dict, fixes: Mapping[str, float | int]) -> dict` (copie, l'original intact).

- [ ] **Step 1 : tests qui échouent**

```python
def test_lire_fixes_convertit_n_agents_en_entier():
    fixes = lire_fixes(["n_agents=150", "largeur_porte=0.8"])
    assert fixes == {"n_agents": 150, "largeur_porte": 0.8}
    assert type(fixes["n_agents"]) is int

def test_lire_fixes_refuse_un_entier_non_entier():
    with pytest.raises(ValueError, match="entier"):
        lire_fixes(["n_agents=150.5"])

def test_appliquer_fixes_laisse_l_original_intact():
    config = lire_configuration(EXEMPLE)["parametres"]
    nouveau = appliquer_fixes(config, {"largeur_porte": 0.8, "relaxation": 0.4})
    assert config["geometrie"]["largeur_porte"] == 1.2
    assert nouveau["geometrie"]["largeur_porte"] == 0.8
    assert {nouveau["parametres_milieux"][m]["relaxation"] for m in ("EAU", "MOUILLE", "SEC")} == {0.4}
```

- [ ] **Step 2 :** `pytest tests/test_balayage_piscine.py -k "fixes" -v` → échec à l'import de `lire_fixes`.
- [ ] **Step 3 :** renommer `_lire_fixes` en `lire_fixes` (conversion par `ENTIERS`), ajouter `appliquer_fixes` (boucle sur `_appliquer`), et mettre à jour les deux appels internes.
- [ ] **Step 4 :** `pytest tests/test_balayage_piscine.py -q` → tout passe, y compris les tests existants du balayage.
- [ ] **Step 5 :** commit `refac(balayage): rendre publiques la lecture et l'application des surcharges`.

### Task 2 : surcharger dans `executer_configuration`

**Files :**
- Modify : `src/viscocrowd/scenarios/experience.py:77-180`
- Test : `tests/test_experience.py`

**Interfaces :**
- Consumes : `appliquer_fixes` (Task 1).
- Produces : `executer_configuration(configuration, sortie, *, archiver_tous: int = 1, fixes: Mapping[str, float | int] | None = None) -> Trajectoire` ; métadonnée `"surcharges"` (dict) présente seulement si `fixes` est non vide.

- [ ] **Step 1 : tests qui échouent.** Utilitaires `piscine_reduite`, `EXEMPLE_GOULOT` et `lire_trajectoire` : voir les contraintes globales de la feuille de route.

```python
def test_fixer_archive_la_configuration_effective(tmp_path):
    cfg = piscine_reduite(tmp_path)
    donnees = executer_configuration(cfg, tmp_path / "a.npz", fixes={"largeur_porte": 0.9})
    meta = lire_trajectoire(tmp_path / "a.npz").metadonnees
    assert meta["configuration"]["parametres"]["geometrie"]["largeur_porte"] == 0.9
    assert meta["surcharges"] == {"largeur_porte": 0.9}

def test_sans_fixer_aucune_surcharge_archivee(tmp_path):
    executer_configuration(piscine_reduite(tmp_path), tmp_path / "a.npz")
    assert "surcharges" not in lire_trajectoire(tmp_path / "a.npz").metadonnees

def test_fixer_refuse_hors_piscine(tmp_path):
    with pytest.raises(ValueError, match="piscine"):
        executer_configuration(EXEMPLE_GOULOT, tmp_path / "a.npz", fixes={"n_agents": 20})
```

- [ ] **Step 2 :** `pytest tests/test_experience.py -k fixer -v` → échec (argument inconnu).
- [ ] **Step 3 :** implémenter. Garder `config_fichier = lire_configuration(configuration)` et construire `config = config_fichier | {"parametres": appliquer_fixes(...)}` ; le contrôle « configuration modifiée pendant le calcul » (chemin du diagnostic) compare au **fichier**, `lire_configuration(configuration) != config_fichier`.
- [ ] **Step 4 :** `pytest tests/test_experience.py tests/test_diagnostic_projection.py -q` → tout passe.
- [ ] **Step 5 :** commit `feat(experience): appliquer des surcharges avant la simulation`.

### Task 3 : option `--fixer` de `simuler`, Makefile et `run.ps1`

**Files :**
- Modify : `src/viscocrowd/cli.py:213-219` (parseur `simuler`), `:445-463` (`commande_simuler`) ; `Makefile:66-67` ; `run.ps1:116-121` ; `README.md` (Démarrage)
- Test : `tests/test_cli.py`

- [ ] **Step 1 : tests qui échouent**

```python
def test_simuler_accepte_fixer(tmp_path):
    sortie = tmp_path / "a.npz"
    assert main(["simuler", str(piscine_reduite(tmp_path)), "--sortie", str(sortie),
                 "--fixer", "n_agents=4", "largeur_porte=0.9"]) == 0
    assert lire_trajectoire(sortie).x.shape[1] == 4

def test_simuler_refuse_un_nom_inconnu(tmp_path, capsys):
    assert main(["simuler", str(EXEMPLE), "--sortie", str(tmp_path / "a.npz"),
                 "--fixer", "porte=0.9"]) == 1
    assert "--fixer attend" in capsys.readouterr().err
```

- [ ] **Step 2 :** `pytest tests/test_cli.py -k simuler -v` → échec.
- [ ] **Step 3 :** argument `--fixer NOM=VALEUR` (`nargs="+"`, `default=[]`), lu par `lire_fixes` dans le `try` existant de `commande_simuler`. Makefile : `simu` accepte `FIXER="n_agents=150 largeur_porte=0.8"` ; `run.ps1 simu` accepte `-Fixer`. README : un exemple.
- [ ] **Step 4 :** `make lint && pytest tests/test_cli.py -q` → passe ; `make simu FIXER="n_agents=150"` produit une archive à 150 agents.
- [ ] **Step 5 :** commit `feat(cli): surcharger une configuration au lancement de simuler`. PR vers `dev`.

---

## E2 : `feat(geometrie): répartir n échelles régulièrement`

Branche `feat/nombre-echelles`. Taille : une demi-journée. Dépend de E1.

### Task 1 : `repartir_echelles`

**Files :**
- Modify : `src/viscocrowd/geometry/piscine.py` (fonction de module, après `_ecart_rectangles`)
- Test : `tests/test_piscine_geometrie.py`

**Interfaces :**
- Produces : `repartir_echelles(n: int, longueur_bassin: float, largeur_echelle: float) -> tuple[tuple[str, float], ...]`. Règle : `ceil(n/2)` échelles en `haut`, `floor(n/2)` en `bas`, aux fractions `(i + 0.5)/k`. Refus si `n` n'est pas un `int` positif ou nul, ou si `longueur_bassin / k < 2 * largeur_echelle`.

- [ ] **Step 1 : tests qui échouent**

```python
@pytest.mark.parametrize("n, attendu", [
    (0, ()),
    (1, (("haut", 0.5),)),
    (3, (("haut", 0.25), ("haut", 0.75), ("bas", 0.5))),
    (4, (("haut", 0.25), ("haut", 0.75), ("bas", 0.25), ("bas", 0.75))),
])
def test_repartir_echelles(n, attendu):
    assert repartir_echelles(n, 25.0, 0.5) == attendu

@pytest.mark.parametrize("n", [-1, 2.0, True, 60])
def test_repartir_echelles_refuse(n):
    with pytest.raises(ValueError):
        repartir_echelles(n, 25.0, 0.5)
```

- [ ] **Step 2 :** `pytest tests/test_piscine_geometrie.py -k repartir -v` → échec.
- [ ] **Step 3 :** implémenter (`True` est un `int` en Python : le refuser explicitement).
- [ ] **Step 4 :** relancer → passe.
- [ ] **Step 5 :** commit `feat(geometrie): répartir n échelles sur les grands côtés du bassin`.

### Task 2 : accepter `echelles: <entier>` dans le YAML et dans `--fixer`

**Files :**
- Modify : `src/viscocrowd/scenarios/piscine.py:140-141` (`__post_init__`, avant `Piscine(**geometrie)`) ; `src/viscocrowd/scenarios/balayage_piscine.py` (`PARAMETRES["echelles"]`, `ENTIERS`, `_valeurs_valides` pour les entiers)
- Test : `tests/test_piscine_scenario.py`, `tests/test_balayage_piscine.py`

**Interfaces :**
- Consumes : `repartir_echelles` (Task 1), `ENTIERS` (E1).
- Produces : `PARAMETRES["echelles"] = ParametreBalaye("E4", "-", "nombre d'echelles, reparties sur les grands cotes", ("geometrie", "echelles"))`.

- [ ] **Step 1 : tests qui échouent**

```python
def test_echelles_entier_equivaut_a_la_liste():
    a = parametres_reduits(geometrie={"echelles": 2})
    b = parametres_reduits(geometrie={"echelles": [["haut", 0.5], ["bas", 0.5]]})
    assert a.piscine.sites() == b.piscine.sites()

def test_zero_echelle_ne_laisse_que_des_rebords():
    p = parametres_reduits(geometrie={"echelles": 0})
    assert {s.nature for s in p.piscine.sites()} == {"rebord"}

def test_archive_ecrit_la_liste_explicite():
    assert parametres_reduits(geometrie={"echelles": 2}).en_dictionnaire()["geometrie"]["echelles"] == [["haut", 0.5], ["bas", 0.5]]

def test_balayer_echelles_valeurs_entieres():
    assert _valeurs_valides("echelles", [0.0, 2.0, 4.0]) == [0, 2, 4]
```

- [ ] **Step 2 :** `pytest tests/test_piscine_scenario.py tests/test_balayage_piscine.py -k echelle -v` → échec.
- [ ] **Step 3 :** implémenter ; `en_dictionnaire` écrit déjà la liste explicite, rien à changer de ce côté.
- [ ] **Step 4 :** `make test` → passe ; `viscocrowd simuler experiments/piscine.yaml --fixer echelles=4 --sortie /tmp/e4.npz` réussit.
- [ ] **Step 5 :** commit `feat(piscine): accepter un nombre d'échelles dans la configuration`, PR vers `dev` avec, dans la validation, t100 de la graine de référence pour 0, 2 et 4 échelles.

---

## E3 : `feat(cli): lancer une simulation depuis un menu`

Branche `feat/lanceur`. Taille : 1 à 2 jours. Vague 4 (après le 21/12 si le reste est fini).

### Task 1 : refuser une population plus grande que le bassin

**Files :**
- Modify : `src/viscocrowd/scenarios/piscine.py` (`capacite_initiale`, contrôle dans `__post_init__`)
- Test : `tests/test_piscine_scenario.py`

**Interfaces :**
- Produces : `capacite_initiale(p: ParametresPiscine) -> int` (nombre d'emplacements de `_grille_initiale`).

- [ ] **Step 1 : tests qui échouent**

```python
def test_capacite_de_la_reference():
    assert capacite_initiale(parametres_reduits()) == 300  # 25 x 12 emplacements

def test_population_trop_grande_refusee():
    with pytest.raises(ValueError, match="300 emplacements"):
        parametres_reduits(n_agents=301)
```

- [ ] **Step 2 :** lancer → échec.
- [ ] **Step 3 :** implémenter. Le contrôle doit venir après la construction de `piscine` dans `__post_init__`, et `_grille_initiale` doit pouvoir lire la géométrie à ce moment-là.
- [ ] **Step 4 :** `make test` → passe (aucune configuration existante ne dépasse 300).
- [ ] **Step 5 :** commit `feat(piscine): refuser plus de baigneurs que d'emplacements de départ`.

### Task 2 : questions, valeurs par défaut et saisie

**Files :**
- Create : `src/viscocrowd/ui/lanceur.py`
- Test : `tests/test_lanceur.py`

**Interfaces :**
- Consumes : `PARAMETRES`, `ENTIERS`, `appliquer_fixes` (E1), `PARAMETRES["echelles"]` (E2).
- Produces :
  - `Question(nom: str, libelle: str, unite: str)`, dataclass figée ;
  - `QUESTIONS` : `n_agents` (« Baigneurs »), `echelles` (« Échelles »), `largeur_porte` (« Largeur de la porte », m), `facteur_vitesse` (« Panique, 1 à 3 »), `largeur_mouillee` (« Bande mouillée, 20 = jusqu'à la porte », m) ;
  - `valeur_actuelle(parametres: dict, nom: str) -> float | int | list` ;
  - `demander(parametres: dict, *, lire=input, ecrire=print, essais: int = 3) -> dict[str, float | int]`.

- [ ] **Step 1 : tests qui échouent**

```python
def test_reponse_vide_garde_la_reference():
    reponses = iter(["", "", "", "", ""])
    assert demander(reference(), lire=lambda _: next(reponses), ecrire=lambda _: None) == {}

def test_saisie_invalide_reposee_puis_acceptee():
    reponses = iter(["150", "", "abc", "0.8", "", ""])
    fixes = demander(reference(), lire=lambda _: next(reponses), ecrire=lambda _: None)
    assert fixes == {"n_agents": 150, "largeur_porte": 0.8}

def test_trois_saisies_invalides_abandonnent():
    with pytest.raises(ValueError):
        demander(reference(), lire=lambda _: "abc", ecrire=lambda _: None)

def test_la_question_affiche_la_reference():
    vus = []
    demander(reference(), lire=lambda _: "", ecrire=vus.append)
    assert any("100" in ligne and "Baigneurs" in ligne for ligne in vus)
```

- [ ] **Step 2 :** `pytest tests/test_lanceur.py -v` → échec à l'import.
- [ ] **Step 3 :** implémenter. Pour `echelles`, si la référence est une liste, afficher son nombre d'éléments.
- [ ] **Step 4 :** relancer → passe.
- [ ] **Step 5 :** commit `feat(lanceur): poser les questions du paramétrage avec la référence par défaut`.

### Task 3 : commande `lancer`, préréglages et `make lancer`

**Files :**
- Modify : `src/viscocrowd/ui/lanceur.py` (`PREREGLAGES`, `ajouter_commande`, `commande_lancer`) ; `src/viscocrowd/cli.py` (`lanceur.ajouter_commande(sous)`) ; `src/viscocrowd/scenarios/balayage_piscine.py` (`PARAMETRES["longueur_bassin"]`, `["largeur_bassin"]`) ; `Makefile` ; `run.ps1` ; `README.md`
- Test : `tests/test_lanceur.py`

**Interfaces :**
- Consumes : `demander` (Task 2), `capacite_initiale` (Task 1), `executer_configuration(..., fixes=)` (E1).
- Produces : `PREREGLAGES = {"bassin-25m": {}, "olympique": {"longueur_bassin": 50.0, "largeur_bassin": 25.0, "n_agents": 200}}` ; commande `viscocrowd lancer [CONFIG] [--prereglage NOM] [--dossier DOSSIER] [--sans-relecture]`.

Déroulé de `commande_lancer` : surcharges du préréglage → `demander` → validation (`ParametresPiscine`) → résumé → écriture de `DOSSIER/AAAAMMJJ-HHMMSS/configuration.yaml` (configuration effective) → `executer_configuration` → relecture, sauf avec `--sans-relecture`.

- [ ] **Step 1 : tests qui échouent**

```python
def test_lancer_ecrit_configuration_et_archive(tmp_path, monkeypatch):
    reponses = iter(["4", "", "0.9", "", ""])
    monkeypatch.setattr("builtins.input", lambda _: next(reponses))
    assert main(["lancer", str(piscine_reduite(tmp_path)), "--dossier", str(tmp_path / "s"),
                 "--sans-relecture"]) == 0
    (run,) = (tmp_path / "s").iterdir()
    assert lire_configuration(run / "configuration.yaml")["parametres"]["n_agents"] == 4
    assert lire_trajectoire(run / "trajectoire.npz").x.shape[1] == 4

def test_lancer_refuse_une_population_trop_grande(tmp_path, monkeypatch, capsys):
    reponses = iter(["100000", "", "", "", ""])
    monkeypatch.setattr("builtins.input", lambda _: next(reponses))
    assert main(["lancer", str(EXEMPLE), "--dossier", str(tmp_path), "--sans-relecture"]) == 1
    assert "emplacements" in capsys.readouterr().err

def test_prereglage_olympique():
    assert appliquer_fixes(reference(), PREREGLAGES["olympique"])["geometrie"]["longueur_bassin"] == 50.0
```

- [ ] **Step 2 :** `pytest tests/test_lanceur.py -v` → échec.
- [ ] **Step 3 :** implémenter ; `make lancer` appelle `viscocrowd lancer` ; `run.ps1 lancer` fait de même.
- [ ] **Step 4 :** `make lint && make test` → passe. À la main : `make lancer`, préréglage olympique, 200 baigneurs → la relecture s'ouvre.
- [ ] **Step 5 :** commit `feat(cli): lancer une simulation depuis un menu de paramétrage`. Dans la PR : capture du menu, temps de calcul mesuré pour la référence et pour le préréglage olympique, et la phrase « exploration et démonstration, aucun résultat du rapport n'en vient ».
