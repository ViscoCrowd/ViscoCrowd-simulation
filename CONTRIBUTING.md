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
issue  →  branche  →  commits  →  PR  →  revue  →  squash merge  →  branche supprimée
```

### 3.1 Branches

`main` est protégée : **pas de push direct**. Tout passe par une pull request.

| Préfixe | Pour quoi |
|---|---|
| `feat/` | nouvelle brique de modèle ou de code |
| `fix/` | correction d'un comportement faux |
| `exp/` | campagne de simulation, exploration de paramètres |
| `docs/` | rapport, cahier des charges, journal des décisions |
| `chore/` | outillage, CI, dépendances |

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

**Fusion** — `Squash and merge`, pour un historique de `main` lisible, une ligne par
contribution. La branche est supprimée automatiquement.

**Vous pouvez fusionner votre propre PR.** GitHub n'exige pas d'approbation : nous travaillons en
alternance, et une approbation bloquante immobiliserait une branche plusieurs jours dès que nos
emplois du temps ne coïncident pas.

Ce qui reste bloquant, et qui n'est pas négociable, c'est la **CI verte** — en particulier les
invariants physiques. Aucune PR ne peut les contourner.

Cette souplesse est une facilité d'organisation, pas une dispense de relecture : voir § 4.

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
