# ViscoCrowd — Spécification de conception

**Module** R5.12 — Modélisation mathématique · BUT 3 Informatique (alternance) · 2026-2027
**Groupe** Karrouchi Hamza (`CodeByHaamza`), Lesueur Shaleena (`shalee-pnt`), Mongrandi Lenny (`lennymgrd`)
**Date** 6 octobre 2026
**Statut** Voir le [cadrage et la trace de validation](../../validation-sujet.md#trace-de-validation)

La date ci-dessus est celle de création du document.

---

## 1. Problématique

> Comment la succession d'une extraction aquatique répartie (franchissement des rebords et
> échelles) et d'un goulot d'étranglement unique en milieu sec, couplée à l'inertie d'une zone
> de carrelage mouillé, altère-t-elle le diagramme fondamental débit/densité d'une foule en
> panique ?

### 1.1 Scénario physique

Évacuation d'urgence d'une piscine couverte. La foule traverse trois milieux successifs aux
propriétés mécaniques distinctes :

1. **Bassin** — milieu aquatique. Forte traînée visqueuse, vitesse de déplacement faible.
   La sortie se fait par une **extraction répartie** : les nageurs franchissent soit le rebord
   (franchissable sur toute sa longueur, mais lentement), soit l'une des échelles (peu
   nombreuses, mais rapides). Chaque point de franchissement est à **capacité unitaire**.
2. **Plage mouillée** — carrelage humide. Faible coefficient d'adhérence : l'accélération
   disponible est bornée, l'agent ne peut ni s'arrêter ni tourner rapidement. C'est le terme
   d'**inertie** de la problématique.
3. **Zone sèche et goulot** — adhérence nominale, puis rétrécissement vers une porte unique.
   C'est là que le diagramme fondamental est mesuré.

### 1.2 Hypothèse de travail

Deux mécanismes antagonistes sont plausibles, et les départager constitue le cœur du travail :

- **Hypothèse tampon** — l'extraction répartie et la traversée de la zone mouillée
  *désynchronisent* les arrivées au goulot. La densité de pointe y diminue, et le débit
  augmente par rapport à une alimentation directe.
- **Hypothèse inertielle** — la faible adhérence empêche les agents de réguler leur approche.
  Ils dépassent leur cible, se percutent, et la densité effective au goulot *augmente*,
  dégradant le débit (phénomène apparenté au *faster-is-slower*).

Le résultat attendu est un déplacement mesurable de la branche congestionnée du diagramme
fondamental, dont on cherchera le signe et l'amplitude en fonction de la longueur et de
l'adhérence de la zone mouillée.

---

## 2. Modèle mathématique

### 2.1 Cadre retenu

Modèle particulaire avec **principe d'exclusion dur**, dans le prolongement direct du cours :
pas libre, puis **projection sur l'ensemble des configurations admissibles**. C'est le cadre
annoncé en fin du document d'introduction (« un pas libre, puis une projection sur un convexe ;
seul le convexe change, et il devient nécessaire de calculer la projection de manière
itérative »).

Référence : Maury & Venel, *A mathematical framework for a crowd motion model* / *Handling
congestion in crowd motion modelling*.

### 2.2 État

Pour chaque agent `i` parmi `N` : position `x_i` dans `R²` (m), vitesse `v_i` dans `R²`
(m·s⁻¹), rayon `r_i` (m). L'état global est noté `X = (x_1, …, x_N)` dans `R^{2N}`.

### 2.3 Vitesse désirée

`U_i = s(x_i) · e(x_i)` où

- `e(x)` est la direction de guidage, issue d'un **champ de plus court temps de parcours**
  (§ 2.6) ;
- `s(x)` est la vitesse souhaitée, fonction du milieu et du niveau de panique.

### 2.4 Pas libre, avec milieu

Le milieu agit par deux paramètres : un **temps de relaxation** `τ(x)` et une **accélération
maximale** `a_max(x)` (traction disponible).

```
a_i      = clip( (U_i − v_i) / τ(x_i),  |a| ≤ a_max(x_i) )
v_libre  = v_i + Δt · a_i
x_libre  = x_i + Δt · v_libre
```

Le schéma est **semi-implicite** (la position est mise à jour avec la vitesse nouvelle),
conformément au cours.

| Milieu | `τ` | `a_max` | Lecture physique |
|---|---|---|---|
| Eau | court | modérée | fortement amorti, mais lent : on s'arrête vite, on n'avance pas vite |
| Carrelage mouillé | long | **faible** | traction limitée : impossible de s'arrêter ou de tourner vite |
| Sol sec | court | élevée | régulation nominale de la vitesse |

C'est le contraste `a_max(mouillé)` très inférieur à `a_max(sec)` qui porte l'effet d'inertie
étudié.

### 2.5 Projection — contrainte d'exclusion

L'ensemble admissible est

```
K = { X : |x_i − x_j| ≥ r_i + r_j  pour i ≠ j,  et  x_i dans Ω (domaine) }
```

**`K` n'est pas convexe** : la contrainte de non-recouvrement est l'extérieur d'une boule dans
l'espace des configurations. On suit Maury & Venel en **linéarisant les contraintes autour de
la configuration courante** `X^n` :

```
D_ij(X) = |x_i − x_j| − (r_i + r_j) ≥ 0
D_ij(X) ≈ D_ij(X^n) + G_ij(X^n) · (X − X^n) ≥ 0
```

où `G_ij` vaut `−e_ij` sur la composante `i` et `+e_ij` sur la composante `j`, avec
`e_ij = (x_j − x_i)/|x_j − x_i|`. L'ensemble linéarisé est une **intersection de demi-espaces**,
donc convexe : la projection y est bien définie et unique.

**Résolution** — algorithme itératif de type **Jacobi** projeté sur les contraintes actives,
accéléré par une **extrapolation de Nesterov retardée** :

```
entrées : x_libre, rayons r, tolérance ε, budget n_max, domaine Ω
X ← x_libre ;  n ← 0                           n : balayages consommés pendant cet appel
résidu ← recouvrement maximal de X, sur toutes les paires
répéter :
    P ← paires à distance < r_i + r_j + m      grille de hachage, marge m = r_min / 2
    X_précédent ← X ;  ρ ← 0                   ρ : rang depuis la dernière recherche de P
    tant que n < n_max et (n = 0 ou résidu > ε) :
        κ ← ρ − k₀ ;  β ← κ / (κ + 3) si κ > 0, sinon 0           k₀ = 80
        Y ← X + β · (X − X_précédent)
        si β > 0 : projeter Y sur Ω            le point extrapolé peut sortir du domaine
        pour toutes les paires (i,j) de P en recouvrement, SIMULTANÉMENT :
            δ_ij ← ½ (r_i + r_j − |y_j − y_i|) / max(c_i, c_j)
            y_i ← y_i − δ_ij e_ij ;  y_j ← y_j + δ_ij e_ij
        projeter Y sur Ω                       toujours en dernier : parois exactes
        X_précédent ← X ;  X ← Y ;  n ← n + 1 ;  ρ ← ρ + 1
        résidu ← recouvrement maximal sur les paires de P
    résidu ← recouvrement maximal sur TOUTES les paires (nouvelle recherche, sans marge)
jusqu'à résidu ≤ ε ou n ≥ n_max
si résidu > ε : compter une non-convergence (et lever ProjectionNonConvergee en mode strict)
rendre X
```

`c_k` est le nombre de recouvrements de l'agent `k` dans le balayage courant. Trois détails du
pseudo-code comptent pour retrouver le comportement du moteur :

- **Les paires sont cherchées avec une marge, puis vérifiées sans marge.** Les agents bougent
  pendant les balayages : une paire absente de `P` peut se créer. Si la vérification finale en
  trouve une, on recherche les paires et on continue, dans le même budget `n_max`.
- **Le rang d'extrapolation `ρ` repart de zéro à chaque recherche de paires.** L'extrapolation
  prolonge le dernier déplacement ; après une nouvelle recherche, ce déplacement concerne une
  autre liste de contraintes, et on ne veut pas reprendre à une valeur de `β` déjà élevée.
- **Au moins un balayage est toujours fait (`n = 0`)**, même sans recouvrement : la projection
  sur `Ω` doit s'appliquer à `x_libre`, qui peut être sorti du domaine.

Une projection qui n'atteint pas `ε` dans son budget n'est jamais silencieuse : elle est comptée
(`non_convergences`, `recouvrement_max`). En mode strict elle interrompt la simulation ; sinon,
`verifier_convergence()` doit être appelé avant d'exploiter une trajectoire. Le mode permissif
reste le défaut, parce que les études de limites ont besoin de **mesurer** l'échec.

Jacobi traite toutes les paires à la fois, ce qui se vectorise en NumPy, là où Gauss-Seidel
impose une boucle Python paire par paire. Mesuré : Jacobi demande **plus** de balayages (35 à
125 contre 13 à 19, de 12 à 600 agents) mais reste **environ deux fois plus rapide** en temps
réel. C'est la seule justification du choix.

Trois points du pseudo-code ci-dessus sont des corrections apportées après mesure, et non des
détails d'implémentation :

- **La pondération est portée par la PAIRE, pas par l'agent.** Diviser les corrections reçues
  par un agent par son nombre de contacts n'est pas symétrique en `(i, j)` : dès que deux
  voisins n'ont pas le même nombre de contacts, les deux réactions d'une paire cessent d'être
  opposées et **le centre de gravité de la foule dérive** sans aucune force extérieure
  (2,2·10⁻³ m mesurés sur un amas de 12 agents). Avec `1/max(c_i, c_j)`, l'amortissement est le
  même et la conservation est exacte (10⁻¹⁷ m).
- **L'extrapolation ne s'allume qu'au-delà de `k₀ = 80` balayages, et sa rampe repart de zéro.**
  Elle écarte les agents au-delà du contact, et ce jeu est définitif puisque les corrections ne
  font qu'écarter. Allumée dès le premier balayage, elle restituait jusqu'à 10⁻³ de l'énergie
  d'arrivée sur un choc à contacts multiples — le choc n'était plus mou. Un choc entre quelques
  agents se résout en moins de 80 balayages et **ne reçoit donc pas d'extrapolation** : ce
  mécanisme de rebond ne le touche pas, ce qui ne le rend pas exact pour autant (voir les limites
  ci-dessous). Seules les longues chaînes de contacts, où l'accélération est indispensable, la
  reçoivent. Restitution ramenée à 9,0·10⁻⁷.
- **Aucune correction ne dépasse le recouvrement.** La correction élémentaire d'une paire est
  calculée à partir de son recouvrement (la moitié pour chaque agent), puis pondérée par
  `1/max(c_i, c_j)` : le déplacement appliqué en un balayage peut donc être **inférieur** au
  recouvrement, jamais supérieur, et plusieurs balayages sont alors nécessaires. Une
  sur-relaxation (facteur > 1) convergerait plus vite, mais séparerait les agents au-delà du
  contact et introduirait un rebond artificiel dans la vitesse relue (§ 2.8), donc un choc qui ne
  serait plus mou.

**Limites connues sur les contacts multiples.** L'algorithme vise le **non-recouvrement à la
tolérance près** ; il ne garantit pas que des agents en contact finissent tangents. Seule une
paire isolée est corrigée exactement, en un balayage (`TestPaire`). Dès que trois agents sont en
contact **mutuel**, leurs corrections simultanées, exactes prises une à une, dépassent une fois
additionnées : un triangle qui s'effondre finit avec un jeu d'environ **1,7·10⁻³ m** au-delà du
contact, soit 0,85 % du diamètre d'un agent de 20 cm. Ce jeu ne doit rien à l'extrapolation (le
triangle se résout en 5 balayages, bien avant le rang 80) et, contrairement au jeu d'un tas, **il
ne décroît pas quand Δt diminue** (1,69·10⁻³ m à Δt = 4·10⁻³ s comme à 2·10⁻³ s). Il est suivi dans
l'[issue #10](https://github.com/ViscoCrowd/ViscoCrowd-simulation/issues/10) et doit être traité,
ou au moins borné et déclaré, avant le jalon 5 : les empilements au goulot sont exactement le cas
où il fausserait la densité locale, abscisse du diagramme fondamental.

**Ce que l'algorithme ne garantit pas.** La projection sur l'ensemble linéarisé est unique, mais
l'algorithme n'est pas construit pour la calculer. Des corrections découplées, répétées jusqu'à
l'admissibilité, cherchent une configuration *admissible* sans minimiser explicitement
`|X − x_libre|`, et aucun balayage ne peut rapprocher deux agents qu'un précédent a trop écartés.
Il n'y a donc **pas de garantie générale d'optimalité euclidienne**. Ce n'est pas la même chose
qu'une impossibilité : pour une paire isolée, la correction en un balayage est exactement la
projection (`TestPaire`).

La comparaison à Gauss-Seidel le confirme sans le démontrer. Aucune des deux méthodes ne déplace
systématiquement moins que l'autre : sur un triangle serré c'est Jacobi qui déplace le moins, sur
un amas de 100 agents c'est Gauss-Seidel, et les deux solutions s'éloignent jusqu'à 1,4·10⁻² m.
Quand deux résultats sont admissibles pour les mêmes contraintes, celui qui déplace strictement
plus n'est pas le minimiseur **dans ce cas précis** : c'est un contre-exemple ponctuel. Mais cette
alternance ne prouve pas qu'une méthode ne calcule jamais le minimum. La formulation retenue est
donc :

> Les résultats numériques ne démontrent pas que les configurations obtenues minimisent
> systématiquement la distance à la position libre. L'algorithme recherche une configuration
> admissible à la tolérance près, sans garantie générale d'optimalité euclidienne.

**Conséquence rédactionnelle, qui engage le rapport et la soutenance** : écrire « configuration
admissible obtenue par projections successives », et **jamais** « projection de Gauss-Seidel »
ni « projection euclidienne sur K ».

Choix, impasses et mesures détaillés dans le
[journal des décisions](../../journal-decisions.md) (entrée du 12 octobre 2026).

Le choix de Jacobi vectorisé et le déclenchement de Nesterov après 80 balayages ont été validés
collectivement par les trois membres du groupe, selon la confirmation communiquée le
13 octobre 2026. Cette décision est consignée dans le journal (entrée du 13 octobre) et dans
l'[issue #13](https://github.com/ViscoCrowd/ViscoCrowd-simulation/issues/13).

Le critère d'arrêt est le recouvrement résiduel maximal, qui devient **l'indicateur de
validation n°1** (§ 5). La tolérance atteinte est une grandeur à mesurer et à publier, pas à
supposer.

Recherche des paires voisines par **grille de hachage spatial**, pour éviter le coût en `N²`.

### 2.6 Champ de guidage

On résout l'**équation eikonale** `|∇φ(x)| = 1 / F(x)` avec `φ = 0` sur la sortie, où `F(x)`
est la vitesse de déplacement maximale locale (donc dépendante du milieu). La direction de
guidage est `e = −∇φ / |∇φ|`.

Résolution par **Fast Marching** sur une grille régulière, implémenté par le groupe (algorithme
numérique généraliste).

Conséquence recherchée : puisque `F` encode la lenteur de l'eau et la rapidité des échelles, le
champ `φ` **arbitre de lui-même** entre « sortir par le rebord près de moi » et « nager jusqu'à
l'échelle ». Le partage du flux entre points d'extraction devient une **sortie du modèle**, et
non un paramètre imposé — c'est précisément l'objet de la partie « extraction répartie » de la
problématique.

### 2.7 Franchissement à capacité limitée

Le rebord et les échelles sont des **sites de franchissement** : chacun a une capacité de 1
agent et une durée de traversée `T_franchissement`. Un agent engagé est immobilisé le temps de
la montée, puis réintroduit côté sec.

- Rebord : sites nombreux (discrétisation du périmètre), `T` long (hissage).
- Échelle : sites rares, `T` court.

### 2.8 Mise à jour de la vitesse

```
v_i^{n+1} = (x_i^{n+1} − x_i^n) / Δt
```

**C'est ici que le choc se produit.** La vitesse n'est pas transportée d'un pas à l'autre : elle
est recalculée à partir du déplacement effectivement réalisé. Si la projection a annulé le
déplacement normal, elle annule du même coup la composante normale de la vitesse — traduction
discrète de la loi de choc mou.

---

## 3. Observables

| Observable | Définition | Unité |
|---|---|---|
| Densité | inverse de l'aire de la cellule de Voronoï de l'agent, moyennée sur la zone de mesure | pers·m⁻² |
| Débit | comptage des franchissements d'une ligne de largeur `w` sur une fenêtre `T` | pers·m⁻¹·s⁻¹ |
| Diagramme fondamental | `q` en fonction de `ρ`, agrégé par classes de densité | — |
| Temps d'évacuation | instant de sortie du dernier agent | s |
| Recouvrement résiduel | maximum sur les paires de la pénétration `(r_i + r_j − distance)` positive | m |

La **densité de Voronoï** (Steffen & Seyfried) est préférée au comptage en boîte : elle donne un
champ de densité continu et reste fiable avec peu d'agents, là où le comptage en boîte produit
des paliers entiers qui bruitent le diagramme.

---

## 4. Protocole expérimental

| # | Configuration | Objet |
|---|---|---|
| E0 | Goulot sec seul, alimentation homogène | **Étalonnage** : le diagramme fondamental doit retrouver la littérature |
| E1 | Piscine + extraction répartie + goulot, **sans** zone mouillée | Isole l'effet de l'extraction répartie |
| E2 | Scénario complet **avec** zone mouillée | Mesure l'effet d'inertie |
| E3 | Balayage : longueur `L` et adhérence `a_max` de la zone mouillée | Courbe de réponse |
| E4 | Balayage : nombre d'échelles, largeur du goulot, niveau de panique | Sensibilité aux paramètres de scénario |

Chaque point de mesure est répété sur **au moins 10 graines** ; les figures portent des barres
d'erreur. Les graines sont fixées et consignées.

---

## 5. Validation

Les consignes exigent une validation chiffrée, pas une impression visuelle. Chaque point
ci-dessous produit un **nombre** reporté dans le rapport.

1. **Non-interpénétration** — recouvrement résiduel maximal sur toute la simulation, publié en
   mètres et rapporté au rayon des agents.
2. **Non-sortie du domaine** — distance maximale de violation des parois.
3. **Conservation** — le nombre d'agents est invariant ; chaque agent sorti est comptabilisé une
   et une seule fois.
4. **Sensibilité à Δt** — relance à Δt/2 puis Δt/4. Les diagrammes fondamentaux doivent se
   superposer dans les barres d'erreur. Écart quantifié.
5. **Sensibilité à N** — les conclusions doivent être stables quand le nombre d'agents augmente.
6. **Sensibilité à la graine** — dispersion inter-graines, pour distinguer un effet réel d'un
   artefact statistique.
7. **Cohérence dimensionnelle** — tableau de toutes les grandeurs avec leurs unités, et
   vérification des ordres de grandeur.
8. **Comparaison à un résultat connu** — confrontation au **diagramme fondamental de Weidmann**
   et au débit spécifique de goulot de la littérature (ordre de 1,2 à 1,4 pers·m⁻¹·s⁻¹). C'est
   le point de repère que les consignes citent explicitement pour une foule.

### 5.1 Choix de Δt

Critère : le déplacement par pas `|v|·Δt` doit rester petit devant le rayon `r`. Avec
`r ≈ 0,2 m` et `v_max ≈ 1,5 m·s⁻¹`, `Δt = 10⁻² s` donne 1,5 cm par pas, soit moins d'un dixième
de rayon. Valeur de départ, à confirmer par le test de sensibilité n°4.

---

## 6. Architecture logicielle

### 6.1 Flux de données

```
config YAML → Scénario → boucle de simulation → trajectoires .npz
                                                       ↓
                                             observables → figures/
```

**Décision structurante** : les trajectoires sont **persistées**, et les observables sont
calculés hors ligne. Conséquences : retracer une figure ou ajouter un observable ne nécessite
pas de relancer les simulations (déterminant sur un balayage de paramètres), et le module
`observables/` est testable sur des données synthétiques, sans dépendre du moteur.

### 6.2 Modules

| Module | Responsabilité | Dépend de |
|---|---|---|
| `core/` | état, schéma semi-implicite, graine RNG, paramètres | — |
| `geometry/` | domaine, parois, projection itérative, grille spatiale | `core` |
| `model/desire` | eikonal et Fast Marching, direction de guidage | `geometry` |
| `model/milieu` | accélération bornée par (`τ`, `a_max`) ; carte position vers (`τ`, `a_max`, `s`) à venir (C6) | `core`, puis `geometry` pour la carte |
| `model/crossing` | sites de franchissement à capacité unitaire | `geometry` |
| `model/contact` | contraintes d'exclusion entre agents | `geometry` |
| `observables/` | densité Voronoï, débit, diagramme fondamental | — |
| `scenarios/` | piscine, bancs d'essai | `model` |
| `io/` | config YAML, lecture et écriture des trajectoires | `core` |
| `viz/` | figures matplotlib, animations | `observables` |

Le moteur (`core` et `geometry`) ignore tout de la notion de foule : il intègre un système de
particules sous contraintes. Toute la sémantique « foule » vit dans `model/`.

### 6.3 Pile technique

Python 3.12, NumPy (vectorisation), SciPy (Voronoï), Matplotlib (figures), PyYAML (configs),
pytest (tests), ruff (lint et format).

Aucune bibliothèque de physique, de jeu ou de simulation de foule : le schéma d'intégration, les
contraintes et les conditions aux limites sont écrits par le groupe, conformément aux consignes.

---

## 7. Reproductibilité

| Exigence des consignes | Réponse dans le dépôt |
|---|---|
| Dépendances, commande de lancement, temps d'exécution typique | `README.md` |
| Paramètres de chaque figure du rapport | `experiments/manifeste.yaml` — table figure / config / graine |
| Graine fixée | `core/rng.py`, graine déclarée dans chaque config |
| Relance à l'identique | `docker compose run --rm viscocrowd make figures` |

---

## 8. Organisation du dépôt et méthodologie

### 8.1 Droits

| Membre | Compte | Rôle |
|---|---|---|
| Karrouchi Hamza | `CodeByHaamza` | admin |
| Lesueur Shaleena | `shalee-pnt` | write |
| Mongrandi Lenny | `lennymgrd` | write |

### 8.2 Branches

`main` protégée : pas de push direct, PR obligatoire, CI verte, historique linéaire (squash),
force-push et suppression bloqués, conversations de revue résolues avant fusion.

**L'approbation d'un pair n'est pas exigée techniquement**, et chacun peut fusionner sa propre
pull request. Le groupe travaillant en alternance, une approbation bloquante immobiliserait une
branche plusieurs jours quand les emplois du temps ne coïncident pas.

La relecture croisée reste la règle de travail (§ 8.5) : elle est simplement portée par la
discipline du groupe plutôt que par un verrou GitHub. Le garde-fou qui, lui, reste mécanique,
c'est la CI — et notamment les invariants physiques, qu'aucune PR ne peut contourner.

Préfixes : `feat/`, `fix/`, `exp/`, `docs/`, `chore/`.

### 8.3 Commits

Conventional Commits, messages en français : `type(portée): description à l'infinitif`.

### 8.4 Intégration continue

| Workflow | Contenu |
|---|---|
| `ci.yml` | ruff, pytest et couverture, **suite d'invariants physiques** |
| `report.yml` | compilation LaTeX, PDF en artefact |

Les invariants physiques (points 1 à 3 du § 5) tournent à chaque PR : une régression physique ne
peut pas être fusionnée.

### 8.5 Revue croisée

La revue par un pair n'est pas une formalité administrative. Les consignes imposent que *chaque
membre puisse expliquer et modifier n'importe quelle partie du travail* en soutenance : la revue
obligatoire est le mécanisme qui garantit cette lecture partagée.

---

## 9. Jalons

| # | Jalon |
|---|---|
| 0 | Socle du dépôt, droits, demi-page et cadrage enseignant |
| 1 | Moteur : semi-implicite et projection sur le domaine |
| 2 | Exclusion entre agents, projection itérative |
| 3 | Champ de guidage eikonal et milieux |
| 4 | Scénario piscine complet, franchissements |
| 5 | Campagnes E0 à E4, diagramme fondamental, validation chiffrée |
| 6 | Rapport, figures finales, transparents |

Le [planning daté](../../planning/README.md) centralise les cibles, les responsables et les
prérequis ; le [README](../../../README.md#état-davancement) résume l'avancement. Le statut
du sujet et la trace disponible figurent dans la [fiche de cadrage](../../validation-sujet.md#trace-de-validation).

### 9.1 Échéances imposées

- Rapport final et code : **mardi 5 janvier 2027, 23h59**, dépôt Moodle.
- Transparents : **lundi 18 janvier 2027, 18h00**.
- Soutenance : **mardi 19 janvier 2027**, 10 minutes de présentation et 10 minutes de questions.

Retard non justifié : 2 points de pénalité par jour entamé.

---

## 10. Hors périmètre (YAGNI)

Écartés explicitement, pour garder le projet tenable sur 13 semaines :

- Troisième dimension : le modèle reste 2D.
- Chocs élastiques ou partiellement élastiques : le choc mou suffit à la problématique.
- Modèle de forces sociales en parallèle : un seul cadre, assumé et défendable.
- Hétérogénéité comportementale fine (âge, groupes familiaux, altruisme) : seule la dispersion
  des rayons et des vitesses désirées est conservée.
- Pilotage interactif de la simulation : les animations scientifiques restent rendues hors ligne
  pour la soutenance. Un aperçu graphique de la piscine est ajouté le 12 octobre 2026 ; il reste
  limité à une maquette visuelle indépendante du moteur, sans agents ni calcul physique.

---

## 11. Conformité aux consignes

| Consigne | Traitement |
|---|---|
| Sujet validé avant implémentation | [Trace à compléter](../../validation-sujet.md#trace-de-validation) ; chronologie non vérifiable avec les informations disponibles |
| Rapport 15-20 p. : résumé, introduction, développement, conclusion, références | structure `report/sections/` |
| Rapport en LaTeX (bonus 1 point) | `report/` et CI de compilation |
| Validation chiffrée | § 5, et suite d'invariants en CI |
| Comparaison à un résultat connu | Weidmann et débit de goulot, § 5 point 8 |
| Figures légendées, axes nommés avec unités, paramètres indiqués | `viz/` et `experiments/manifeste.yaml` |
| Pas de capture d'écran en guise de graphique | figures matplotlib exclusivement |
| README : dépendances, commande, temps d'exécution | § 7 |
| Graine fixée | § 7 |
| Pas de bibliothèque spécialisée | § 6.3 |
| Section sur l'usage de l'IA générative | section dédiée du rapport et `docs/journal-decisions.md` |
| Tableau de répartition des tâches en annexe | tenu à jour en continu, alimenté par l'historique git |
| Pistes explorées non abouties | `docs/journal-decisions.md` |
