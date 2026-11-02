# Tests lents en intégration continue (CI)

Guide d'exploitation du workflow `.github/workflows/tests-lents.yml` (issue #61).

---

## 1. Rôle et périmètre

La suite de tests rapides habituelle (`pytest -m "not slow"`, environ 2 minutes) valide
le typage, le style, les tests unitaires et les invariants locaux à chaque push et PR.
Elle exclut volontairement les scénarios longs pour ne pas bloquer le flux de développement.

Les **tests lents** (`pytest -m slow`) exécutent :
- Les scénarios physiques complets sur des durées longues (banc couloir, tassement, piscine complète à 100 agents) ;
- Les vérifications asymptotiques de non-recouvrement et de conservation d'énergie ;
- Les tests d'invariance statistique et de sensibilité aux tolérances de projection.

---

## 2. Déclenchements et automatisation

Le workflow `tests-lents.yml` s'exécute selon trois modalités :

| Modalité | Déclencheur | Cible |
|---|---|---|
| **Push automatique** | `push.branches: [dev]` | Exécuté à chaque fusion de PR sur `dev` (`cancel-in-progress: false` pour ne pas interrompre un audit en cours). |
| **Cron hebdomadaire** | `schedule: - cron: "23 5 * * 1"` | Chaque lundi à 05:23 UTC en ciblant explicitement `dev` (`ref: dev`). |
| **Lancement manuel** | `workflow_dispatch` | Déclenché à la demande depuis l'onglet Actions (sélectionner la branche `dev`) ou via `gh workflow run tests-lents.yml --ref dev`. |

### Limitation GitHub importante (branche par défaut)

> [!IMPORTANT]
> GitHub Actions n'active les déclencheurs planifiés (`schedule`) et manuels (`workflow_dispatch`)
> **que si le fichier de workflow est présent sur la branche par défaut du dépôt** (actuellement `main`).
>
> Tant que `tests-lents.yml` réside uniquement sur `dev`, seuls les pushs sur `dev` déclenchent
> les tests. Dès que le fichier est fusionné sur `main` (lors de la livraison d'un jalon), le cron
> hebdomadaire et le bouton « Run workflow » deviennent actifs.
>
> Dans le cron, le checkout cible explicitement `dev` (`ref: dev`) afin de surveiller
> l'intégration continue avant toute mise en production ; pour un lancement manuel (`workflow_dispatch`),
> `actions/checkout` utilise `github.ref`, d'où l'importance de cibler explicitement `--ref dev` si l'on
> souhaite auditer `dev` plutôt que `main`.

---

## 3. Matrice multiplateforme et traçabilité

Le workflow teste trois environnements distincts avec `fail-fast: false` (un échec sur un système
n'interrompt pas les deux autres, ce qui permet de diagnostiquer immédiatement si un défaut est
spécifique à un OS) :
- `ubuntu-latest`
- `macos-latest`
- `windows-latest`

### Versions figées et timeouts

- **Reproductibilité stricte** : Python 3.12 et installation à partir de `requirements.lock.txt` avec
  `pip install --no-deps -e .` et `pip check` pour interdire toute mise à jour silencieuse de dépendance.
- **Timeouts différenciés** : 20 minutes sur Linux et macOS, 40 minutes sur Windows
  (le système de fichiers et les E/S y sont structurellement plus lents).

### Artefacts archivés

À chaque exécution (même en échec, grâce à `if: always()`), les artefacts suivants sont
conservés pendant 30 jours sous `tests-lents-<os>` :
1. `resultats-lents.xml` : rapport structuré JUnit détaillant le statut et la durée de chaque test ;
2. `environnement.txt` : commit exact testé (`git rev-parse HEAD`), version de Python et `pip freeze` complet.

---

## 4. Conduite à tenir en cas d'échec

Lorsqu'un job de tests lents échoue sur `dev` ou en cron, **ne jamais relever arbitrairement un seuil**
pour masquer l'erreur. Suivre ce protocole :

### Étape 1 : Isoler la nature de l'échec

1. Ouvrir l'exécution GitHub Actions en défaut et télécharger l'artefact `tests-lents-<os>`.
2. Consulter `resultats-lents.xml` pour repérer le test et la pile d'appel exacte.
3. Distinguer :
   - **Timeout machine** : le job s'est arrêté à 20 ou 40 minutes sans erreur de test (saturation temporaire des runners GitHub).
   - **Régression physique (`invariant`)** : violation de paroi > 0, recouvrement > tolérance, ou augmentation d'énergie mécanique sur domaine fixe.
   - **Divergence numérique multiplateforme** : un test échoue sur une architecture spécifique (ex. macOS arm64 vs Linux x86-64) en raison d'un arrondi flottant ou d'une tolérance trop rigide sur une distribution aléatoire.

### Étape 2 : Reproduire localement

Rejouer le test fautif dans le même environnement virtuel figé :

```bash
# Lancer uniquement le test lent concerné avec affichage verbeux
pytest -m slow -k "<nom_du_test>" -v
```

### Étape 3 : Traiter et documenter

- Si une régression physique est avérée : identifier le commit incriminé sur `dev`, ouvrir une issue avec le log JUnit, et soumettre un correctif via PR.
- Si une dispersion entre architectures est constatée : utiliser un test statistique sans hypothèse arbitraire (ex. test de permutation appariée comme dans `test_densite.py`), et justifier le critère dans `docs/journal-decisions.md`.
