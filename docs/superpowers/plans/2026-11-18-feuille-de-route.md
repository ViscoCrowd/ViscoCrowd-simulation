# Feuille de route du 18 novembre au rendu : plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal :** finir les PR ouvertes, rattraper le retard technique, confirmer les résultats, puis
ajouter les options de modèle, les outils et le paramétrage au lancement, dans un ordre qui
tient avant la version complète du 21/12 et le rendu du 05/01/2027.

**Architecture :** ce document est l'index. Il fixe l'ordre (vagues), les dépendances, la
branche, le titre de commit et le critère de fin de chaque PR, et détaille les PR sans code
(organisation, campagnes, rapport). Les PR de code ont leur plan TDD dans trois documents :

- [`2026-11-18-parametrage-lancement.md`](2026-11-18-parametrage-lancement.md) : E1 à E3 ;
- [`2026-11-18-observables-outillage.md`](2026-11-18-observables-outillage.md) : C1 à C7 ;
- [`2026-11-18-options-modele.md`](2026-11-18-options-modele.md) : D1 à D3, puis D5.

**Tech Stack :** Python 3.12, NumPy, SciPy, Matplotlib, pytest, ruff, GitHub CLI.

**Spec :** [`../specs/2026-10-06-viscocrowd-design.md`](../specs/2026-10-06-viscocrowd-design.md),
[`../../criteres-acceptation.md`](../../criteres-acceptation.md), [`../../planning/README.md`](../../planning/README.md).

## Global Constraints

S'appliquent à toutes les PR de ce plan et des trois plans détaillés.

- Une issue → une branche (`feat/`, `fix/`, `exp/`, `docs/`, `test/`, `refac/`, `chore/`) → une PR vers `dev` → relecture croisée → squash.
- Commits Conventional Commits, description en français à l'infinitif : `feat(scope): ajouter …`. Aucune ligne `Co-Authored-By`, aucune mention d'outil d'IA.
- Gabarit `.github/pull_request_template.md` rempli **avec les valeurs mesurées** (violation, écarts, nombre de graines).
- `make lint` et `make test` passent avant de demander la relecture.
- Aucun appel direct à `numpy.random` : tirages par `viscocrowd.core.rng.generateur(graine, flux=k)`. Flux déjà pris : 0 positions initiales, 1 chutes, 2 navigation (#163). Nouveaux flux : **3 réaction (D1)**.
- Toute option de modèle est **désactivée par défaut** (`null` dans le YAML), et un test vérifie que la référence est **identique au bit près** quand elle est absente.
- Toute hypothèse de modèle a une entrée dans `docs/journal-decisions.md`, au statut « proposition » tant que le groupe ne l'a pas validée.
- Grandeurs physiques en unités SI, unité écrite dans les docstrings et les en-têtes de tableaux.
- Campagnes : graines **1 à 10** ; confirmation d'un effet exploratoire sur les graines **11 à 20** (`criteres-acceptation.md`, § 3). Un effet n'est « détecté » qu'avec au plus une graine contraire sur 10.
- Toute figure du rapport entre dans `experiments/manifeste.yaml` **dans la même PR**.
- Aucune dépendance spécialisée nouvelle (pas de moteur de foule ou physique).
- **Utilitaires de test communs**, dans `tests/utilitaires.py`, ajoutés par la première PR qui en a besoin (même logique que `parametres(**changements)` de `tests/test_piscine_scenario.py`) :
  - `EXEMPLE` (`experiments/piscine.yaml`) et `EXEMPLE_GOULOT` (`experiments/goulot.yaml`) ;
  - `reference() -> dict` : la table `parametres` de `EXEMPLE` ;
  - `parametres_reduits(**surcharges) -> ParametresPiscine` : la référence avec `n_agents=6` et `duree=10.0` par défaut ; une clé `geometrie` est **fusionnée** dans la géométrie de référence, les autres clés remplacent ;
  - `piscine_reduite(dossier: Path, **surcharges) -> Path` : la même configuration, écrite en YAML dans `dossier / "piscine.yaml"` ;
  - `simuler_archive_reduite(chemin: Path, **surcharges) -> Path` : `executer_configuration(piscine_reduite(chemin.parent, **surcharges), chemin)`.

## Review Focus

1. **Référence modifiée en silence** quand une option est absente : chaque PR d'option ajoute le test « absent → au bit près » (D1, D2, D3) et C2 fige la référence.
2. **Configuration surchargée mais archive trompeuse** : avec `--fixer`, l'archive doit contenir la configuration *effective*, et le contrôle « configuration modifiée pendant le calcul » doit comparer au fichier lu, pas à la configuration surchargée (E1, Task 2).
3. **Entier lu comme réel** : `n_agents=150` ou `echelles=4` passés par `--fixer` arrivent en `float` ; ils doivent être convertis en `int` ou refusés (E1, E2).
4. **Bouchage définitif pris pour un résultat** : un bouchon ne se défait jamais dans ce modèle déterministe ; C3 et D1 doivent compter les évacuations incomplètes séparément, jamais les retirer d'une moyenne.
5. **Paramètre numérique qui change une conclusion** (taille des cases de #165, `pas` des cartes de C4) : chaque grille a un test de convergence (même résultat à pas/2, à tolérance écrite).

---

## Vue d'ensemble : vagues et dépendances

| Vague | Quand | Contenu |
|---|---|---|
| 0 | 18–21/11 | Finir et fusionner les PR de Lenny ; attribuer les tâches de S8 à S15 |
| 1 | 21–28/11 | Confirmations (graines 11 à 20), petites PR d'outillage, ménage du dépôt |
| 2 | 28/11–07/12 | Paramétrage au lancement, observables, figures du rapport |
| 3 | 07–21/12 | Options du modèle, analyse et conclusion, release `jalon-4` |
| 4 | après le 21/12, si le temps le permet | Menu interactif complet, maître-nageur, porte de secours, `make demo` |

```text
#166 ─┐
#160 ─┼─► C5 refac(cli) ─► C6 duel N vues ─► C7 make demo
#164 ─┤
#165 ─┘ (après #164 : conflit dans piscine.py)
E1 --fixer ─► E2 n échelles ─► E3 menu
E1 ─► C6
#163 (crochet facteur_individuel) ─► D2 profondeur
C3 intervalles ─► exp bouchons (#166 relancée sur 1 à 10)
B1 confirmation ─► G1 figures ─► G2 analyse et conclusion ─► A3 release jalon-4
```

---

## Vague 0 : finir les PR de Lenny et les fusionner

État vérifié le 18/11 : #166 se fusionne sans conflit avec `dev`. #160, #164 et #165 sont en
conflit avec `dev` sur `README.md` et `src/viscocrowd/cli.py` (deux ajouts au même endroit) ;
les PR #164 et #165 se chevauchent aussi dans `src/viscocrowd/scenarios/piscine.py`.

**Règle d'équipe :** les points de fond restent à l'auteur. On ne pousse sur la branche de
Lenny qu'avec son accord (message dans la PR), et chaque commit ajouté est signalé dans un
commentaire avec ce qu'il change, puisque `CONTRIBUTING.md` exige que tout changement
supplémentaire soit relu.

**Ordre de fusion :** #166 → #160 → #164 → #165. Chaque fusion modifie `README.md` et
`cli.py` : on remet la suivante à jour juste après.

### Tâche 0.1 : #166 `exp(panique)`, reformuler la lecture puis fusionner

**Files :** Modify `docs/balayages-piscine.md` (section « *Faster-is-slower* »).

- [ ] **Step 1 :** remplacer le point 3 de la lecture par la formulation proposée dans la revue de Shaleena : « deux graines sur cinq du témoin sec se figent, aucune du mouillé. C'est compatible avec l'hypothèse tampon, mais cinq graines ne permettent pas de la distinguer du hasard (p ≈ 0,22) : à refaire sur au moins dix graines. »
- [ ] **Step 2 :** ajouter sous le tableau : « Sur les trois graines où les deux évacuations se terminent (panique 1, sans régulation), le mouillé est plus lent : +18,3, +0,7 et +8,5 s. Les moyennes de la ligne ne portent pas sur les mêmes graines. »
- [ ] **Step 3 :** ajouter aux limites : « Le modèle n'a pas de bruit dynamique : un bouchon formé ne se défait jamais. Chez Helbing et al. (2000), les bouchons sont intermittents. »
- [ ] **Step 4 :** vérifier `make lint`, puis pousser sur `exp/faster-is-slower` (accord de Lenny) avec `docs(panique): nuancer la lecture du bouchage sur cinq graines`.
- [ ] **Step 5 :** demander à Shaleena de confirmer (sa revue en faisait la condition), puis `gh pr merge 166 --squash --delete-branch`.

**Fini quand :** #166 est dans `dev`, et la relance sur les graines 1 à 10 est ouverte en issue (assignée à Lenny).

### Tâche 0.2 : #160 `feat(viz)` duel, mettre à jour puis fusionner

**Files :** Modify `README.md`, `src/viscocrowd/cli.py` (conflits) ; Create `experiments/demo/duel-plage-glissante.yaml`.

- [ ] **Step 1 :** `git switch feat/duel-sec-mouille && git merge origin/dev`. Dans les deux fichiers, garder les deux versions (paragraphe de `dev` puis celui de la PR ; les deux appels `ajouter_commande`).
- [ ] **Step 2 :** lancer `pytest tests/test_duel.py tests/test_cli.py tests/test_relecture_piscine.py -q` → tous passent.
- [ ] **Step 3 :** créer `experiments/demo/duel-plage-glissante.yaml` : copie de `experiments/piscine.yaml` avec `largeur_porte: 0.8`, `largeur_mouillee: 20.0`, `MOUILLE.acceleration_max: 1.0`, et en tête un commentaire qui cite #137 (Δt100 = 13,95 ± 1,53 s, 10/10) et précise « démonstration du mécanisme inertiel, pas la référence ».
- [ ] **Step 4 :** `viscocrowd duel experiments/demo/duel-plage-glissante.yaml --gif sorties/duel.gif` ; vérifier que les deux vues divergent visiblement avant 60 s.
- [ ] **Step 5 :** commit `docs(duel): versionner la configuration de démonstration (#137)`, push, commentaire dans la PR, puis `gh pr merge 160 --squash --delete-branch`.

### Tâche 0.3 : #164 `feat(viz)` carte de pression, demandes de relecture puis fusion

**Files :** Modify `README.md`, `src/viscocrowd/cli.py`, `src/viscocrowd/viz/pression.py`, `tests/test_pression.py` ; Create `experiments/demo/pression-porte-saturee.yaml`.

- [ ] **Step 1 :** mettre à jour avec `dev` (après 0.2), garder les deux versions des conflits.
- [ ] **Step 2 :** créer `experiments/demo/pression-porte-saturee.yaml` (porte 0,8 m, 150 agents, `facteur_vitesse: 2.0`, `temps_espacement: null`, `dt: 0.005`), et remplacer l'exemple du README par cette configuration, avec la phrase : « sur la référence régulée, presque aucun contact n'apparaît (98ᵉ centile 1,4 m/s²) ».
- [ ] **Step 3 : test qui échoue.** Dans `tests/test_pression.py` :

```python
def test_residu_nul_pour_une_colonne_equilibree():
    x = np.array([[0.0, 0.0], [0.4, 0.0], [0.8, 0.0]])
    a = np.array([[-1.0, 0.0]] * 3)
    lam, residu = forces_de_contact(
        x, a, np.array([[0, 1], [1, 2]]), np.array([False, False, True]), avec_residu=True
    )
    np.testing.assert_allclose(lam, [1.0, 2.0], atol=1e-9)
    assert residu == pytest.approx(0.0, abs=1e-9)


def test_residu_signale_une_poussee_inexpliquee():
    """Deux disques sans mur poussés dans le même sens : aucun λ ≥ 0 ne l'explique."""
    x = np.array([[0.0, 0.0], [0.4, 0.0]])
    a = np.array([[1.0, 0.0], [1.0, 0.0]])
    _, residu = forces_de_contact(
        x, a, np.array([[0, 1]]), np.zeros(2, dtype=bool), avec_residu=True
    )
    assert residu > 0.5
```

- [ ] **Step 4 :** ajouter le paramètre `avec_residu: bool = False` à `forces_de_contact(x, a, paires, contre_mur, *, avec_residu=False) -> np.ndarray | tuple[np.ndarray, float]` ; le résidu relatif vaut `‖Aλ − a‖ / max(‖a‖, 1e-12)`. La commande `pression` affiche le résidu de l'image exportée.
- [ ] **Step 5 :** contrôle « chaîne ou choc » : `viscocrowd pression experiments/demo/pression-porte-saturee.yaml --image /tmp/p1.png --instant 35`, puis la même chose avec `dt: 0.0025`. Noter le contact maximal aux deux pas dans la description. S'il double, écrire dans la docstring que les maxima sont des chocs, et retirer « 4,3 kN » de la description.
- [ ] **Step 6 :** commit `feat(pression): afficher le résidu des forces et versionner la démonstration`, push, commentaire, fusion.

### Tâche 0.4 : #165 `feat(modele)` égouttage, à laisser à Lenny

Le correctif touche au modèle (dépôt réparti sur l'empreinte) et oblige à remesurer tout le
tableau de validation. C'est à Lenny de le faire. Ce qu'il faut lui transmettre :

- [ ] dépôt sur les cases dont le centre est à moins de `r` de l'agent, poids normalisés (somme = volume du pas) ;
- [ ] test `test_film_independant_du_pas` : un baigneur seul, `pas = 0.25` puis `0.125`, film maximal égal à 10 % près ;
- [ ] mise à jour avec `dev` **après** #164, en gardant les deux mécanismes dans `simuler_piscine` et `ResultatPiscine`, puis relance de `test_mesurer_les_contraintes_ne_change_pas_la_trajectoire` et des tests de l'égouttage.

### Tâche 0.5 : donner l'avis promis dans #158

La revue de #163 annonce « J'en reparle dans #158 ».

- [ ] Commenter #158 : garder la référence sans navigation, présenter la navigation comme une variante au § 6 (figure avant/après, tableau de la piscine, E0 et l'anneau comme validation partielle), et demander l'essai `dispersion_vitesse: 0` avant toute conclusion sur les −4,1 s.
- [ ] Une fois les points de la revue traités par Shaleena, relire de nouveau #163 ; la fusionner en option désactivée apporte le crochet `facteur_individuel` dont D2 a besoin.

### Tâche 0.6 : attribuer les tâches de S8 à S15 (A1)

**Files :** Modify `docs/planning/README.md`.

- [ ] **Step 1 :** ouvrir une issue « Attribuer P6, M7, M9, R2, R5, R6, R7 avant le 24/11 », avec la proposition : R2 et R3 Hamza, M7 et M9 Shaleena, P6 et R7 Lenny, R5 et R6 les trois.
- [ ] **Step 2 :** après accord, PR `docs(planning): attribuer les tâches de S8 à S15` qui remplace chaque « À attribuer avant S8 » par le nom retenu, et remplit le tableau des disponibilités (C2).

---

## Vague 1 : confirmer, outiller, nettoyer

### B1 : `exp(balayage): confirmer l'effet inertiel à porte saturée sur les graines 11 à 20 (#59)`

**Branche :** `exp/confirmation-inertie`. **Files :** Create `docs/mesures/confirmation-inertie-2026-11-21/` ; Modify `docs/balayages-piscine.md`, `report/sections/06-resultats.tex`.

- [ ] **Step 1 :** écrire les critères dans la PR **avant** le calcul : effet confirmé si Δt100 > 0 sur au moins 9 graines sur 10 (graines 11 à 20) à a_max = 1 et 2 m/s², et moyenne supérieure à l'effet du pas de temps (#138).
- [ ] **Step 2 :** lancer, en arrière-plan :

```bash
viscocrowd balayer-piscine experiments/piscine.yaml --parametre adherence_mouille --valeurs 1 2 3.3 \
  --fixer largeur_porte=0.8 largeur_mouillee=20 --graines 11 12 13 14 15 16 17 18 19 20 \
  --sortie docs/mesures/confirmation-inertie-2026-11-21/adherence.json \
  | tee docs/mesures/confirmation-inertie-2026-11-21/sortie.txt
```

- [ ] **Step 3 :** tableau au format de #137 (t100 mouillé, J_s, Δt50, Δt100, décompte des signes) dans `balayages-piscine.md`, avec le commit mesuré et `modifications_locales: false`.
- [ ] **Step 4 :** si les critères tiennent, remplacer « exploratoire » par « confirmé sur les graines 11 à 20 » au § 6.5 du rapport ; sinon, écrire ce que la mesure montre, sans conclure.

**Fini quand :** les 60 évacuations sont dans le bilan JSON et le § 6.5 dit l'un ou l'autre.

### B2 : `exp(diagramme): mesurer le diagramme fondamental en écoulement libre sur la plage (#124)`

**Branche :** `exp/diagramme-ecoulement-libre`. Ce qui manque à M8 : un point de mesure **loin de la porte**, où la foule marche sans être bloquée.

- [ ] **Step 1 :** choisir la zone : rectangle convexe sur la plage de sortie, entre le coin du bassin et la porte, à au moins 5 m de la porte (pour que le flux n'y soit pas encore ralenti), hors du bassin. Écrire ses bornes dans la PR avant le calcul.
- [ ] **Step 2 :** ajouter l'option `--zone XMIN XMAX YMIN YMAX` à `diagramme-piscine` si elle n'existe pas (test : zone personnalisée → mêmes classes que la zone par défaut quand on passe les bornes par défaut).
- [ ] **Step 3 :** mesurer sur les graines 1 à 10, sec contre mouillé jusqu'à la porte (`largeur_mouillee=20`), à a_max de référence puis à 1 m/s².
- [ ] **Step 4 :** comparer `v(ρ)` à Weidmann (`observables/weidmann.py`) dans son domaine, et écrire la lecture dans `docs/diagramme-fondamental.md`. Mettre la figure au manifeste si elle entre dans le rapport.

### B3 : `docs(paramètres): mesurer les durées de franchissement à la piscine`

**Branche :** `docs/durees-franchissement`. Remplace deux hypothèses sans source (rebord 4 s, échelle 2 s) par une mesure du groupe.

- [ ] **Step 1 : protocole**, écrit dans `docs/mesures/franchissement-AAAA-MM-JJ/protocole.md` avant la séance : départ chronométré quand la main touche le bord ou l'échelle, arrêt quand les deux pieds sont sur la plage ; 3 personnes × 5 essais × 2 natures, à allure normale puis pressée.
- [ ] **Step 2 :** saisir les durées dans `chronos.csv` (`personne,nature,allure,essai,duree_s`).
- [ ] **Step 3 :** médiane et écart interquartile par nature et par allure, dans `docs/parametres-piscine.md` (statut « mesuré par le groupe, n = 15 »).
- [ ] **Step 4 :** si les valeurs pressées sortent des intervalles déjà balayés par #119, ouvrir une issue de décision (changer `piscine.yaml` oblige à refaire E1/E2) ; sinon, citer la mesure comme justification sans toucher la référence.

### C1, C2 : outillage rapide (plan détaillé dans `observables-outillage.md`)

- `chore(json): arrondir les bilans du diagramme fondamental` (`chore/arrondi-bilans`).
- `test(piscine): figer la référence pour détecter un changement involontaire` (`test/reference-figee`).

### A2 : ménage des branches (sans PR)

- [ ] **Step 1 :** lister les branches des PR fusionnées :

```bash
gh pr list --state merged --limit 200 --json headRefName --jq '.[].headRefName' | sort -u > /tmp/fusionnees.txt
git branch -r | sed 's|origin/||' | grep -vE '^(HEAD|main|dev)' | sort > /tmp/distantes.txt
comm -12 /tmp/fusionnees.txt /tmp/distantes.txt
```

- [ ] **Step 2 :** envoyer la liste au groupe, puis supprimer : `git push origin --delete <branche>` pour chacune (jamais `main` ni `dev`).
- [ ] **Step 3 :** un admin active la suppression automatique : `gh api -X PATCH repos/ViscoCrowd/ViscoCrowd-simulation -f delete_branch_on_merge=true`.

---

## Vague 2 : paramétrer, observer, illustrer

- **E1** `feat(cli): surcharger une configuration au lancement` et **E2** `feat(geometrie): répartir n échelles régulièrement` (plan `parametrage-lancement.md`).
- **C3** `feat(observables): mesurer les intervalles entre sorties successives` (plan `observables-outillage.md`), puis `exp(panique): tracer la durée des bouchons selon la panique`, sur les archives de la relance de #166 (graines 1 à 10).
- **C4** `feat(viz): tracer la carte des temps d'arrêt`.
- **C5** `refac(cli): déclarer les commandes de visualisation dans leurs modules`, **après** la vague 0.

### G1 : `docs(rapport): ajouter les figures des résultats (R2)`

**Branche :** `docs/figures-resultats`. Les figures existent déjà dans `docs/mesures/` ; il faut les rendre reproductibles et les mettre au rapport.

- [ ] **Step 1 :** retenir au plus 5 figures pour le § 6 : diagramme fondamental devant la porte (#133), effet de l'adhérence à porte saturée (#137 confirmé par B1), balayage de la porte et de la population (#128), *faster-is-slower* (#166), pose longue ou carte de pression (illustration).
- [ ] **Step 2 :** pour chacune, une entrée dans `experiments/manifeste.yaml` (`identifiant`, `produite_par` avec la commande exacte, `parametres`, `graine`, `resultat_attendu`), et l'image copiée dans `report/figures/`.
- [ ] **Step 3 :** `\includegraphics` et légende avec unités, graines et commit, dans `06-resultats.tex`.
- [ ] **Step 4 :** vérifier que le job « Reproductibilité des figures » passe et que `make report` compile.

---

## Vague 3 : modèle, analyse, publication

- **D1** `feat(piscine): décaler les départs par un temps de réaction (facultatif)`, puis `exp(balayage): tester l'effet tampon avec des départs échelonnés`.
- **D2** `feat(piscine): faire varier la profondeur du bassin (facultatif)`.
- **D3** `feat(piscine): choisir son site de sortie selon la file d'attente (facultatif)`, en bonus.

### G2 : `docs(rapport): rédiger l'analyse, la conclusion et le résumé (R3)`

**Branche :** `docs/analyse-conclusion`. **Files :** `report/sections/06-resultats.tex` (synthèse), `07-conclusion.tex`, `00-resume.tex`.

- [ ] **Step 1 : plan de l'analyse**, une phrase par résultat, chacun avec sa preuve : (1) à la référence, le mouillé ne change rien de détectable (E1/E2, #128) ; (2) avec une adhérence faible jusqu'à une porte saturée, l'inertie fait perdre du débit (#137, confirmé B1) ; (3) sans régulation, le sec bouche quand le mouillé passe, mais le mouillé est plus lent quand les deux passent (#166) ; (4) les deux mécanismes de la problématique existent, et c'est l'adhérence qui choisit lequel domine.
- [ ] **Step 2 : réponse à la problématique** (§ 7.1) : 10 à 15 lignes qui reprennent ces quatre points, sans chiffre qui ne figure pas au § 6.
- [ ] **Step 3 : analyse critique** (§ 7.2) : modèle 2D à chocs mous, aucun bruit dynamique (bouchons définitifs), taux de chute non calibrés, durées de franchissement, navigation non activée et pourquoi (#158).
- [ ] **Step 4 : pistes** (§ 7.3) : temps de réaction (D1), profondeur (D2), fluctuations, porte de secours.
- [ ] **Step 5 : résumé** : une demi-page au plus, écrit en dernier.
- [ ] **Step 6 :** relecture par les deux autres membres, `make report` vert.

### G3 : `docs(soutenance): préparer les réponses aux questions sur les ajouts récents`

**Files :** Modify `docs/repères-soutenance.md`. Une entrée par question, chacune avec la réponse en trois lignes et la PR qui la prouve : file indienne et navigation (#158, #163) ; chaîne de force ou choc (#164, tâche 0.3) ; bouchage définitif (#166) ; régulation et *faster-is-slower* (#166) ; pourquoi la traînée d'eau est désactivée (#165).

### A3 : `release(jalon-4): publier la piscine et ses campagnes`

**Préalable :** P6 livré, vague 0 fusionnée, CI de `dev` verte.

- [ ] **Step 1 :** écrire `docs/releases/jalon-4.md` sur le modèle de `jalon-3.md` (périmètre, PR intégrées, mesures, limites, tag).
- [ ] **Step 2 :** PR `dev` → `main`, fusion **par commit de fusion** : `gh pr merge <n> --merge` (jamais squash, `CONTRIBUTING.md` § 3.4).
- [ ] **Step 3 :** `git tag -a jalon-4 <commit de fusion> -m "Jalon 4 — piscine"`, `git push origin jalon-4`, puis `gh release create jalon-4 --notes-file docs/releases/jalon-4.md`.

---

## Vague 4 : bonus, seulement si la vague 3 est finie

| PR | Plan | Condition |
|---|---|---|
| E3 `feat(cli): lancer une simulation depuis un menu` | `parametrage-lancement.md` | E1 et E2 fusionnées |
| C6 `feat(viz): comparer n variantes côte à côte` | `observables-outillage.md` | #160, E1 et C5 fusionnées |
| C7 `chore(make): régénérer les films de la soutenance en une commande` | `observables-outillage.md` | C6, #164, #165 fusionnées |
| D5 `feat(piscine): coordonner la sortie par un maître-nageur` | `options-modele.md` | D3 fusionnée |
| F1 `docs(reglementation): confronter la porte au règlement de sécurité` | ci-dessous | aucune |
| Population hétérogène (enfants, nageurs faibles) | issue seulement | des données sourcées sur les rayons et les vitesses dans l'eau ; sans elles, ne pas l'ouvrir |
| F2 porte de secours | ci-dessous | après le rendu |

### F1 : confronter la porte au règlement de sécurité des établissements recevant du public

**Branche :** `docs/reglementation-porte`. Aucune ligne de code : une campagne et une page de doc.

- [ ] **Step 1 :** relever dans le texte officiel (règlement de sécurité contre l'incendie des ERP, dispositions générales sur les dégagements, et dispositions du type X pour les établissements sportifs couverts) la largeur d'une unité de passage, la largeur exigée pour 1 et 2 unités, et le nombre d'unités par effectif. **Recopier les articles cités** ; aucune valeur de mémoire.
- [ ] **Step 2 :** en déduire, pour 100, 150 et 200 baigneurs, la largeur réglementaire de la porte unique.
- [ ] **Step 3 :** `balayer-piscine --parametre n_agents --valeurs 100 150 200` à cette largeur, graines 1 à 10, sec et mouillé.
- [ ] **Step 4 :** `docs/reglementation.md` : tableau effectif / largeur réglementaire / t100 / débit, et la phrase de conclusion « une piscine conforme s'évacue en … selon le modèle », avec ses limites.

### F2 : porte de secours (après le rendu)

Changement de géométrie lourd (`Piscine.porte` devient une liste, sources multiples du champ
eikonal, une ligne de sortie et deux montants par porte, mesures par porte). À ne pas
commencer avant le 05/01 : il sort du sujet « goulot unique ». Ouvrir seulement une issue
qui décrit ces quatre changements.

---

## Avancement au 18 novembre 2026 (soir)

Toutes les PR attendent une relecture : **aucune n'a été fusionnée sans revue**. Les PR
empilées sont à fusionner dans l'ordre de leur base : GitHub remet d'office la bonne base
aux suivantes, puisque la suppression automatique des branches est active.

| Tâche | PR ou issue | Base | État |
|---|---|---|---|
| 0.1 #166, reformuler la lecture | #166 (commit `d231d63`) | dev | poussé, attend Shaleena |
| 0.2 #160, démonstration du duel | #160 fusionnée par Shaleena ; configuration dans #169 | dev | ouverte |
| 0.3 #164, résidu, démonstration, contrôle à Δt/2 | #164 | dev | poussé, fusionnable |
| 0.4 #165, dépôt sur l'empreinte | revue de #165 | – | à Lenny |
| 0.5 avis sur la navigation | #158 | – | posté |
| 0.6 attribuer S8 à S15 | #170, #190 | dev | proposition, à confirmer |
| A2 ménage des branches | #170 (liste) | – | 54 supprimées, suppression automatique active |
| B1 confirmation, graines 11 à 20 | #172 | dev | **effet inertiel confirmé** |
| B2 écoulement libre | anneau (#149, fusionné) ; suite #167 | – | couvert |
| B3 durées de franchissement | #185 (protocole) | dev | mesure à faire à la piscine |
| T0 utilitaires de test | #171 | dev | base de l'empilement |
| C1 arrondi des bilans | #176 | dev | ouverte |
| C2 référence figée | #175 | dev | ouverte, CI Linux verte |
| C3 intervalles entre sorties | #177 | #171 | ouverte |
| C4 carte des temps d'arrêt | #178 | dev | ouverte |
| C5 commandes de visualisation | #196 | dev | ouverte, **à fusionner en dernier** |
| C6 comparer n variantes | #182 | #173 | ouverte |
| C7 `make demo` | #197 | #182 | ouverte (3 min 27) |
| D1 temps de réaction | #181 | #171 | ouverte |
| D1, campagne tampon | #187 | #181 | **effet tampon : 10/10** |
| D2 profondeur variable | #186 | #171 | ouverte, sans effet à la référence |
| D3 + D5 choix du site, maître-nageur | #188 | #171 | ouverte, indication |
| E1 `--fixer` sur `simuler` | #173 | #171 | ouverte |
| E2 nombre d'échelles | #174 | #173 | ouverte |
| E3 menu de paramétrage | #183 | #174 | ouverte (`make menu`) |
| F1 règlement des ERP | #199 ; question ouverte #198 | dev | ouverte |
| F2 porte de secours | #193 | – | après le rendu |
| G1 figures du rapport | #184 (figure 8 en double) | dev | ouverte |
| G2 conclusion et résumé | #180 | #172 | ouverte, constat 3 à trancher |
| G3 questions de soutenance | #179 | dev | ouverte |
| A3 release `jalon-4` | #189 | dev | brouillon ; publication après P6 |

**Ordre de fusion conseillé** : #166, #164, #169, #184 ; #171, puis #173, #174, #183, #182 et
#197 ; #172, puis #180 ; #175, #176, #178, #179, #185 ; les options du modèle
(#181, #187, #186, #188) après décision du groupe, en résolvant les conflits de
`simuler_piscine` avec #164 et #165 ; #196 **en dernier**.

**Issues ouvertes le 18 novembre** : #191 (relancer #166 sur dix graines), #192 (confirmer
le tampon et le choix du site sur les graines 11 à 20), #193 (porte de secours), #194
(population hétérogène), #195 (deux corrections mineures), #198 (débit de la porte entre 0,8
et 0,9 m). Revue de #163 refaite le 18 au soir : les trois points sont traités.
