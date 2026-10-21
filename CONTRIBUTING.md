# Contribuer à ViscoCrowd

Ce document est notre méthode de travail. Il vaut pour les trois membres du groupe.

---

## 1. Principe directeur

> **Chaque membre doit pouvoir expliquer et modifier n'importe quelle partie du travail.**

Ce n'est pas une ambition, c'est une contrainte d'évaluation : en soutenance, les questions
portent sur l'ensemble du projet et s'adressent à chacun. Toute notre organisation en découle —
c'est pourquoi la revue croisée est obligatoire, et pourquoi le code est commenté en expliquant
*pourquoi*, pas *quoi*.

Corollaire pratique : **ne fusionnez jamais du code que vous ne sauriez pas réécrire.** Si une
PR vous est incompréhensible, le problème est la PR, pas vous. Demandez.

---

## 2. Mise en route

```bash
git clone git@github.com:ViscoCrowd/ViscoCrowd-simulation.git
cd ViscoCrowd-simulation
make install
make test
```

Si `make` n'est pas disponible (Windows sans Git Bash complet) :

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
pytest
```

---

## 3. Cycle de travail

```
issue  →  branche  →  commits  →  PR vers dev  →  revue  →  squash merge  →  branche supprimée
                                       jalon terminé  →  PR dev vers main  →  tag + release
```

### 3.1 Branches

`main` et `dev` sont protégées : **pas de push direct**, pas de force-push, et **elles ne sont
jamais supprimées**. Tout passe par une pull request.

- `dev` est la branche d'intégration : les branches de travail (`feat/`, `fix/`…) y arrivent.
- `main` est la branche présentable : elle ne reçoit que des briques terminées (voir § 3.4).

| Préfixe | Pour quoi |
|---|---|
| `feat/` | nouvelle brique de modèle ou de code |
| `fix/` | correction d'un comportement faux |
| `exp/` | campagne de simulation, exploration de paramètres |
| `docs/` | rapport, cahier des charges, journal des décisions |
| `chore/` | outillage, CI, dépendances |
| `release/` | instantané de jalon à publier, uniquement si un rattrapage est nécessaire |
| `sync/` | resynchronisation de `main` vers `dev` après publication |

```bash
git switch -c feat/projection-iterative
```

Nommez la branche d'après **ce qu'elle produit**, pas d'après qui la fait.

### 3.2 Commits

Format [Conventional Commits](https://www.conventionalcommits.org/), description en français à
l'infinitif :

```
type(portée): description courte

Corps facultatif : expliquer POURQUOI ce changement, pas ce qu'il fait —
le diff dit déjà ce qu'il fait.
```

```bash
feat(projection): ajouter la projection itérative de Gauss-Seidel
fix(integrateur): évaluer la contrainte à l'instant d'arrivée
docs(rapport): rédiger la section discrétisation
exp(goulot): balayer la largeur de porte de 0,6 à 1,8 m
```

Types : `feat`, `fix`, `docs`, `test`, `refac`, `exp`, `chore`.

Un commit = un changement cohérent. Un commit qui touche la projection *et* corrige une faute
dans le rapport est deux commits.

### 3.3 Pull requests

Le [gabarit de PR](.github/pull_request_template.md) se remplit tout seul à l'ouverture.

La section **Validation** est la plus importante, et elle attend des **chiffres**. « Ça a l'air
de marcher » ne passe pas la revue : donnez la violation maximale mesurée, l'écart constaté, le
temps d'exécution. C'est exactement ce que le barème du module évalue, et s'y entraîner à chaque
PR évite de devoir tout mesurer en catastrophe au mois de décembre.

**Avant d'ouvrir :**

```bash
make lint && make test
```

**Fusion** — `Squash and merge` vers `dev`, pour un historique lisible, une ligne par
contribution. La branche de travail peut être supprimée après fusion, **jamais `main` ni `dev`**.
Seule exception : les PR de synchronisation `sync/` conservent leurs commits de fusion (§ 3.4).

**Vous pouvez fusionner votre propre PR.** GitHub n'exige pas d'approbation : nous travaillons en
alternance, et une approbation bloquante immobiliserait une branche plusieurs jours dès que nos
emplois du temps ne coïncident pas.

Ce qui reste bloquant, et qui n'est pas négociable, c'est la **CI verte** — en particulier les
invariants physiques. Aucune PR ne peut les contourner.

Cette souplesse est une facilité d'organisation, pas une dispense de relecture : voir § 4.

### 3.4 Passer de `dev` à `main`

Les jalons sont définis dans la [spécification § 9](docs/superpowers/specs/2026-10-06-viscocrowd-design.md#9-jalons),
leur avancement dans le [planning](docs/planning/README.md) et leur publication dans le
[registre des livraisons](docs/livraisons.md). Une tâche terminée dans un jalon encore ouvert
reste sur `dev` : livrer G1 ne clôt pas à lui seul le jalon 3.

À la fin d'un jalon, stabiliser `dev` puis ouvrir une PR `dev` → `main`. Elle indique le
jalon, son périmètre, les PR intégrées, les mesures, les limites connues et le tag prévu.
Les travaux du jalon suivant attendent sur leurs branches jusqu'à la publication.
**Avant fusion**, les trois conditions suivantes doivent être réunies :

1. **Toute la CI de la PR est verte**, y compris Docker et, lorsqu'il est concerné, le rapport.
2. **Le périmètre du jalon est terminé et documenté**, ou une version de rendu est explicitement
   délimitée ; aucun travail incomplet n'est annoncé comme une livraison achevée.
3. **La relecture croisée est traçable**, avec les chiffres de validation. Les revues des PR
   constitutives peuvent servir de preuve si leurs corrections sont incluses sans modification ;
   tout changement supplémentaire doit être relu. Une revue automatisée ne vaut pas accord collectif.

Fusionner par **squash vers `main`**, puis publier un **tag annoté `jalon-N` sur le commit
exact résultant de cette fusion**. Une **GitHub Release du même nom** accompagne ce tag :
elle contient le périmètre, les commandes de reproduction, les résultats et les limites.
Le tag est le repère Git ; la release est sa fiche de livraison. Ils sont complémentaires.

Ne jamais créer le tag sur le `HEAD` de travail par défaut, déplacer un tag publié ou
antidater une régularisation. Un correctif ultérieur passe par de nouvelles PR et, si nécessaire,
une nouvelle version `jalon-N.1`. Une version figée est aussi prévue avant chaque échéance
(rapport le 5 janvier 2027, transparents le 18 janvier, soutenance le 19 janvier).

Après fusion et vérification du SHA sur `main` (remplacer les valeurs entre chevrons) :

```bash
git fetch origin --tags
git merge-base --is-ancestor <sha_publication> origin/main
git tag -a jalon-N <sha_publication> -m "Jalon N : <intitule>"
git push origin refs/tags/jalon-N
gh release create jalon-N --verify-tag --title "Jalon N — <intitule>" --notes-file notes.md
```

**Resynchroniser par PR, sans push direct.** Le squash crée un nouveau commit sur `main` ;
il doit devenir un ancêtre de `dev` pour que la prochaine promotion n'inclue pas à nouveau
l'ancien jalon. Depuis un arbre propre :

```bash
git switch -c sync/main-jalon-N origin/dev
git merge origin/main
# Résoudre les conflits en conservant les travaux plus récents de dev.
git push -u origin HEAD
gh pr create --base dev --head sync/main-jalon-N
```

Après revue et CI verte, fusionner cette PR avec **Create a merge commit** (`gh pr merge
<numero> --merge`), jamais squash ou rebase : ces modes perdraient l'ascendance recherchée.
Vérifier ensuite `git merge-base --is-ancestor origin/main origin/dev` après un fetch.
Si une protection interdit le commit de fusion, faire corriger la règle par un administrateur ;
ne pas contourner la protection par un push direct ou forcé.

**Rattrapage historique.** Si `dev` contient déjà un jalon suivant incomplet, une branche
`release/jalon-N` peut partir du dernier instantané complet de `dev`, identifié par SHA.
Seuls des correctifs et documents déjà intégrés et relus dans `dev` peuvent y être repris,
avec leurs références ; toute correction nouvelle repasse d'abord par une PR vers `dev`.
Les notes propres à la version, son registre et ses indications de périmètre sont finalisés
dans la PR de publication, puis repris dans `dev` lors de la synchronisation.
La PR de publication vers `main` explique cette exception, rejoue la validation sur son
contenu exact, puis suit les mêmes règles de tag, release et synchronisation. Ne jamais
reculer `dev` ni réécrire les anciens commits pour simuler un historique parfait.

---

## 4. Revue

Rien ne vous empêche techniquement de fusionner sans relecture. La question n'est donc pas « ai-je
le droit », mais **« est-ce que mes deux coéquipiers sauront défendre ce code en soutenance »** —
et la réponse ne dépend que de vous.

En pratique : demandez une relecture par défaut, et fusionnez sans attendre quand la PR est
mineure (une faute de frappe, une section de rapport, un paramètre de figure) ou quand personne
n'est disponible et que la CI est verte. Si vous fusionnez seul une PR qui touche au **modèle**
ou au **schéma numérique**, prévenez les autres : ce sont les parties sur lesquelles vous serez
tous les trois interrogés.

**Côté auteur** — une PR qui dépasse ~400 lignes de diff est difficile à relire sérieusement.
Découpez. Si vous ne pouvez pas, dites dans la description par où commencer.

**Côté relecteur** — vous engagez votre capacité à défendre ce code en soutenance. Vérifiez :

- [ ] Je saurais réexpliquer ce que fait ce code, et pourquoi il le fait ainsi.
- [ ] Les grandeurs physiques portent leurs unités, et les ordres de grandeur sont plausibles.
- [ ] La validation annoncée est chiffrée, et les chiffres sont cohérents.
- [ ] Les tests couvrent le comportement, pas seulement le passage dans le code.
- [ ] Rien de spécialisé n'a été introduit en dépendance (cf. § 6).

Une question en revue n'est pas un reproche. « Pourquoi ce facteur 2 ? » est souvent la
meilleure contribution d'une relecture.

---

## 5. Tests

```bash
make test                      # tout, sauf les scénarios lents
pytest -m invariant            # uniquement les invariants physiques
pytest -m "not slow"           # ce que fait la CI
```

Trois niveaux :

| Marque | Nature | Dans la CI |
|---|---|---|
| *(aucune)* | unitaire — une fonction, un comportement | ✅ |
| `invariant` | propriété physique vraie à chaque pas de temps | ✅ |
| `slow` | scénario complet, campagne de simulation | ❌ (manuel) |

**Les invariants sont la garde rapprochée du projet.** Non-interpénétration, non-sortie du
domaine, conservation du nombre d'agents, décroissance de l'énergie en domaine fixe : ils
tournent à chaque PR et rendent une régression physique impossible à fusionner.

Si vous corrigez un comportement faux, **écrivez d'abord le test qui échoue**. Sans lui, rien ne
garantit que le bug ne reviendra pas, ni même que vous avez corrigé ce que vous croyez.

### Un test qui échoue n'accuse pas forcément le code

Nos trois premiers échecs venaient tous d'attentes de test fausses, pas du moteur. Avant de
modifier le code, vérifiez **ce que la physique prédit vraiment** — au besoin en mesurant.
Affaiblir un seuil de test pour faire passer la CI est la pire issue possible : on perd le test
*et* on garde le bug éventuel.

---

## 6. Dépendances

Les consignes du module sont nettes : bibliothèques **généralistes** autorisées (calcul
numérique, algèbre linéaire, tracé de courbes, structures de données), bibliothèques
**spécialisées** exclues (moteurs physiques, moteurs de jeu, dynamique moléculaire, simulation
de foule prête à l'emploi).

> Le modèle lui-même — forces d'interaction, conditions aux limites, schéma d'intégration en
> temps — doit être écrit par le groupe.

Ajouter une dépendance se discute **en issue avant la PR**. En cas de doute sur une
bibliothèque, on pose la question à l'enseignant plutôt que de trancher seuls.

---

## 7. Reproductibilité

Trois règles, non négociables :

1. **Aucun appel direct à `numpy.random`.** Tout l'aléa passe par `viscocrowd.core.rng`, qui
   impose une graine explicite. C'est la seule façon de garantir qu'aucune source d'aléa
   n'échappe à la graine déclarée.
2. **Toute figure du rapport est inscrite dans [`experiments/manifeste.yaml`](experiments/manifeste.yaml)**,
   avec sa configuration et sa graine. Une figure dont on ne sait plus avec quels paramètres
   elle a été produite est inutilisable dans le rapport.
3. **Aucune valeur numérique en dur dans le code de scénario.** Les paramètres vivent dans les
   configurations YAML de `experiments/`.

---

## 8. Décisions de modélisation

Toute décision de modélisation un peu structurante va dans
[`docs/journal-decisions.md`](docs/journal-decisions.md) : la décision, les options écartées,
et pourquoi.

**Consignez aussi les pistes qui n'ont pas abouti.** Les consignes précisent qu'elles font
partie du travail et que leur analyse est valorisée. Une impasse documentée en octobre est une
section de rapport en décembre ; la même impasse oubliée n'est rien.

---

## 9. Répartition des tâches

Le rapport doit comporter en annexe un tableau indiquant qui a travaillé sur quoi et dans
quelle proportion, et la répartition doit être **équilibrée sur le fond** : aucun membre ne peut
se cantonner à la rédaction ou à la préparation des transparents.

L'historique git le documente au fil de l'eau, à condition que chacun pousse son propre travail
sous son propre compte. C'est la raison pratique pour laquelle on ne se prête pas de session.
