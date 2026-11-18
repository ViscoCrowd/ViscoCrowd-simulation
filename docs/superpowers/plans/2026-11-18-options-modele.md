# Options du modèle : plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal :** rendre l'évacuation plus réaliste par trois options facultatives, chacune
désactivée par défaut et testable seule : un temps de réaction à l'alarme (D1), une
profondeur variable du bassin (D2), un choix du site de sortie selon la file d'attente (D3).
D5 (maître-nageur) étend D3.

**Architecture :** chaque option est un module de `src/viscocrowd/model/` (fonctions pures),
une clé facultative de `ParametresPiscine`, et un branchement dans `simuler_piscine` qui ne
change rien quand la clé vaut `null`. D1 agit sur la **direction** (une direction nulle
arrête l'agent, comme le fait déjà le module de chutes) ; D2 agit sur la **vitesse
souhaitée** par le crochet `facteur_individuel` de `pas_libre_milieux` ; D3 remplace la
direction des nageurs proches du bord.

**Tech Stack :** Python 3.12, NumPy, pytest.

**Spec :** [`2026-11-18-feuille-de-route.md`](2026-11-18-feuille-de-route.md) (D1, D2, D3, D5) ;
spec de conception § 2.6 (guidage) et § 2.7 (franchissements).

## Global Constraints

Celles de la feuille de route, plus :

- Chaque option a une entrée « proposition » dans `docs/journal-decisions.md`, avec ses hypothèses chiffrées et la mention « à balayer avant toute conclusion ».
- Les tirages de D1 utilisent `generateur(graine, flux=3)` : activer D1 ne change ni les positions initiales (flux 0), ni les chutes (flux 1), ni la navigation (flux 2).
- Le contrôle du pas de temps (`dt · vitesse_max ≤ rayon / 5`) tient compte du plus grand facteur de vitesse qu'une option peut produire.
- Aucune valeur sans source n'est présentée comme un résultat : les campagnes sur ces options sont exploratoires (`criteres-acceptation.md`, § 3).

## Review Focus

1. **Nageur qui n'a pas encore réagi :** il ne doit ni saisir un site libre à portée, ni déclencher la règle de déblocage parce qu'il est immobile depuis plus de 2 s : D1, Task 2.
2. **Profondeur constante à 0,7 m** : facteur exactement 1, donc simulation identique au bit près à `profondeur: null` : D2, Task 2.
3. **Profondeur faible** (< 0,7 m) : le facteur dépasse 1, la vitesse aussi ; le contrôle du pas doit le voir : D2, Task 2.
4. **Hésitation entre deux sites** de coût voisin : sans marge, le nageur oscille et n'arrive jamais ; un changement de site n'est accepté que si le gain dépasse `marge` : D3, Task 1.
5. **Option combinée aux chutes ou à la navigation** : les directions et les facteurs se composent (multiplication, direction nulle prioritaire), sans qu'une option écrase l'autre : D1 Task 2, D2 Task 2.

---

## D1 : `feat(piscine): décaler les départs par un temps de réaction (facultatif)`

Branche `feat/temps-reaction`. Taille : une journée.

**Configuration :** `reaction: {mediane: 5.0, dispersion: 0.5}` (s, et écart-type du
logarithme) ou `null`. Loi log-normale : forme habituelle des temps de pré-mouvement dans la
littérature sur l'évacuation (ISO/TR 16738, Purser et Bensilum 2001, **à vérifier sur
l'original**). Aucune valeur n'existe pour une piscine : hypothèse à balayer.

### Task 1 : tirage des instants de réaction

**Files :**
- Create : `src/viscocrowd/model/reaction.py`
- Test : `tests/test_reaction.py`

**Interfaces :**
- Produces : `FLUX_REACTION = 3` ; `instants_reaction(n: int, mediane: float, dispersion: float, graine: int) -> np.ndarray` (n,), en s : `exp(log(mediane) + dispersion · N(0, 1))` ; `dispersion == 0` rend `mediane` partout. Refus si `mediane <= 0`, `dispersion < 0`, ou une valeur non finie.

- [ ] **Step 1 : tests qui échouent**

```python
def test_dispersion_nulle():
    np.testing.assert_array_equal(instants_reaction(5, 3.0, 0.0, 1), np.full(5, 3.0))

def test_mediane_retrouvee():
    assert np.median(instants_reaction(20_000, 5.0, 0.5, 1)) == pytest.approx(5.0, rel=0.02)

def test_reproductible_et_flux_propre():
    np.testing.assert_array_equal(instants_reaction(10, 5.0, 0.5, 7), instants_reaction(10, 5.0, 0.5, 7))
    assert not np.array_equal(instants_reaction(10, 5.0, 0.5, 7), instants_reaction(10, 5.0, 0.5, 8))

@pytest.mark.parametrize("mediane, dispersion", [(0.0, 0.5), (-1.0, 0.5), (5.0, -0.1), (np.nan, 0.5)])
def test_refus(mediane, dispersion):
    with pytest.raises(ValueError):
        instants_reaction(3, mediane, dispersion, 1)
```

- [ ] **Step 2 :** `pytest tests/test_reaction.py -v` → échec à l'import.
- [ ] **Step 3 :** implémenter avec `viscocrowd.core.rng.generateur(graine, flux=FLUX_REACTION)`.
- [ ] **Step 4 :** relancer → passe.
- [ ] **Step 5 :** commit `feat(reaction): tirer les instants de réaction selon une loi log-normale`.

### Task 2 : brancher sur la piscine

**Files :**
- Modify : `src/viscocrowd/scenarios/piscine.py` (champ `reaction`, validation dans `__post_init__`, `en_dictionnaire`, direction composée avant `pas_libre_milieux`, bloc d'attribution des sites autour de `etat[i], debut_agent[i], site_agent[i] = FRANCHISSEMENT, t, k`, compteur `immobile` du déblocage)
- Test : `tests/test_piscine_scenario.py`

**Interfaces :**
- Consumes : `instants_reaction` (Task 1).
- Produces : `ParametresPiscine.reaction: dict | None = None` (clés exactement `mediane`, `dispersion`) ; `ResultatPiscine.reactions: np.ndarray | None` (n,), en s.

Règle : tant que `t < reactions[i]`, l'agent i a une direction nulle (il freine sous a_max comme les autres), n'est candidat à aucun site, et son compteur `immobile` reste à 0. La direction composée est : guidage, puis chutes s'il y en a, puis masque de réaction.

- [ ] **Step 1 : tests qui échouent**

```python
def test_sans_reaction_identique_au_bit_pres():
    a = simuler_piscine(parametres_reduits())
    b = simuler_piscine(parametres_reduits(reaction=None))
    np.testing.assert_array_equal(a.x, b.x); np.testing.assert_array_equal(a.sorties, b.sorties)

def test_personne_ne_bouge_ni_ne_franchit_avant_sa_reaction():
    r = simuler_piscine(parametres_reduits(reaction={"mediane": 3.0, "dispersion": 0.0}, duree=2.5))
    assert np.max(np.abs(r.x - r.x[0])) < 1e-12
    assert r.deblocages == 0 and np.all(r.etats == EAU)

def test_les_agents_partent_apres_leur_reaction():
    r = simuler_piscine(parametres_reduits(reaction={"mediane": 1.0, "dispersion": 0.0}, duree=3.0))
    assert np.max(np.hypot(*(r.x[-1] - r.x[0]).T)) > 0.1

def test_positions_initiales_inchangees_par_la_reaction():
    np.testing.assert_array_equal(
        positions_initiales(parametres_reduits()),
        positions_initiales(parametres_reduits(reaction={"mediane": 5.0, "dispersion": 0.5})))

def test_reaction_mal_formee_refusee():
    with pytest.raises(ValueError, match="reaction"):
        parametres_reduits(reaction={"mediane": 5.0})
```

(`parametres_reduits(**surcharges)` : référence à 6 agents, `duree` 10 s, surcharges fusionnées.)

- [ ] **Step 2 :** `pytest tests/test_piscine_scenario.py -k reaction -v` → échec.
- [ ] **Step 3 :** implémenter les trois exclusions (direction, sites, déblocage).
- [ ] **Step 4 :** `make test` → passe, `test_reference_inchangee` (C2) compris s'il est fusionné.
- [ ] **Step 5 :** journal (proposition, hypothèses, sources à vérifier), paragraphe dans `docs/parametres-piscine.md` (statut « hypothèse »). Commit `feat(piscine): décaler les départs par un temps de réaction (facultatif)`. PR avec t50 et t100 de la graine de référence pour `mediane` = 1, 5 et 10 s.

### Suite : `exp(balayage): tester l'effet tampon avec des départs échelonnés`

- [ ] Ajouter `PARAMETRES["reaction_mediane"]` (chemin `("reaction", "mediane")`, unité s).
- [ ] Créer `experiments/variantes/reaction.yaml` : référence, porte 0,8 m, `largeur_mouillee: 20`, `MOUILLE.acceleration_max: 1.0`, `reaction: {mediane: 1.0, dispersion: 0.5}`.
- [ ] `balayer-piscine experiments/variantes/reaction.yaml --parametre reaction_mediane --valeurs 1 5 10 20 --graines 1 2 3 4 5 6 7 8 9 10`.
- [ ] Question posée **avant** le calcul, dans la PR : si l'hypothèse tampon tient, Δt100 (mouillé − sec) diminue quand les départs s'étalent. Lire avec le décompte des signes, en exploratoire.

---

## D2 : `feat(piscine): faire varier la profondeur du bassin (facultatif)`

Branche `feat/profondeur-bassin`. Taille : une journée.

**Configuration :** `profondeur: {gauche: 1.2, droite: 0.7}` (m, aux bords gauche et droit du
bassin, variation linéaire en x) ou `null`. Vitesse dans l'eau d'après shirvani2020 :
V = 0,53 (d²/2)^−0,19, donc V ∝ d^−0,38 ; la vitesse `EAU.vitesse` du YAML (0,69 m/s)
correspond à d = 0,7 m.

**Dépendance :** le crochet `facteur_individuel: Callable[[State], np.ndarray] | None` de
`pas_libre_milieux`, introduit par #163. Si #163 est fusionnée, le réutiliser. Sinon,
l'ajouter **avec exactement cette signature**, dans un commit à part
(`feat(milieu): accepter un facteur de vitesse par agent`), pour que la fusion de #163 reste
triviale.

### Task 0 : domaine de validité de la formule

- [ ] Lire shirvani2020 (J. Hydroinformatics 22(5), p. 1078-1092) : domaine de profondeur où V = 0,53 (d²/2)^−0,19 est donnée, et conditions (eau calme, marche). Écrire `PROFONDEUR_MIN` et `PROFONDEUR_MAX` et la page dans la docstring du module. Sans domaine trouvé : bornes 0,5 et 1,3 m, présentées comme une hypothèse.

### Task 1 : profondeur et facteur de vitesse

**Files :**
- Create : `src/viscocrowd/model/profondeur.py`
- Test : `tests/test_profondeur.py`

**Interfaces :**
- Produces : `PROFONDEUR_REFERENCE = 0.7` (m) ; `PROFONDEUR_MIN`, `PROFONDEUR_MAX` (Task 0) ; `profondeur(x: np.ndarray, bassin: ObstacleRectangle, gauche: float, droite: float) -> np.ndarray` (m, linéaire en x, bornée aux bords du bassin) ; `facteur_profondeur(d: np.ndarray) -> np.ndarray = (d / PROFONDEUR_REFERENCE) ** -0.38`.

- [ ] **Step 1 : tests qui échouent**

```python
def test_facteur_a_la_reference():
    assert facteur_profondeur(np.array([0.7]))[0] == 1.0

def test_facteur_au_grand_bain():
    assert facteur_profondeur(np.array([1.2]))[0] == pytest.approx(0.8149, abs=1e-4)  # 0,56 / 0,69

def test_profondeur_lineaire_et_bornee():
    b = ObstacleRectangle(3.0, 28.0, 4.0, 16.5)
    d = profondeur(np.array([[3.0, 8.0], [15.5, 8.0], [28.0, 8.0], [40.0, 8.0]]), b, 1.2, 0.7)
    np.testing.assert_allclose(d, [1.2, 0.95, 0.7, 0.7])
```

- [ ] **Step 2 :** `pytest tests/test_profondeur.py -v` → échec.
- [ ] **Step 3 :** implémenter.
- [ ] **Step 4 :** relancer → passe.
- [ ] **Step 5 :** commit `feat(profondeur): calculer la vitesse dans l'eau selon la profondeur`.

### Task 2 : vitesse des nageurs et guidage

**Files :**
- Modify : `src/viscocrowd/scenarios/piscine.py` (champ `profondeur`, validation, contrôle de `dt` avec `facteur_profondeur(PROFONDEUR_MIN)`, facteur composé passé à `pas_libre_milieux`) ; `src/viscocrowd/model/guidage_piscine.py:147` (`F_eau`)
- Test : `tests/test_piscine_scenario.py`, `tests/test_guidage_piscine.py` (ou le fichier de tests du guidage existant)

**Interfaces :**
- Consumes : `profondeur`, `facteur_profondeur` (Task 1) ; crochet `facteur_individuel` (#163).
- Produces : `ParametresPiscine.profondeur: dict | None = None` (clés `gauche`, `droite`) ; `GuidagePiscine(..., facteur_eau: Callable[[np.ndarray], np.ndarray] | None = None)`, qui multiplie `F_eau` par `facteur_eau(noeuds)`.

Facteur d'un agent : `facteur_profondeur(profondeur(x))` s'il est dans le bassin (`piscine.dans_bassin`), 1 sinon, multiplié par le facteur de la navigation si elle est active.

- [ ] **Step 1 : tests qui échouent**

```python
def test_profondeur_constante_identique_a_sans_profondeur():
    a = simuler_piscine(parametres_reduits())
    b = simuler_piscine(parametres_reduits(profondeur={"gauche": 0.7, "droite": 0.7}))
    np.testing.assert_array_equal(a.x, b.x)

def test_nageur_plus_lent_au_grand_bain():
    v_grand = vitesse_moyenne_nageur_seul(profondeur={"gauche": 1.2, "droite": 1.2})
    v_ref = vitesse_moyenne_nageur_seul(profondeur=None)
    assert v_grand / v_ref == pytest.approx(0.815, rel=0.03)

def test_guidage_plus_long_au_grand_bain():
    assert temps_eau_au_centre(profondeur={"gauche": 1.2, "droite": 1.2}) > temps_eau_au_centre(profondeur=None)

def test_profondeur_hors_domaine_refusee():
    with pytest.raises(ValueError, match="profondeur"):
        parametres_reduits(profondeur={"gauche": 3.0, "droite": 0.7})
```

(`vitesse_moyenne_nageur_seul(**surcharges)` : `parametres_reduits(n_agents=1, duree=5.0, **surcharges)`, vitesse moyenne de l'agent sur les 2 dernières secondes, régime établi après 5 τ. `temps_eau_au_centre(**surcharges)` : `GuidagePiscine` construit comme dans `simuler_piscine` pour ces paramètres, `guidage.temps` au centre du bassin, en s.)

- [ ] **Step 2 :** lancer → échec.
- [ ] **Step 3 :** implémenter.
- [ ] **Step 4 :** `make test` → passe.
- [ ] **Step 5 :** journal, `docs/parametres-piscine.md` (statut « transposé » : shirvani2020, crue → bassin). Commit `feat(piscine): faire varier la vitesse des nageurs avec la profondeur (facultatif)`. PR avec t50 et t100 sur les graines 1 à 10, pour un bassin à 0,7 m partout et un bassin de 0,7 à 1,2 m.

---

## D3 : `feat(piscine): choisir son site de sortie selon la file d'attente (facultatif)`

Branche `feat/choix-site`. Taille : 2 jours. Bonus de la vague 3.

**Pourquoi :** le champ eikonal de l'eau est statique (`guidage_piscine.py`, docstring : « il
ignore l'attente devant un site occupé »). Un vrai nageur, près du bord, voit la file
devant l'échelle et va au rebord libre d'à côté.

**Configuration :** `choix_site: {portee: 3.0, periode: 1.0, marge: 1.0}` (m, s, s) ou `null`.

### Task 1 : coûts et choix

**Files :**
- Create : `src/viscocrowd/model/choix_site.py`
- Test : `tests/test_choix_site.py`

**Interfaces :**
- Produces :
  - `files_par_site(site_vise: np.ndarray, k: int) -> np.ndarray` (k,) : nombre de nageurs qui visent chaque site (−1 = aucun) ;
  - `couts_sites(x: np.ndarray, attentes: np.ndarray, v_eau: float, durees: np.ndarray, temps_apres: np.ndarray, files: np.ndarray) -> np.ndarray` (N, K), en s : `|x − attente_k| / v_eau + files_k · durees_k + durees_k + temps_apres_k`, où `temps_apres_k = phi_plage(arrivee_k)` ;
  - `choisir(couts: np.ndarray, actuels: np.ndarray, marge: float, portee_ok: np.ndarray) -> np.ndarray` (N,) : meilleur site parmi ceux à portée ; un nageur qui vise déjà un site n'en change que si le gain dépasse `marge` ; −1 si aucun site à portée.

- [ ] **Step 1 : tests qui échouent**

```python
def test_la_file_detourne_vers_le_site_libre():
    couts = couts_sites(np.array([[5.0, 1.0]]), np.array([[4.0, 0.2], [6.0, 0.2]]), 1.0,
                        np.array([2.0, 2.0]), np.zeros(2), files=np.array([3, 0]))
    assert choisir(couts, np.array([-1]), 1.0, np.ones((1, 2), bool))[0] == 1

def test_la_marge_evite_l_hesitation():
    couts = np.array([[10.0, 9.5]])
    assert choisir(couts, np.array([0]), 1.0, np.ones((1, 2), bool))[0] == 0

def test_aucun_site_a_portee():
    assert choisir(np.array([[1.0, 2.0]]), np.array([-1]), 1.0, np.zeros((1, 2), bool))[0] == -1

def test_files_par_site():
    np.testing.assert_array_equal(files_par_site(np.array([0, 0, 2, -1]), 3), [2, 0, 1])
```

- [ ] **Step 2 → 4 :** échec, implémentation, passage.
- [ ] **Step 5 :** commit `feat(choix-site): choisir un site selon le coût total et la file`.

### Task 2 : brancher sur la piscine

**Files :**
- Modify : `src/viscocrowd/scenarios/piscine.py` (champ `choix_site`, mise à jour de `site_vise` toutes les `periode` s pour les nageurs à moins de `portee` du bord, direction vers `attentes[site_vise]` à la place du champ de l'eau)
- Test : `tests/test_piscine_scenario.py`

- [ ] **Step 1 : tests qui échouent**

```python
def test_sans_choix_identique_au_bit_pres():
    np.testing.assert_array_equal(simuler_piscine(parametres_reduits()).x,
                                  simuler_piscine(parametres_reduits(choix_site=None)).x)

def test_evacuation_complete_avec_choix():
    r = simuler_piscine(parametres_reduits(n_agents=30, duree=120.0,
                                           choix_site={"portee": 3.0, "periode": 1.0, "marge": 1.0}))
    assert np.all(np.isfinite(r.sorties)) and r.violation_paroi_max() <= 1e-14
```

- [ ] **Step 2 → 4 :** échec, implémentation, `make test`.
- [ ] **Step 5 :** journal, commit `feat(piscine): choisir son site de sortie selon la file d'attente (facultatif)`. PR avec, sur les graines 1 à 10 : part des sorties par les échelles, attente moyenne devant un site, t100, avec et sans l'option.

---

## D5 : `feat(piscine): coordonner la sortie par un maître-nageur` (vague 4)

Étend D3 : `choix_site.mode: "local" | "coordonne"` (`"local"` par défaut). En mode
coordonné, un maître-nageur voit tout le bassin (`portee` infinie) et attribue les sites un
nageur après l'autre, par ordre de temps eikonal croissant, au site de coût minimal **files
mises à jour au fur et à mesure**.

- [ ] **Interfaces :** `attribuer_coordonne(couts_sans_file: np.ndarray, durees: np.ndarray, ordre: np.ndarray) -> np.ndarray` (N,) dans `model/choix_site.py`.
- [ ] **Test :** 6 nageurs, 2 sites identiques → 3 et 3 ; un site deux fois plus lent → moins de nageurs dessus.
- [ ] **Test :** `mode: "local"` identique au bit près à D3 sans la clé.
- [ ] **PR :** démonstration avec `comparer-variantes` (C6) : sans maître-nageur / avec. À présenter comme un scénario illustratif : aucune source ne décrit ce comportement.
