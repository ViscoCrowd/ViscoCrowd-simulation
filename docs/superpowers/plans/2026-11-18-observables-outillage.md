# Observables et outillage : plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal :** alléger les bilans, figer la référence, mesurer les bouchons et les temps d'arrêt,
mettre fin aux conflits de `cli.py`, puis préparer les films de la soutenance en une commande.

**Architecture :** sept PR indépendantes ou presque (C1 à C7). Les observables vivent dans
`src/viscocrowd/observables/` (fonctions pures sur des tableaux NumPy, testées sur des données
synthétiques) et les commandes de visualisation dans `src/viscocrowd/viz/`, chacune avec son
`ajouter_commande(sous)`.

**Tech Stack :** Python 3.12, NumPy, Matplotlib, Pillow (déjà présent), pytest.

**Spec :** [`2026-11-18-feuille-de-route.md`](2026-11-18-feuille-de-route.md) (C1 à C7).

## Global Constraints

Celles de la feuille de route, plus :

- Une observable lit les archives existantes (`lire_trajectoire` : `t`, `x`, `v`, `etats`, `metadonnees`) et ne relance aucune simulation (spec § 6.1).
- Une évacuation incomplète (sortie `None` ou `NaN`) est **comptée et affichée**, jamais retirée en silence.
- Les modules de `viz/` importent Matplotlib dans les fonctions, comme `ui/` le fait déjà, pour garder `viscocrowd --help` rapide.

## Review Focus

1. Sorties `None` dans les métadonnées (agents jamais sortis) : converties en `NaN`, ignorées par les intervalles et comptées comme « incomplète » : C3.
2. Archive espacée (`archiver_tous > 1`) pour la carte des temps d'arrêt : pondérer chaque instant par l'écart réel entre instants archivés, pas par `dt` : C4.
3. Plate-forme différente (CI Linux, postes Windows) : la référence figée compare avec une tolérance écrite (10⁻⁶ s), pas une égalité binaire : C2.
4. Carte des temps d'arrêt et taille des cases : le temps total doit rester le même quand la case est divisée par deux : C4.
5. Module de visualisation oublié dans la liste des commandes : un test compare la liste au contenu du paquet : C5.

---

## C1 : `chore(json): arrondir les bilans du diagramme fondamental`

Branche `chore/arrondi-bilans`. Convenu dans la revue de #133. Taille : 1 h.

### Task 1 : arrondir à l'écriture

**Files :**
- Modify : `src/viscocrowd/scenarios/campagne.py` (fonction après `ecrire_json`) ; `src/viscocrowd/scenarios/diagramme_piscine.py:242-250` ; `src/viscocrowd/scenarios/diagramme_goulot.py:282-290`
- Test : `tests/test_campagne.py`, `tests/test_diagramme_piscine.py`

**Interfaces :**
- Produces : `arrondir(valeurs: np.ndarray, decimales: int) -> list[float | None]` (`NaN` → `None`), dans `campagne.py` ; `serie_en_json(s) -> dict[str, list]`, dans `diagramme_goulot.py` à côté de `serie_voronoi`, qui rend seulement `{"t", "densite", "vitesse"}` (le reste du dictionnaire écrit ne change pas) et que `diagramme_piscine.py` importe. Décimales fixées : `t` 2 (0,01 s), `densite` et `vitesse` 4, agrégats 4.

- [ ] **Step 1 : tests qui échouent**

```python
def test_arrondir():
    assert arrondir(np.array([1.23456, np.nan, 2.0]), 2) == [1.23, None, 2.0]

def test_serie_en_json_arrondie():
    s = SimpleNamespace(t=np.array([0.123456]), densite=np.array([1.234567]), vitesse=np.array([np.nan]))
    assert serie_en_json(s) == {"t": [0.12], "densite": [1.2346], "vitesse": [None]}
```

- [ ] **Step 2 :** `pytest tests/test_campagne.py tests/test_diagramme_piscine.py -k arrond -v` → échec.
- [ ] **Step 3 :** implémenter et l'utiliser dans les deux commandes. Les classes sont calculées en mémoire avant l'écriture : elles ne changent pas.
- [ ] **Step 4 :** `pytest tests/test_diagramme.py tests/test_diagramme_piscine.py -q` → passe. Relancer la commande de #133 sur 2 graines et noter la taille avant/après dans la PR (attendu : environ ÷ 3).
- [ ] **Step 5 :** commit `chore(json): arrondir les séries des bilans du diagramme fondamental`. Les bilans déjà versionnés ne sont pas régénérés : le dire dans la PR.

---

## C2 : `test(piscine): figer la référence pour détecter un changement involontaire`

Branche `test/reference-figee`. Taille : 2 h.

### Task 1 : test de référence figée

**Files :**
- Create : `tests/donnees/reference_piscine.json`, `tests/donnees/regenerer_reference.py`, `tests/test_reference_piscine.py`

**Interfaces :**
- Produces : `mesurer_reference() -> dict` dans `tests/test_reference_piscine.py` : `experiments/piscine.yaml` à 20 agents, graine du YAML ; rend `{"sorties": list[float], "t50": float, "t100": float, "deblocages": int, "franchissements": int}`. Le script de régénération l'importe et écrit le JSON.

- [ ] **Step 1 :** écrire `mesurer_reference` et le test :

```python
def test_reference_inchangee():
    attendu = json.loads(FICHIER.read_text(encoding="utf-8"))
    obtenu = mesurer_reference()
    np.testing.assert_allclose(obtenu["sorties"], attendu["sorties"], rtol=0, atol=1e-6)
    assert obtenu["deblocages"] == attendu["deblocages"]
    assert obtenu["franchissements"] == attendu["franchissements"]
```

- [ ] **Step 2 :** `pytest tests/test_reference_piscine.py` → échec (fichier absent).
- [ ] **Step 3 :** `python tests/donnees/regenerer_reference.py` écrit le JSON avec le commit courant dans un champ `commit`.
- [ ] **Step 4 :** relancer → passe ; mesurer la durée (`--durations=1`). Si elle dépasse 5 s, réduire à 12 agents. Pousser et vérifier que le test passe aussi sur la CI Linux.
- [ ] **Step 5 :** ajouter à `CONTRIBUTING.md` (§ revue) : « une PR qui change volontairement la référence régénère `tests/donnees/reference_piscine.json` et l'explique dans sa description ». Commit `test(piscine): figer la référence sur vingt baigneurs`.

---

## C3 : `feat(observables): mesurer les intervalles entre sorties successives`

Branche `feat/intervalles-sorties`. Taille : une journée. Référence : Zuriguel et al. (2014),
*Clogging transition of many-particle systems flowing through bottlenecks*, Sci. Rep. 4, 7324,
**à vérifier sur l'original** et à ajouter à `report/references.bib`.

### Task 1 : observables

**Files :**
- Create : `src/viscocrowd/observables/bouchage.py`
- Test : `tests/test_bouchage.py`

**Interfaces :**
- Produces :
  - `intervalles_sorties(sorties: np.ndarray) -> np.ndarray` : instants finis triés, différences successives, en s ;
  - `survie(intervalles: np.ndarray, seuils: np.ndarray) -> np.ndarray` : P(Δ > τ) pour chaque τ (inégalité stricte) ;
  - `resumer(sorties: np.ndarray, seuil_bouchon: float = 1.0) -> dict[str, float | int]` : `n_sortis`, `incomplete` (0/1), `mediane`, `p_bouchon` = P(Δ > seuil), `max`, en s.

- [ ] **Step 1 : tests qui échouent**

```python
def test_intervalles_ignorent_les_non_sortis_et_trient():
    np.testing.assert_array_equal(intervalles_sorties(np.array([5.0, 0.0, np.nan, 1.0, 2.0])), [1, 1, 3])

@pytest.mark.parametrize("sorties", [np.array([]), np.array([3.0]), np.array([np.nan, 2.0])])
def test_moins_de_deux_sorties(sorties):
    assert intervalles_sorties(sorties).size == 0

def test_survie_stricte():
    np.testing.assert_allclose(survie(np.array([1.0, 1.0, 3.0]), np.array([0.5, 1.0, 2.0, 3.0])), [1, 1/3, 1/3, 0])

def test_resumer_signale_une_evacuation_incomplete():
    r = resumer(np.array([0.0, 1.0, np.nan]), seuil_bouchon=0.5)
    assert r["incomplete"] == 1 and r["n_sortis"] == 2 and r["p_bouchon"] == 1.0
```

- [ ] **Step 2 :** `pytest tests/test_bouchage.py -v` → échec à l'import.
- [ ] **Step 3 :** implémenter.
- [ ] **Step 4 :** relancer → passe.
- [ ] **Step 5 :** commit `feat(observables): mesurer les intervalles entre sorties successives`.

### Task 2 : commande `bouchons`

**Files :**
- Create : `src/viscocrowd/viz/bouchage.py`
- Modify : `src/viscocrowd/cli.py` (ou la liste de C5 si elle est fusionnée)
- Test : `tests/test_bouchage.py`

**Interfaces :**
- Consumes : `intervalles_sorties`, `survie`, `resumer` (Task 1) ; `lire_trajectoire(a).metadonnees["evenements"]["sorties"]` (liste, `None` si jamais sorti).
- Produces : `viscocrowd bouchons ARCHIVES... --etiquettes E... --image X.png [--seuil 1.0]`. Les archives d'une même étiquette (graines) sont regroupées. Courbe P(Δ > τ) en échelle log-log, une par étiquette ; la console affiche, par étiquette, le nombre d'intervalles, la médiane, P(Δ > seuil), le maximum et le nombre d'évacuations incomplètes.

- [ ] **Step 1 : test qui échoue**

```python
def test_commande_bouchons(tmp_path, capsys):
    a = simuler_archive_reduite(tmp_path / "a.npz", duree=2.0)  # 6 agents : certains non sortis
    assert main(["bouchons", str(a), "--etiquettes", "essai", "--image", str(tmp_path / "b.png")]) == 0
    assert (tmp_path / "b.png").stat().st_size > 0
    assert "incomplète" in capsys.readouterr().out
```

- [ ] **Step 2 :** lancer → échec.
- [ ] **Step 3 :** implémenter ; refuser une liste d'étiquettes de longueur différente de celle des archives.
- [ ] **Step 4 :** `make lint && pytest tests/test_bouchage.py tests/test_cli.py -q` → passe.
- [ ] **Step 5 :** commit `feat(viz): tracer la distribution des intervalles entre sorties`. PR vers `dev`.

**Suite (PR `exp`, après la relance de #166 sur les graines 1 à 10) :** script
`docs/mesures/bouchons-AAAA-MM-JJ/mesurer.py` qui simule chaque couple (panique 1, 2, 2,5, 3) ×
(mouillé, sec) × graines 1 à 10 sans régulation avec `simuler_piscine`, garde `sorties` dans un
JSON, et trace `survie` par panique. Question : la queue de P(Δ > τ) s'épaissit-elle à panique 3 ?

---

## C4 : `feat(viz): tracer la carte des temps d'arrêt`

Branche `feat/carte-attente`. Taille : une demi-journée.

### Task 1 : calcul et commande

**Files :**
- Create : `src/viscocrowd/viz/attente.py`
- Test : `tests/test_attente.py`

**Interfaces :**
- Produces :
  - `temps_arret(t: np.ndarray, x: np.ndarray, v: np.ndarray, actifs: np.ndarray, *, seuil: float, pas: float, emprise: tuple[float, float]) -> np.ndarray`, de forme (nx, ny), en s : à chaque instant k < P − 1, chaque agent actif de vitesse inférieure à `seuil` (m/s) ajoute `t[k+1] − t[k]` à sa case ;
  - `viscocrowd attente ARCHIVE --image X.png [--seuil 0.1] [--pas 0.25]`. `actifs = (etats == EAU) | (etats == PLAGE)`, lus dans `Trajectoire.etats` ; fond de géométrie identique à la pose longue de #159.

- [ ] **Step 1 : tests qui échouent**

```python
def test_agent_immobile_deux_secondes():
    t = np.array([0.0, 1.0, 2.0])
    x = np.full((3, 1, 2), [0.6, 0.6]); v = np.zeros((3, 1, 2))
    carte = temps_arret(t, x, v, np.ones((3, 1), bool), seuil=0.1, pas=0.25, emprise=(2.0, 2.0))
    assert carte[2, 2] == pytest.approx(2.0) and carte.sum() == pytest.approx(2.0)

def test_agent_en_mouvement_ou_inactif_ne_compte_pas():
    t = np.array([0.0, 1.0, 2.0]); x = np.full((3, 1, 2), [0.6, 0.6])
    rapide = np.full((3, 1, 2), [1.0, 0.0])
    assert temps_arret(t, x, rapide, np.ones((3, 1), bool), seuil=0.1, pas=0.25, emprise=(2.0, 2.0)).sum() == 0.0
    assert temps_arret(t, x, np.zeros((3, 1, 2)), np.zeros((3, 1), bool), seuil=0.1, pas=0.25, emprise=(2.0, 2.0)).sum() == 0.0

def test_total_independant_de_la_case():
    t = np.linspace(0.0, 4.0, 5)
    x = np.tile([[0.3, 0.3], [1.7, 2.9]], (5, 1, 1)); v = np.zeros((5, 2, 2)); actifs = np.ones((5, 2), bool)
    a = temps_arret(t, x, v, actifs, seuil=0.1, pas=0.25, emprise=(4.0, 4.0))
    b = temps_arret(t, x, v, actifs, seuil=0.1, pas=0.125, emprise=(4.0, 4.0))
    assert a.sum() == pytest.approx(b.sum()) == pytest.approx(8.0)

def test_archive_espacee_ponderee_par_l_ecart_reel():
    t = np.array([0.0, 0.5, 2.0])  # écarts 0,5 puis 1,5 s
    carte = temps_arret(t, np.full((3, 1, 2), [0.6, 0.6]), np.zeros((3, 1, 2)), np.ones((3, 1), bool),
                        seuil=0.1, pas=0.25, emprise=(2.0, 2.0))
    assert carte.sum() == pytest.approx(2.0)
```

- [ ] **Step 2 :** `pytest tests/test_attente.py -v` → échec.
- [ ] **Step 3 :** implémenter (`np.add.at` sur les indices de case).
- [ ] **Step 4 :** relancer → passe. À la main : `viscocrowd attente <archive de experiments/demo/pression-porte-saturee.yaml> --image /tmp/attente.png` : la zone devant la porte doit dominer.
- [ ] **Step 5 :** commit `feat(viz): tracer la carte des temps d'arrêt d'une évacuation`. PR avec l'image et le temps d'arrêt total en pers·s.

---

## C5 : `refac(cli): déclarer les commandes de visualisation dans leurs modules`

Branche `refac/commandes-viz`. **Après la vague 0** (#160, #164, #165 fusionnées). Taille : 2 h.

### Task 1 : liste des commandes dans `viz/__init__.py`

**Files :**
- Modify : `src/viscocrowd/viz/__init__.py`, `src/viscocrowd/cli.py` (appels `ajouter_commande` des modules de `viz/`) ; `README.md` (les paragraphes par commande partent dans `docs/visualisations.md`, le README garde un lien)
- Test : `tests/test_cli.py`

**Interfaces :**
- Produces : `viz.COMMANDES: tuple[str, ...]`, noms de modules triés par ordre alphabétique, un par ligne ; `cli.construire_analyseur` appelle `importlib.import_module(f"viscocrowd.viz.{nom}").ajouter_commande(sous)` pour chacun. Une nouvelle commande ajoute une ligne à sa place alphabétique : deux PR ne se touchent plus sur la même ligne.

- [ ] **Step 1 : test qui échoue**

```python
def test_tous_les_modules_viz_a_commande_sont_declares():
    trouves = {m.name for m in pkgutil.iter_modules(viz.__path__)
               if hasattr(importlib.import_module(f"viscocrowd.viz.{m.name}"), "ajouter_commande")}
    assert set(viz.COMMANDES) == trouves
    assert list(viz.COMMANDES) == sorted(viz.COMMANDES)
```

- [ ] **Step 2 :** lancer → échec (`COMMANDES` absent).
- [ ] **Step 3 :** implémenter ; `viscocrowd --help` doit lister exactement les mêmes commandes qu'avant (comparer les deux sorties dans la PR).
- [ ] **Step 4 :** `make test` → passe.
- [ ] **Step 5 :** commit `refac(cli): déclarer les commandes de visualisation dans viz/__init__`.

---

## C6 : `feat(viz): comparer n variantes côte à côte`

Branche `feat/comparer-variantes`. Après #160, E1 et C5. Taille : une journée.

### Task 1 : généraliser le duel

**Files :**
- Modify : `src/viscocrowd/viz/duel.py` (`instants_communs`, `exporter_duel`)
- Test : `tests/test_duel.py`

**Interfaces :**
- Consumes : `lire_fixes`, `appliquer_fixes` (E1) ; `exporter_duel`, `instants_communs`, `configuration_temoin` (#160).
- Produces : `instants_communs_n(fins: Sequence[float], fps: int, vitesse: float) -> np.ndarray` ; `exporter_comparaison(donnees: Sequence, titres: Sequence[str], chemin: Path, *, fps=15, vitesse=4.0, dpi=60) -> None`, de 2 à 4 vues (1 × 2, 1 × 3, 2 × 2). `exporter_duel` devient un appel à `exporter_comparaison` à deux vues.

- [ ] **Step 1 : tests qui échouent**

```python
def test_instants_communs_n_suit_la_plus_longue():
    np.testing.assert_allclose(instants_communs_n([2.0, 4.0, 3.0], fps=2, vitesse=2.0),
                               instants_communs(2.0, 4.0, fps=2, vitesse=2.0))

@pytest.mark.parametrize("n", [1, 5])
def test_nombre_de_vues_refuse(n, tmp_path):
    with pytest.raises(ValueError):
        archive = lire_trajectoire(simuler_archive_reduite(tmp_path / "a.npz", duree=1.0))
        exporter_comparaison([archive] * n, ["v"] * n, tmp_path / "x.gif")
```

- [ ] **Step 2 :** lancer → échec.
- [ ] **Step 3 :** implémenter ; `tests/test_duel.py` existant doit passer sans modification.
- [ ] **Step 4 :** `pytest tests/test_duel.py -q` → passe.
- [ ] **Step 5 :** commit `refac(duel): généraliser l'export à n vues`.

### Task 2 : commande `comparer-variantes`

**Files :**
- Create : `src/viscocrowd/viz/variantes.py` (et sa ligne dans `viz.COMMANDES`)
- Test : `tests/test_variantes.py`

**Interfaces :**
- Produces : `viscocrowd comparer-variantes CONFIG --variante NOM=VALEUR [NOM=VALEUR ...] (répété 2 à 4 fois) --gif X.gif [--vitesse 4]`. Titre de chaque vue : ses surcharges (`adherence_mouille=1`). Chaque calcul passe par `executer_configuration(..., fixes=)` dans un répertoire temporaire.

- [ ] **Step 1 : test qui échoue**

```python
def test_trois_variantes(tmp_path):
    cfg = piscine_reduite(tmp_path)
    assert main(["comparer-variantes", str(cfg), "--gif", str(tmp_path / "v.gif"),
                 "--variante", "adherence_mouille=3.3", "--variante", "adherence_mouille=2",
                 "--variante", "adherence_mouille=1"]) == 0
    with Image.open(tmp_path / "v.gif") as gif:
        assert gif.n_frames > 1
```

- [ ] **Step 2 → 4 :** échec, implémentation, passage ; `make lint`.
- [ ] **Step 5 :** commit `feat(viz): comparer n variantes d'une configuration côte à côte`. PR avec le GIF de `experiments/demo/duel-plage-glissante.yaml` aux adhérences 3,3, 2 et 1 m/s².

---

## C7 : `chore(make): régénérer les films de la soutenance en une commande`

Branche `chore/make-demo`. Après C6, #164 et #165. Taille : 2 h.

### Task 1 : configurations de démonstration et `make demo`

**Files :**
- Create : `experiments/demo/README.md` (une ligne par film : configuration, commande, message à l'oral) ; les YAML de la vague 0 y sont déjà
- Modify : `Makefile` (cible `demo`), `run.ps1` (`demo`), `docs/repères-soutenance.md` (lien)
- Test : `tests/test_demo.py`

**Interfaces :**
- Produces : `make demo` écrit dans `sorties/demo/` : `duel.gif` (`duel`), `variantes.gif` (`comparer-variantes`), `pression.png` (`pression --instant 35`), `pose-longue.png`, `trainee.png`, `attente.png`. Chaque commande lit un YAML de `experiments/demo/`.

- [ ] **Step 1 : test qui échoue**

```python
@pytest.mark.parametrize("yaml", sorted(DEMO.glob("*.yaml")), ids=lambda p: p.stem)
def test_configuration_de_demo_valide(yaml):
    config = lire_configuration(yaml)
    ParametresPiscine(**config["parametres"], graine=config["graine"])
```

- [ ] **Step 2 :** lancer → passe dès que les YAML sont valides (c'est un garde-fou contre l'évolution du code).
- [ ] **Step 3 :** cible `demo` dans le Makefile, équivalent dans `run.ps1`.
- [ ] **Step 4 :** `make demo` sur un poste propre ; noter la durée totale dans la PR.
- [ ] **Step 5 :** commit `chore(make): régénérer les films de la soutenance en une commande`.
