# Balayages E3/E4 de la piscine (M6)

Au point de référence (`experiments/piscine.yaml`), le carrelage mouillé ne change presque
rien à l'évacuation : rien de mesurable au facteur de panique 1 (#83), et +0,02 s sur t50
au facteur 1,5, la référence depuis le 6 novembre (journal des décisions). Deux raisons, relevées dans [#26](https://github.com/ViscoCrowd/ViscoCrowd-simulation/issues/26) :

- à 1,34 m/s, relancer ou freiner en ligne droite demande au plus `s/τ = 2,7 m/s²`, sous
  l'adhérence du mouillé (3,3 m/s²). L'adhérence ne limite rien tant que `s < a_max·τ =
  1,65 m/s` ; seuls les virages serrés, au-delà d'environ 76°, l'atteignent ;
- 17 m de sol sec séparent la bande mouillée de la porte : un agent a retrouvé son
  adhérence bien avant le goulot.

`viscocrowd balayer-piscine` cherche donc **où** le sol mouillé commence à compter, en faisant
varier un paramètre à la fois, les autres restant ceux du YAML (spec § 4) :

| Paramètre | Campagne | Unité | Ce qu'il change |
|---|---|---|---|
| `largeur_mouillee` | E3 | m | largeur de la bande mouillée ; à 20 m, la plage est mouillée jusqu'à la porte |
| `adherence_mouille` | E3 | m/s² | `a_max` du carrelage mouillé |
| `vitesse_mouille` | E3 | m/s | vitesse souhaitée sur le carrelage mouillé (#26) |
| `lambda_chute` | E3 | 1/s | taux de chute par perte d'adhérence ; **active le module de chutes**, voir ci-dessous |
| `lambda_domino` | E3 | 1/s | taux de chute par effet domino, près d'un corps au sol ; active le module (#130) |
| `lambda_bousculade` | E3 | 1/s | taux de chute par bousculade (0 l'éteint ; seul compte son produit avec `duree_bousculade`, #135) ; active le module (#130) |
| `facteur_rayon_terre` | E3 | – | rayon d'un corps au sol rapporté au rayon debout ; active le module (#130) |
| `facteur_vitesse` | E4 | – | niveau de panique : multiplie toutes les vitesses souhaitées |
| `largeur_porte` | E4 | m | largeur du goulot |
| `n_agents` | E4 | pers | nombre de baigneurs |
| `temps_espacement` | E4 | s | temps d'espacement T de la relation vitesse–espacement (Tordeux et al.) ; 0,35 s, étalonné sur E0 (#58), dans le YAML depuis le 10 novembre (#57). `temps_espacement: null` dans le YAML la désactive ; `--fixer` n'accepte pas `null` |
| `relaxation` | M9 | s | temps de relaxation τ, **commun** à l'eau, au mouillé et au sec (témoin compris) : vérifier que les conclusions tiennent quand τ varie |
| `dt` | M9 | s | pas de temps : vérifier que les écarts n'en dépendent pas (spec § 5) |
| `duree_rebord` | E4 | s | durée pour se hisser sur le rebord, à chaque site (4 s dans le YAML, hypothèse sans source) ; un rebord lent envoie aussi plus de nageurs aux échelles, puisque le guidage compte cette durée |
| `duree_echelle` | E4 | s | durée de montée d'une échelle, à chaque site (2 s dans le YAML, hypothèse sans source) |
| `adherence_eau` | M9 | m/s² | `a_max` dans l'eau : 0,34 g × un poids apparent supposé de moitié, soit 1,67 m/s² dans le YAML depuis #128 |

**Balayer un paramètre des chutes active le module.** `experiments/piscine.yaml` n'a pas de
section `chutes` : le balayage la crée, et toutes les autres valeurs du module (domino,
relevage, contournement) restent celles par défaut de `ParametresChutes`. Ces valeurs ne sont pas
calibrées : comme le précise [`modele-chutes.md`](modele-chutes.md), aucun chiffre obtenu
avec ce module ne peut servir de résultat avant sa calibration. L'enseignant a validé son
inclusion dans le rendu le 3 novembre (#19), pas ses valeurs. Le témoin sec garde les
**mêmes** chutes que le mouillé, si bien que Δ ne mesure que le sol.

Le nombre d'échelles n'est pas balayé : il faudrait d'abord choisir où placer les échelles
ajoutées, ce qui est un choix de scénario à faire en groupe.

**Durées de franchissement.** Comme pour les autres paramètres, le témoin sec reçoit la même
durée que le mouillé : Δ ne mesure toujours que le sol, et le témoin est recalculé à chaque
valeur. Sur une vraie évacuation de trois agents (graine 1, facteur 1,5), passer le rebord
de 1 s à 8 s retarde t100 de 21,6 s à 31,2 s (test `test_rebord_plus_lent_retarde_la_derniere_sortie`).

## Commande

```bash
viscocrowd balayer-piscine experiments/piscine.yaml \
  --parametre largeur_mouillee --valeurs 3 10 17 20 \
  --fixer facteur_vitesse=1.5 \
  --graines 1 2 3 4 5 6 7 8 9 10 \
  --sortie data/m6/largeur-mouillee.json
```

`--fixer NOM=VALEUR` change d'autres paramètres de la liste pour tout le balayage. Par
exemple, on peut faire varier la largeur mouillée à un facteur de panique de 1,5. Au-delà
d'un facteur de 2, il faut aussi `--fixer dt=0.005` : à `dt = 0,01 s`, un agent poussé par
ses voisins avance de plus de `r/5` en un pas, et la simulation s'arrête (mesuré le
2 novembre, facteur 2, graine 1, t = 16,35 s). Sans
`--graines`, la commande prend dix graines à partir de celle du YAML (spec § 4 : au moins
dix). Toutes les configurations sont construites avant la première simulation : une valeur
hors domaine est refusée tout de suite. Le bilan JSON n'écrase jamais un fichier existant,
et il est refusé sous `src/` ou `experiments/`, comme pour les campagnes.

### Sensibilité à τ (à lancer)

τ = 0,5 s vient de Helbing, Farkas et Vicsek (2000). Il n'a été mesuré ni dans l'eau ni sur
sol mouillé. Or l'adhérence ne limite un agent que si `|U − v| > a_max · τ` : un τ plus
court rend les agents plus vifs, donc le mouillé limite plus souvent. Il faut donc vérifier
que les conclusions tiennent quand τ varie. τ est changé **en même temps** sur les trois
sols et sur le témoin, pour que l'écart Δ reste un effet du sol seul.

Avant de lancer, appliquer les valeurs du moment dans `experiments/piscine.yaml`.
Au 6 novembre, il reste à passer `EAU.acceleration_max` de 1,6 à 1,67 m/s² (journal des
décisions).

Mêmes graines 1 à 10 que les balayages M6, une valeur par terminal pour paralléliser. Chaque commande enchaîne 20 évacuations, car le
témoin dépend de τ et est recalculé à chaque valeur :

```bash
viscocrowd balayer-piscine experiments/piscine.yaml --parametre relaxation --valeurs 0.3 --graines 1 2 3 4 5 6 7 8 9 10 --sortie data/m9/relaxation-0.3.json
viscocrowd balayer-piscine experiments/piscine.yaml --parametre relaxation --valeurs 0.5 --graines 1 2 3 4 5 6 7 8 9 10 --sortie data/m9/relaxation-0.5.json
viscocrowd balayer-piscine experiments/piscine.yaml --parametre relaxation --valeurs 1.0 --graines 1 2 3 4 5 6 7 8 9 10 --sortie data/m9/relaxation-1.0.json
```

τ doit rester supérieur ou égal à `dt` : une valeur plus petite est refusée avant tout calcul.

## Ce qui est mesuré

Pour chaque valeur et chaque graine, **deux** évacuations partent des mêmes positions :

- **mouillé** : la piscine telle que configurée ;
- **témoin** : la même piscine, sol entièrement sec (pas de bande mouillée, et le mouillé
  prend les paramètres du sec).

L'effet du sol mouillé est l'écart **Δ = mouillé − témoin**, graine par graine. Comparer
deux graines différentes mélangerait l'effet du sol et le hasard du placement de départ.

Chaque évacuation donne `t50`, `t90`, `t100` (instants où 50, 90 et 100 % des baigneurs sont
sortis, en s), le débit à la porte, en pers/(m·s), le nombre de baigneurs encore présents
à la fin de `duree`, et le nombre de chutes de chaque cause (glissade, domino, bousculade),
nul quand le module est désactivé. Le débit utilise le même estimateur que le goulot E0 (`debit_seyfried`,
ΔN/(Δt·b)), pour que les deux restent comparables.

Le tableau affiche, pour chaque valeur, `t100` du mouillé, la moyenne ± écart-type de chaque
Δ, les non-sortis (total sur les graines, mouillé/témoin), les chutes (moyenne par
évacuation, toutes causes, mouillé/témoin) et le nombre de graines où le mouillé est plus
lent (`Δ t100 > 0`). Le JSON garde toutes
les mesures brutes, graine par graine, avec la configuration et la provenance du code : tout
tableau ou figure peut en être recalculé sans relancer les simulations.

## Garde-fous

- **Aucune moyenne partielle.** Une évacuation inachevée à la fin de `duree` est un résultat
  (une porte qui se bouche en est un), pas une erreur : elle est conservée, avec `t100 = +∞`
  et un débit indéfini, et le balayage continue. Mais aucune moyenne ne la cache : dès
  qu'une graine n'a pas fini, la case affiche `incomplet k/n` au lieu d'une moyenne des
  autres graines. C'est le même principe que le « bouchage » du goulot E0. Une projection
  non convergée, elle, arrête le balayage : la trajectoire n'est pas un état physique.
- **Aucune simulation en double.** Le témoin ne dépend ni de la largeur mouillée ni de
  l'adhérence du mouillé : il est calculé une fois par graine. Un point où le mouillé équivaut
  au sec (bande nulle, ou mêmes paramètres que le sec) reprend son témoin, et le tableau
  l'indique par `(= temoin)`. Deux tests vérifient sur de vraies évacuations que ces
  raccourcis ne changent aucun bit.
- **Code figé.** Si le code ou l'environnement change pendant un balayage, il s'arrête : les
  résultats mélangeraient deux versions.

Un balayage de 4 valeurs sur 10 graines à 100 agents représente 40 à 80 évacuations. Une
évacuation seule prend environ 8 s ([performances](performances.md)). Lancés à 19 en
parallèle sur un i7-14700KF (28 fils), les balayages ci-dessous ont pris environ 23 s par
évacuation, et 15 à 40 min chacun.

## Premiers résultats (2 novembre 2026)

Commit `fc2d60d`, sans modification locale ; graines 1 à 10 ; 100 baigneurs ;
`experiments/piscine.yaml`, au facteur de panique 1,5 sauf pour le balayage de la panique.
Ces balayages sont faits **sans régulation vitesse–espacement** : le YAML n'avait pas encore
le champ `temps_espacement`. Pour les reproduire depuis le 10 novembre, il faut une copie du
YAML avec `temps_espacement: null`.
Les [bilans bruts](mesures/balayages-piscine-2026-11-02/) gardent chaque graine, la
configuration et la provenance (la porte de 0,8 m, très lente quand elle se bouche, a
été lancée graine par graine, un fichier par graine). Les valeurs sont des moyennes ± écart-type sur les
10 graines ; Δ = mouillé − témoin sec, en s ; « plus lent » compte les graines où
Δ t100 > 0.

**Niveau de panique** (`--fixer dt=0.005`) :

| Facteur | t100 mouillé (s) | Δ t50 (s) | Δ t90 (s) | Δ t100 (s) | Plus lent |
|---|---|---|---|---|---|
| 1 | 47,02 ± 0,96 | 0,000 ± 0,000 | 0,000 ± 0,001 | 0,000 ± 0,001 | 2/10 |
| 1,25 | 41,80 ± 2,46 | 0,000 ± 0,001 | −0,17 ± 0,45 | −0,05 ± 0,17 | 8/10 |
| 1,5 | 40,94 ± 3,18 | 0,020 ± 0,012 | 0,12 ± 0,19 | 0,31 ± 1,13 | 7/10 |
| 2 | 38,95 ± 3,45 | 0,044 ± 0,086 | −0,08 ± 0,61 | 0,49 ± 0,71 | 8/10 |
| 2,5 | 40,40 ± 3,17 | 0,095 ± 0,104 | 0,16 ± 0,30 | 0,07 ± 0,87 | 6/10 |

**Adhérence du mouillé** (le sec reste à 5,9 m/s²) :

| a_max mouillé (m/s²) | Δ t50 (s) | Δ t90 (s) | Δ t100 (s) | Plus lent |
|---|---|---|---|---|
| 1 | 0,38 ± 0,26 | 0,33 ± 0,37 | −0,48 ± 1,99 | 4/10 |
| 2 | 0,05 ± 0,12 | 0,36 ± 0,89 | −0,80 ± 1,33 | 4/10 |
| 3,3 (référence) | 0,020 ± 0,013 | −0,10 ± 0,22 | −0,03 ± 0,96 | 7/10 |
| 5,9 | = témoin | | | |

**Largeur mouillée** (0, 3, 10, 20 m). À 3 et 10 m, les résultats sont identiques **au bit
près**. À 20 m, la plage est mouillée jusqu'à la porte : deux graines diffèrent d'au plus
1,4·10⁻⁵ s sur t50, les autres mesures sont identiques.

**Pas de temps** (facteur 1,5) :

| dt (s) | t100 mouillé (s) | Δ t50 (s) | Δ t100 (s) |
|---|---|---|---|
| 0,01 | 41,20 ± 3,06 | 0,020 ± 0,013 | −0,03 ± 0,96 |
| 0,005 | 40,94 ± 3,18 | 0,020 ± 0,012 | 0,31 ± 1,13 |
| 0,0025 | 41,40 ± 3,30 | −0,001 ± 0,147 | 0,12 ± 1,20 |

**Porte et population** : voir « Bouchage » ci-dessous. Sans bouchage, l'effet du mouillé
reste du même ordre (porte de 1,6 m : Δ t100 = −0,28 ± 0,93 s ; 2,4 m : −0,05 ± 0,92 s ;
50 baigneurs : 0,018 ± 0,023 s ; 150 baigneurs : −1,14 ± 1,16 s).

### Lecture

1. **Le mouillé n'agit que là où l'on change de vitesse ou de direction.** Mouiller la plage
   sur 10 m au lieu de 3 ne change aucun bit : aucun baigneur n'atteint la limite
   d'adhérence entre 3 et 10 m du bassin. Les relances et les virages serrés ont lieu en
   sortant de l'eau et au coin du bassin ; ensuite, les baigneurs vont droit vers la porte.
2. **Un seul effet net : une adhérence très faible retarde la première moitié.** À
   1 m/s², t50 recule de 0,38 s, sur les 10 graines (de 0,06 à 1,0 s) : relancer depuis
   l'arrêt en sortant de l'eau prend plus de temps. C'est 1,5 % de t50 (25,9 s).
3. **Sur la fin de l'évacuation, l'effet se perd dans le hasard.** Δ t100 change de signe
   d'une graine à l'autre, avec un écart-type de 1 à 2 s. Un léger décalage à la sortie de
   l'eau change l'ordre d'arrivée aux échelles et au rebord, et donc le dernier sorti.
4. **Ces écarts ne sont pas plus grands que l'effet du pas de temps.** Diviser dt par 4 déplace
   t100 de 0,5 s et Δ t100 de 0,3 s. Seul le retard de t50 à faible adhérence dépasse
   nettement ce seuil.
5. **La panique ne raccourcit plus l'évacuation au-delà d'un facteur 2.** t100 passe de 47 s
   à 39 s entre les facteurs 1 et 2, puis remonte à 40 s. Ce qui fixe le rythme, c'est la
   sortie de l'eau (capacité et durée des échelles et du rebord), pas la vitesse sur la plage.
   La porte n'est jamais saturée.

### Bouchage : un défaut de la géométrie, pas un résultat

| Porte (m) | Population | Graines bouchées, mouillé | Graines bouchées, témoin |
|---|---|---|---|
| 0,8 | 100 | 8 sur 10 (10 à 65 baigneurs restés) | 7 sur 10 (23 à 61 restés) |
| 1,0 | 100 | 2 sur 10 (23 et 27 baigneurs restés) | 0 sur 10 |
| 1,2 | 200 | 1 sur 10 (13 restés) | 1 sur 10 (14 restés) |

Un diagnostic sur la porte de 0,8 m (graine 2) trouve 65 baigneurs sur 100 figés devant la
porte, en réseau serré, à vitesse nulle, sans aucun déplacement en 10 s. Ce sont des arches
statiques. La porte de la piscine est construite comme la première géométrie du goulot E0 :
l'union de la plage et du couloir de la porte, chacun réduit d'un rayon, avec des **coins
vifs** aux montants. Dans E0, cette construction bouchait la foule à 0,8 et 1,0 m sur
toutes les graines, et arrondir les coins a supprimé tout bouchage (journal, entrée E0).
Tant que la porte de la piscine n'est pas arrondie, les balayages de largeur de porte et de
population ne mesurent pas un comportement de foule. En particulier, la différence entre
mouillé (2 graines bouchées) et sec (aucune) à 1,0 m ne peut pas être interprétée.

## Régulation vitesse–espacement (10 novembre 2026)

Commit `af07e19`, sans modification locale, sous macOS arm64 ; `experiments/piscine.yaml`
(facteur 1,5, porte de 1,2 m, 100 baigneurs) ; graines 1 à 10, les mêmes que E1/E2, donc
appariées avec la ligne « sans ». 60 évacuations en 5 min 52 s, sans parallélisme.
[Bilan brut](mesures/balayages-piscine-2026-11-10/temps-espacement.json).

```bash
viscocrowd balayer-piscine experiments/piscine.yaml \
  --parametre temps_espacement --valeurs 0.25 0.35 0.5 \
  --graines 1 2 3 4 5 6 7 8 9 10
```

| T (s) | t50 mouillé (s) | t100 mouillé (s) | Débit mouillé (pers/(m·s)) | Δ t50 (s) | Δ t50 > 0 | Δ t100 (s) | Δ t100 > 0 | Non sortis |
|---|---|---|---|---|---|---|---|---|
| sans (`temps_espacement: null`, E2 du 6 novembre) | 25,90 ± 0,49 | 41,20 ± 3,06 | 3,20 ± 0,45 | 0,020 ± 0,013 | 10/10 | −0,03 ± 0,96 | 7/10 | 0 |
| 0,25 | 29,48 ± 0,72 | 47,44 ± 2,31 | 2,56 ± 0,17 | 0,017 ± 0,012 | 10/10 | 0,09 ± 0,82 | 9/10 | 0 |
| 0,35 | 31,42 ± 0,53 | 51,83 ± 1,68 | 2,25 ± 0,10 | 0,014 ± 0,023 | 8/10 | −0,12 ± 0,42 | 5/10 | 0 |
| 0,5 | 34,43 ± 0,42 | 57,77 ± 1,78 | 1,94 ± 0,07 | 0,014 ± 0,006 | 10/10 | 0,04 ± 0,07 | 10/10 | 0 |

À T = 0,35 s, le balayage retrouve exactement E2 refait avec `comparer-piscine`
(t100 = 51,83 ± 1,68 s) : les deux outils se recoupent.

Ce qu'on en retient :

1. **Aucun bouchage**, pour aucune valeur de T. Freiner derrière un meneur ne crée pas
   d'arche à la porte de 1,2 m, malgré ses coins vifs (#85).
2. **La porte ralentit nettement, mais reste au-dessus des références.** À T = 0,35 s, la
   valeur étalonnée sur E0, le débit passe de 3,20 à 2,25 pers/(m·s), à graines égales, et
   t100 s'allonge d'environ 10 s. Il reste au-dessus de E0 régulé à 1,2 m (1,84 au facteur 1)
   et de la mesure de Seyfried (1,97). Une partie de l'écart vient du facteur de panique :
   E0 au facteur 1,5 donne 2,04 ± 0,05 (10 graines, T = 0,35 s, mesure du 10 novembre). Le
   reste, de 2,04 à 2,25, n'est pas expliqué. Pistes non mesurées : la porte de la piscine,
   profonde de 1 m et à coins vifs, n'a pas la géométrie du goulot E0, et la foule y arrive
   par la plage au lieu d'attendre devant.
3. **L'écart-type de t100 diminue** (de 3,06 s à 1,7 s à T = 0,35 s) : le dernier sorti dépend
   moins de l'ordre d'arrivée, puisque la file à la porte s'écoule à un rythme plus régulier.
4. **L'effet du mouillé ne change pas d'ordre de grandeur.** Δ t50 reste de l'ordre du
   centième de seconde, positif sur 8 à 10 graines sur 10. La régulation ne crée pas de
   bouchon devant la porte, donc pas de freinage supplémentaire sur le mouillé, qui est de
   toute façon à 17 m de la porte.

Le 10 novembre, la régulation est activée à T = 0,35 s dans la configuration de référence
(#57, journal). Les balayages du 2 novembre, faits sans elle, restent valables pour ce
qu'ils comparent (mouillé contre sec à réglage égal), mais leurs valeurs absolues ne sont
plus celles de la référence.

## Porte arrondie et a_max de l'eau à 1,67 (13 novembre 2026)

Les montants de la porte sont arrondis comme ceux du goulot E0 (#85, PR #125), et l'eau
passe à `a_max = 1,67 m/s²`, la valeur prévue à la prochaine relance (C6, journal du
6 novembre). Configuration de référence pour le reste : facteur 1,5, T = 0,35 s. Graines 1
à 10, une graine par processus (mêmes séries qu'en un seul appel). Code du commit `5dc556a`
et `piscine.yaml` de `773d6f3` : c'est ce que signale `modifications_locales: true` dans
les bilans de [`mesures/porte-arrondie-2026-11-13/`](mesures/porte-arrondie-2026-11-13/).

```bash
viscocrowd balayer-piscine experiments/piscine.yaml --parametre largeur_porte --valeurs 0.8 1.0 1.2 1.6 --graines 1 2 3 4 5 6 7 8 9 10
viscocrowd balayer-piscine experiments/piscine.yaml --parametre n_agents --valeurs 50 100 150 200 --graines 1 2 3 4 5 6 7 8 9 10
```

**Aucune évacuation incomplète** sur les 160 simulations (mouillé et témoin). Avant la
correction et sans régulation, les mêmes commandes bouchaient 8 graines sur 10 à 0,8 m
(section « Bouchage » ci-dessus, reproduite à l'identique le 13 novembre).

Largeur de porte (témoin sec ; flux = J_s × b, en sorties par seconde) :

| b (m) | t50 (s) | t90 (s) | t100 (s) | J_s (pers/(m·s)) | Flux (pers/s) | Δ t100 mouillé − sec (s) |
|---|---|---|---|---|---|---|
| 0,8 | 41,96 ± 0,36 | 64,25 ± 0,50 | 70,52 ± 0,75 | 2,24 ± 0,01 | 1,79 ± 0,01 | 0,06 ± 0,52 |
| 1,0 | 31,95 ± 0,77 | 45,74 ± 0,85 | 51,35 ± 1,79 | 2,73 ± 0,11 | 2,73 ± 0,11 | 0,00 ± 0,12 |
| 1,2 | 31,44 ± 0,51 | 45,42 ± 0,66 | 51,36 ± 1,77 | 2,28 ± 0,09 | 2,73 ± 0,11 | −0,08 ± 0,17 |
| 1,6 | 31,30 ± 0,54 | 45,43 ± 0,64 | 51,23 ± 1,77 | 1,71 ± 0,07 | 2,74 ± 0,11 | −0,09 ± 0,16 |

Population (porte de 1,2 m, témoin sec ; Δ t50 et nombre de graines où il est positif) :

| N | t50 (s) | t90 (s) | t100 (s) | Flux (pers/s) | Δ t50 mouillé − sec (s) |
|---|---|---|---|---|---|
| 50 | 24,84 ± 0,77 | 31,68 ± 0,83 | 34,21 ± 1,30 | 2,60 ± 0,17 | 0,012 ± 0,004, 10/10 |
| 100 | 31,44 ± 0,51 | 45,42 ± 0,66 | 51,36 ± 1,77 | 2,73 ± 0,11 | −0,01 ± 0,07, 7/10 |
| 150 | 39,43 ± 0,25 | 60,16 ± 0,95 | 67,89 ± 2,72 | 2,82 ± 0,13 | 0,05 ± 0,15, 8/10 |
| 200 | 47,61 ± 0,44 | 73,99 ± 0,56 | 84,73 ± 1,61 | 2,85 ± 0,06 | 0,07 ± 0,24, 7/10 |

La ligne N = 200 est celle de la relance du 14 novembre, avec la règle de déblocage active
(#131) : elle se déclenche sur quelques évacuations régulées à 200 baigneurs et y avance la
dernière sortie (t100 de 84,78 ± 1,52 à 84,73 ± 1,61 s, Δ t50 positif sur 7 graines au lieu
de 8). Les lignes 50 à 150 sont inchangées aux arrondis du tableau. Commit `7a96db1`, sans
modification locale, macOS arm64 ; bilans dans
[`mesures/deblocage-2026-11-14/`](mesures/deblocage-2026-11-14/), avec un contrôle sans la règle
sur la même machine (`sans-regle/`), qui sépare deux causes d'écart :

- **la règle** ne change aucune évacuation du balayage de largeur de porte (`tab:e4-porte` reste
  valable) et 10 des 80 évacuations du balayage de population : au plus 0,006 s sur t100, sauf
  deux à N = 200 (−0,49 s, sec, graine 4 ; −0,76 s, mouillé, graine 8) ;
- **la plateforme** : sans la règle, macOS et Windows (bilans du 13 novembre) diffèrent sur 16
  des 160 évacuations, de 0,002 s au plus sur t100 pour la population et de 0,024 s pour la
  porte. Les résultats ne sont donc pas identiques au bit près d'une machine à l'autre ; les
  tableaux, arrondis au centième, n'en sont pas affectés.

Ce qu'on en retient :

1. **La porte ne limite l'évacuation que sous un mètre.** Dès 1,0 m, t100 ne bouge plus et
   le flux de sorties reste de 2,73 pers/s : c'est l'extraction de l'eau qui fixe le rythme.
   À 0,8 m, le flux tombe à 1,79 ± 0,01 pers/s, presque sans dispersion : la porte est
   saturée, et t100 s'allonge de 19 s.
2. **J_s se lit avec prudence.** Tant que la porte n'est pas saturée, il vaut le flux imposé
   en amont divisé par b : il baisse quand la porte s'élargit, sans rien dire de sa capacité.
3. **La durée croît linéairement avec la population** : 16,5 à 17,2 s de plus par tranche de
   cinquante baigneurs, avec un flux de sorties qui ne passe que de 2,60 à 2,85 pers/s.
4. **Le mouillé reste sans effet mesurable**, même devant une porte saturée (0,8 m :
   Δ t100 = 0,06 ± 0,52 s). Il n'est systématique qu'à cinquante baigneurs (Δ t50 de 0,007 à
   0,019 s sur les dix graines), quand peu d'interactions couvrent la relance écrêtée.

E1/E2 refaits sur la même configuration (`comparer-piscine`, graines 1 à 10) : t100 sec =
51,36 ± 1,77 s, mouillé = 51,28 ± 1,87 s, J_s = 2,28 ± 0,09 pers/(m·s) ; Δ t50 = −0,01 ± 0,07 s,
médiane +0,014 s, positif sur 7 graines sur 10, la graine 5 seule s'écartant de −0,22 s.
Le rapport (§ 6.2, 6.4 et 6.5) reprend ces chiffres.

## Sensibilité au pas de temps sur la référence actuelle (M9, 14 novembre 2026)

Le balayage de Δt du 2 novembre avait été fait sans régulation, avec l'ancienne porte. Refait
sur la référence actuelle (régulation à T = 0,35 s, porte arrondie, a_max de l'eau à 1,67) :
commit `3d6d43a`, sans modification locale, macOS arm64, graines 1 à 10, une valeur par
processus. Bilans dans [`mesures/sensibilite-dt-2026-11-14/`](mesures/sensibilite-dt-2026-11-14/).

| Δt (s) | t100 mouillé (s) | Δ t50 mouillé − sec (s) | Δ t100 (s) | Temps de calcul |
|---|---|---|---|---|
| 0,01 | 51,28 ± 1,87 | −0,014 ± 0,074 | −0,08 ± 0,17 | 173 s |
| 0,005 | 51,27 ± 1,86 | −0,025 ± 0,099 | −0,03 ± 0,20 | 300 s |
| 0,0025 | 51,29 ± 1,86 | −0,024 ± 0,102 | −0,03 ± 0,19 | 478 s |

Écart apparié au pas de référence, graine par graine, comparé à l'erreur standard entre
graines (critère 2 de `criteres-acceptation.md`) :

| Grandeur | Δt/2 − Δt | Δt/4 − Δt | Erreur standard entre graines |
|---|---|---|---|
| t50 | +0,001 ± 0,049 s | +0,001 ± 0,059 s | 0,165 s |
| t90 | −0,024 ± 0,103 s | −0,002 ± 0,108 s | 0,240 s |
| t100 | −0,012 ± 0,169 s | +0,007 ± 0,169 s | 0,592 s |
| J_s | +0,001 ± 0,010 | −0,000 ± 0,010 | 0,032 pers/(m·s) |

La problématique porte sur les écarts Δ mouillé − sec. Pour un Δ, l'erreur standard qui
compte est celle de Δ lui-même (écart-type des Δ par graine / √10), bien plus petite que
celle des grandeurs brutes, puisque l'appariement retire la variabilité commune :

| Écart mouillé − sec | Δt/2 − Δt | Δt/4 − Δt | Erreur standard de Δ | Rapport à Δt/2 |
|---|---|---|---|---|
| Δ t50 | −0,011 ± 0,029 s | −0,010 ± 0,041 s | 0,023 s | 0,47 |
| Δ t90 | −0,016 ± 0,050 s | +0,021 ± 0,098 s | 0,046 s | 0,34 |
| Δ t100 | +0,048 ± 0,144 s | +0,048 ± 0,097 s | 0,053 s | 0,91 |
| Δ J_s | −0,003 ± 0,009 | −0,003 ± 0,006 | 0,0037 pers/(m·s) | 0,80 |

**Le pas de 0,01 s suffit, mais de peu pour les écarts.** Sur les grandeurs brutes, les écarts
moyens restent au moins 10 fois sous l'erreur standard entre graines (t90 à Δt/2), et plus de
100 fois pour t50. Sur les écarts Δ, ils restent sous l'erreur standard de Δ, mais à un
rapport de 0,3 à 0,9 : à la référence, l'erreur numérique sur Δ t100 est du même ordre que
son incertitude statistique. L'effet du mouillé y est donc plus petit que la résolution
numérique et statistique : on peut seulement le borner à quelques centièmes de seconde sur
t50 (−0,014 ± 0,053 s, intervalle de confiance à 95 % sur 10 graines), pas dire qu'il est
nul. Ce contrôle ne couvre que la référence ; les configurations à effet (#137) sont à
vérifier de la même façon avant d'être publiées.

## Sensibilité à τ et à la vitesse sur le mouillé (14 novembre 2026)

Commit `3d6d43a` (empreinte des sources `d1387660…`), sans modification locale, macOS arm64 ;
`experiments/piscine.yaml` de
référence (régulation à T = 0,35 s, porte arrondie, a_max de l'eau à 1,67) ; graines 1 à 10 ;
une valeur par processus. Le balayage de τ change τ sur les trois sols **et** sur le témoin ;
celui de la vitesse sur le mouillé ne touche que le mouillé. Bilans dans
[`mesures/sensibilite-2026-11-14/`](mesures/sensibilite-2026-11-14/).

```bash
viscocrowd balayer-piscine experiments/piscine.yaml --parametre relaxation --valeurs 0.3 \
  --graines 1 2 3 4 5 6 7 8 9 10 --sortie relaxation-0.3.json
viscocrowd balayer-piscine experiments/piscine.yaml --parametre vitesse_mouille --valeurs 0.7 \
  --graines 1 2 3 4 5 6 7 8 9 10 --sortie vitesse-mouille-0.7.json
```

| Paramètre | t100 mouillé (s) | Δ t50 (s) | Δ t50 > 0 | Δ t50 / t50 | Δ t100 (s) |
|---|---|---|---|---|---|
| τ = 0,3 s | 47,67 ± 1,56 | 0,081 ± 0,028 | 10/10 | 0,27 % | 0,20 ± 0,35 |
| τ = 0,5 s (référence, E2 de #128) | 51,28 ± 1,87 | −0,01 ± 0,07 | 7/10 | — | — |
| τ = 0,8 s | 56,60 ± 3,17 | 0,000 ± 0,000 | 2/10 | 0 % | 0,01 ± 0,03 |
| s mouillé = 1,0 m/s | 51,31 ± 1,41 | 0,73 ± 0,51 | 9/10 | 2,3 % | −0,05 ± 1,02 |
| s mouillé = 0,7 m/s | 51,70 ± 1,36 | 1,49 ± 0,76 | 10/10 | 4,5 % | 0,34 ± 1,13 |

Ce qu'on en retient, avec les critères proposés dans `criteres-acceptation.md` :

1. **Un τ plus court renforce l'effet inertiel, sans le rendre pertinent.** À τ = 0,3 s, une
   relance demande |U − v| / τ ≈ 6,7 m/s², au-delà même de l'adhérence du sec : le mouillé
   écrête plus souvent, et Δ t50 est positif sur les 10 graines. Il reste de 0,08 s, soit
   0,27 % de t50. À τ = 0,8 s, la relance demande 2,5 m/s², sous l'adhérence du mouillé :
   aucun effet. L'effet inertiel du modèle dépend donc de τ, qui n'a pas de source pour le
   mouillé, mais reste petit sur toute la plage.
2. **Le seul effet pertinent est la marche plus lente sur le mouillé.** Si l'on marche à
   1,0 ou 0,7 m/s sur le carrelage mouillé (au lieu de 1,34), la première moitié sort
   0,7 à 1,5 s plus tard (2,3 à 4,5 % de t50, 9 et 10 graines sur 10). Ce n'est pas un effet
   d'inertie, mais un effet de prudence, que le modèle impose par hypothèse. Il se prédit à
   la main : traverser la bande de ℓ = 3 m à κ s au lieu de κ × 1,34 m/s (κ = 1,5, facteur de
   panique) coûte ℓ (1/(κ s) − 1/(κ × 1,34)), soit **1,36 s** à s = 0,7 m/s (1,49 s mesurés)
   et **0,51 s** à s = 1,0 m/s (0,73 s mesurés). Le reste vient des baigneurs sortis par le
   haut et le bas du bassin, qui longent la bande sur plus de 3 m, et de la relance. L'effet
   est cinématique, non inertiel.
3. **Sur la fin de l'évacuation, l'effet se dilue.** Δ t100 change de signe d'une graine à
   l'autre, avec un écart-type de 1 s : la porte et l'extraction de l'eau imposent le rythme.

**Niveau de panique, avec la régulation.** Le balayage du 2 novembre avait été fait sans
régulation. Refait le 14 novembre sur la même référence, depuis le commit de branche
`29fbca7`, qui ne change que de la documentation : les bilans portent l'empreinte des
sources `d1387660…`, la même que `3d6d43a`. C'est elle qui reste vérifiable une fois la
branche supprimée.

| Facteur | t100 mouillé (s) | J_s porte (pers/(m·s)) | Δ t50 (s) | Δ t50 > 0 |
|---|---|---|---|---|
| 1 | 62,16 ± 1,33 | 1,98 | 0,000 ± 0,000 | 3/10 |
| 1,25 | 55,83 ± 1,48 | 2,14 | 0,000 ± 0,001 | 6/10 |
| 1,5 (référence, E2 de #128) | 51,28 ± 1,87 | 2,28 | −0,01 ± 0,07 | 7/10 |
| 2 | 47,09 ± 2,58 | 2,39 | 0,095 ± 0,085 | 9/10 |

4. **Avec la régulation, la panique accélère toujours l'évacuation**, jusqu'au facteur 2 :
   pas d'effet *faster-is-slower* dans cette plage, la porte de 1,2 m n'étant pas saturée.
5. **L'effet inertiel du mouillé grandit avec la vitesse** : nul jusqu'au facteur 1,25 (une
   relance demande alors au plus 3,4 m/s², à peine plus que l'adhérence du mouillé), il atteint
   0,1 s au facteur 2. Il reste sous le seuil de pertinence de 1 %.

## Plage mouillée jusqu'à une porte saturée (14 novembre 2026)

Le test que les sections précédentes réclamaient : mettre le sol glissant au contact de la
file, devant une porte saturée. Commit `3d6d43a`, sans modification locale, macOS arm64 ;
`experiments/piscine.yaml` de référence ; porte de 0,8 m (saturée, #128) ; graines 1 à 10.
Bilans dans [`mesures/mouille-porte-saturee-2026-11-14/`](mesures/mouille-porte-saturee-2026-11-14/).

```bash
viscocrowd balayer-piscine experiments/piscine.yaml --parametre largeur_mouillee --valeurs 3 20 \
  --fixer largeur_porte=0.8 --graines 1 2 3 4 5 6 7 8 9 10
viscocrowd balayer-piscine experiments/piscine.yaml --parametre adherence_mouille --valeurs 1 2 3.3 \
  --fixer largeur_porte=0.8 largeur_mouillee=20 --graines 1 2 3 4 5 6 7 8 9 10
```

| Configuration, porte de 0,8 m | t100 mouillé (s) | J_s mouillé | Δ t50 (s) | Δ t100 (s) | Δ t100 > 0 |
|---|---|---|---|---|---|
| Bande de 3 m, a_max 3,3 | 70,57 ± 0,90 | — | 0,02 ± 0,22 | 0,06 ± 0,52 | 5/10 |
| Mouillé jusqu'à la porte, a_max 3,3 | 70,60 ± 0,83 | 2,24 ± 0,03 | 0,05 ± 0,19 | 0,09 ± 0,41 | 6/10 |
| Mouillé jusqu'à la porte, a_max 2 | 72,99 ± 0,65 | 2,15 ± 0,01 | **0,92 ± 0,45** | **2,47 ± 0,51** | **10/10** |
| Mouillé jusqu'à la porte, a_max 1 | 84,46 ± 1,18 | 1,81 ± 0,03 | **6,53 ± 0,87** | **13,95 ± 1,53** | **10/10** |

Le témoin sec écoule 2,24 pers/(m·s) dans tous les cas.

1. **Mouiller jusqu'à la porte ne suffit pas.** À l'adhérence de référence (0,34 g), l'écart
   reste de quelques centièmes de seconde, sans signe dominant.
2. **Avec une adhérence plus faible, l'inertie fait perdre du débit à la porte saturée.** À
   2 m/s² (0,2 g), la porte perd 4 % de son débit et t100 recule de 2,5 s, sur les 10 graines.
   À 1 m/s² (0,1 g), elle perd 19 % et l'évacuation s'allonge de 14 s (20 %). C'est
   ce qu'annonce l'hypothèse inertielle de la problématique. Dans le modèle, a_max borne la
   norme de (U − v)/τ : freinage, relance et virages sont limités de la même façon. Mais un
   baigneur qui freine mal ne perd rien, puisque la projection l'arrête contre celui qui le
   précède. Ce qui coûte du débit, c'est la **relance** : repartir de l'arrêt demande
   U/τ ≈ 4 m/s², que le sec fournit ; à 1 m/s², retrouver 1 m/s prend 1 s au lieu de 0,34 s,
   et 1,5 m/s prend 1,5 s au lieu de 0,69 s. Interprétation, non mesurée : dans le
   va-et-vient de la file, chaque baigneur repart plus lentement, et la porte saturée écoule
   moins de monde. C'est le mécanisme de relance écrêtée du rapport (§ 6, `sec:e2`).
3. **Comparé à la même adhérence loin de la porte** (bande de 3 m, porte de 1,2 m,
   2 novembre, sans régulation) : à 1 m/s², Δ t50 ne valait que 0,38 s. C'est la proximité de la file qui
   donne de l'ampleur à l'effet.

Limite : 0,2 g et 0,1 g sont bien sous le seuil de glissance de Kendzior (0,34 g) ; ce sont des
sols très glissants (savon, produit d'entretien), pas un carrelage mouillé ordinaire. La
conclusion est donc : **dans ce modèle, le sol mouillé ne dégrade l'évacuation que s'il est très
glissant et qu'il touche la file d'une porte saturée.**

### Confirmation sur les graines 11 à 20 (18 novembre 2026)

Selon `criteres-acceptation.md` (§ 3), un effet trouvé dans un balayage reste exploratoire
tant qu'il n'est pas confirmé sur dix nouvelles graines, fixées avant la relance. Critère
écrit avant le calcul : Δt100 > 0 sur au moins 9 graines sur 10 à 1 et à 2 m/s², et moyenne
supérieure à l'effet du pas de temps (#138, #140 : moins d'une erreur standard de Δ).

Commit `0499a12`, sans modification locale, Windows ; bilan graine par graine et sortie :
[`mesures/confirmation-inertie-2026-11-18/`](mesures/confirmation-inertie-2026-11-18/).

```bash
viscocrowd balayer-piscine experiments/piscine.yaml --parametre adherence_mouille --valeurs 1 2 3.3 \
  --fixer largeur_porte=0.8 largeur_mouillee=20 --graines 11 12 13 14 15 16 17 18 19 20 \
  --sortie docs/mesures/confirmation-inertie-2026-11-18/adherence.json
```

| a_max mouillé (m/s²) | t100 mouillé (s) | J_s mouillé | Δ t50 (s) | Δ t100 (s) | Δ t100 > 0 | Graines 1 à 10 (#137) |
|---|---|---|---|---|---|---|
| 3,3 (référence) | 70,50 ± 0,82 | 2,24 ± 0,03 | −0,06 ± 0,24 | −0,33 ± 0,80 | 2/10 | 0,09 ± 0,41, 6/10 |
| 2 | 73,21 ± 0,72 | 2,14 ± 0,02 | **1,00 ± 0,66** | **2,38 ± 1,12** | **10/10** | 2,47 ± 0,51, 10/10 |
| 1 | 84,31 ± 1,27 | 1,81 ± 0,03 | **6,14 ± 0,91** | **13,48 ± 1,65** | **10/10** | 13,95 ± 1,53, 10/10 |

Le témoin sec écoule 2,23 ± 0,05 pers/(m·s) ; t100 = 70,83 s en moyenne. Aucune évacuation
incomplète, aucun bouchage. Calcul : 9 min pour les 60 évacuations.

**L'effet inertiel est confirmé.** À 2 et à 1 m/s², Δt100 est positif sur les dix nouvelles
graines (de +0,45 à +3,8 s, puis de +11,5 à +15,8 s), et les moyennes retrouvent celles des
graines 1 à 10 à moins d'une demi-seconde. À l'adhérence de référence, il n'y a toujours rien
(2 graines positives sur 10). La conclusion ci-dessus passe d'« exploratoire » à « confirmée
sur vingt graines », avec la même limite : 0,2 et 0,1 g sont des sols très glissants.

## Témoin : la même adhérence loin de la file (14 novembre 2026)

La section précédente change deux choses à la fois : l'adhérence et l'étendue du mouillé. Pour
attribuer l'effet à la file, il faut la même adhérence faible **loin** de la porte, avec la même
porte saturée et la même régulation. La comparaison du 2 novembre (bande de 3 m, 1 m/s²) ne
convient pas : porte de 1,2 m, sans régulation, code antérieur. Même configuration que la
section précédente, bande de 3 m de la référence. Commit `29fbca7` (empreinte des sources
`d1387660…`, identique à `3d6d43a`), sans modification locale, Windows 11, Python 3.12 ;
graines 1 à 10. Bilans dans
[`mesures/temoin-inertie-2026-11-14/`](mesures/temoin-inertie-2026-11-14/).

```bash
viscocrowd balayer-piscine experiments/piscine.yaml --parametre adherence_mouille --valeurs 1 2 \
  --fixer largeur_porte=0.8 --graines 1 2 3 4 5 6 7 8 9 10
viscocrowd balayer-piscine experiments/piscine.yaml --parametre dt --valeurs 0.005 \
  --fixer largeur_porte=0.8 largeur_mouillee=20 adherence_mouille=1 --graines 1 2 3 4 5 6 7 8 9 10
```

| Porte de 0,8 m, a_max mouillé | Bande de 3 m : Δ t100 (s) | Δ J_s | Δ t100 > 0 | Mouillé jusqu'à la porte : Δ t100 (s) | Δ J_s |
|---|---|---|---|---|---|
| 1 m/s² | 0,57 ± 0,56 | −0,000 ± 0,022 | 9/10 | 13,95 ± 1,53 | −0,433 ± 0,044 |
| 2 m/s² | 0,26 ± 0,36 | −0,005 ± 0,014 | 8/10 | 2,47 ± 0,51 | −0,090 ± 0,020 |

(Δ J_s en pers/(m·s), écart apparié mouillé − sec ; colonnes de droite : section précédente.)

1. **Loin de la file, la porte saturée ne perd rien.** À 1 m/s² sur la seule bande de 3 m, son
   débit est inchangé à 10⁻³ près, et la dernière sortie ne recule que de 0,6 s : les baigneurs
   quittent la bande un peu plus tard, puis la porte les écoule au même rythme.
2. **L'effet de la section précédente vient donc de la file sur sol glissant.** À la même
   adhérence, la porte ne perd du débit que lorsque le mouillé l'atteint, et Δ t100 est 24 fois
   plus grand (13,95 s contre 0,57 s). Une porte saturée écoule au rythme de la file qui la
   presse : c'est cette file, sur sol glissant, qui passe moins vite.
3. **Ce que le témoin ne sépare pas.** Avec `largeur_mouillee=20`, toute la plage côté porte
   est glissante, pas seulement la file. Le point 2 repose sur la saturation : la bande de 3 m
   retarde les arrivées sans changer le débit de la porte, donc ce débit dépend de ce qui se
   passe devant elle. Un mouillé limité aux abords de la porte demanderait une autre géométrie
   de la bande, que le scénario ne permet pas aujourd'hui.

**Pas de temps.** Même configuration qu'à la ligne 1 m/s² de la section précédente, à
Δt = 0,005 s, apparié graine par graine au bilan de cette section (Δt = 0,01 s, macOS).
Les graines 1 et 2 de ce bilan, relancées sous Windows, donnent des résultats identiques au
bit près. Ce n'est pas vrai partout : sur 160 évacuations, #131 trouve 16 écarts entre macOS et
Windows, au plus 0,024 s sur t100. L'effet du pas ci-dessous peut donc contenir un écart de
plateforme de cet ordre, 40 fois plus petit que sa dispersion entre graines (0,98 s sur Δ t100).

| Écart mouillé − sec | Δt = 0,01 s | Δt = 0,005 s | Effet du pas | Erreur standard de Δ |
|---|---|---|---|---|
| Δ t50 (s) | 6,53 ± 0,87 | 6,07 ± 0,77 | −0,45 ± 0,81 | 0,27 |
| Δ t90 (s) | 12,93 ± 1,20 | 12,96 ± 1,13 | +0,03 ± 0,93 | 0,38 |
| Δ t100 (s) | 13,95 ± 1,53 | 13,95 ± 1,27 | +0,005 ± 0,98 | 0,48 |
| Δ J_s (pers/(m·s)) | −0,433 ± 0,044 | −0,433 ± 0,035 | +0,000 ± 0,028 | 0,014 |

Δ t100 et Δ J_s ne dépendent pas du pas : leur moyenne bouge de 1 % de leur erreur standard.
Δ t50 bouge de 0,45 s, 1,7 fois son erreur standard, sans être significatif sur 10 graines
(t = 1,8). Avec le critère 2 proposé dans `criteres-acceptation.md` (#134), Δ t50 de cette
configuration se publie au pas de 0,005 s, ou avec cet écart.

## Chutes : campagne exploratoire (16 novembre 2026)

**Ce ne sont pas des résultats.** Aucun des quatre paramètres balayés n'a de source primaire
(`modele-chutes.md`, § 8). La référence reste sans chutes, et cette campagne montre
seulement ce que les chutes changeraient, et à quelles hypothèses c'est sensible (journal,
16 novembre).

Référence régulée (`experiments/piscine.yaml`, T = 0,35 s), graines 1 à 10, un paramètre à
la fois, les autres valeurs du module par défaut (λ_chute = 2 /s, λ_domino = 4 /s,
λ_bousculade = 0, r_terre = 1,5 r). Le témoin sec garde les mêmes chutes. Commit `4400d84`,
sans modification locale ; cinq balayages en parallèle, 35 min sous Windows. Une première
exécution, sur le même code, avait donné exactement les mêmes mesures au bit près.
[Bilans bruts](mesures/chutes-exploratoire-2026-11-16/) ; répartition par cause et test
apparié sur le pas de temps : `analyse.py`, dans le même dossier.

```bash
viscocrowd balayer-piscine experiments/piscine.yaml --parametre lambda_chute \
  --valeurs 0.5 1 2 5 10 --graines 1 2 3 4 5 6 7 8 9 10
# de même : lambda_domino 1 4 16 ; lambda_bousculade 0 2 10 ; facteur_rayon_terre 1 1.5 2 ;
# dt 0.01 0.005 avec --fixer lambda_chute=2
```

Chutes par évacuation sur le mouillé (moyenne sur 10 graines) et écarts Δ = mouillé − témoin :

| Balayage | Valeur | Glissades | Domino | Bousculade | t100 mouillé (s) | Δ t50 (s) | Δ t100 (s) | Δ t100 > 0 |
|---|---|---|---|---|---|---|---|---|
| λ_chute (1/s) | 0,5 | 11,5 | 45,5 | 0 | 58,32 ± 7,95 | 0,53 ± 1,30 | 6,97 ± 7,84 | 10/10 |
| | 1 | 21,1 | 62,5 | 0 | 61,52 ± 6,32 | 0,94 ± 0,98 | 10,16 ± 6,22 | 10/10 |
| | **2** | **29,6** | **85,4** | **0** | **63,36 ± 6,09** | **1,64 ± 1,27** | **12,01 ± 5,25** | **10/10** |
| | 5 | 58,6 | 126,0 | 0 | 68,35 ± 6,56 | 3,93 ± 2,42 | 17,00 ± 7,56 | 10/10 |
| | 10 | 105,7 | 145,8 | 0 | 76,14 ± 7,11 | 8,48 ± 2,85 | 24,79 ± 7,57 | 10/10 |
| λ_domino (1/s) | 1 | 34,0 | 29,0 | 0 | 57,42 ± 4,35 | 0,26 ± 0,62 | 6,06 ± 4,74 | 9/10 |
| | 16 | 25,9 | 149,0 | 0 | 69,11 ± 6,00 | 3,30 ± 4,17 | 17,76 ± 5,78 | 10/10 |
| λ_bousculade (1/s) | 2 | 30,7 | 89,6 | 2,3 | 61,35 ± 8,38 | 1,72 ± 2,30 | 9,42 ± 7,94 | 9/10 |
| | 10 | 26,3 | 93,6 | 9,3 | 65,00 ± 5,60 | 1,61 ± 1,52 | 11,72 ± 8,04 | 10/10 |
| r_terre (× r) | 1 | 68,2 | 55,8 | 0 | 72,36 ± 12,61 | 2,41 ± 2,63 | 21,01 ± 12,96 | 10/10 |
| | 2 | 25,9 | 99,1 | 0 | 62,82 ± 4,90 | 0,88 ± 0,81 | 11,47 ± 4,95 | 10/10 |

La ligne en gras est le point par défaut, commun aux cinq balayages. Le témoin sec ne tombe
jamais sans bousculade ; avec λ_bousculade = 2 et 10 /s, il compte 8,1 et 36,6 chutes par
évacuation (1,4 et 7,0 bousculades, que le domino propage).

**Pas de temps, glissade et domino actifs** (λ_chute = 2 /s, mêmes graines) :

| Δt (s) | Chutes par évacuation | Glissades | Domino | Δ t100 (s) |
|---|---|---|---|---|
| 0,01 | 115,0 | 29,6 | 85,4 | 12,01 ± 5,25 |
| 0,005 | 108,5 | 30,2 | 78,3 | 10,00 ± 6,24 |

Écart apparié Δt/2 − Δt : −6,5 ± 22,0 chutes (IC 95 % : −22,2 à +9,2 ; p = 0,37 par
permutation exacte des signes). Glissade +0,6 ± 10,6 (+2 %, p = 0,88), domino −7,1 ± 13,8
(−8 %, p = 0,15).

Ce qu'on en retient :

1. **Avec des chutes, le sol mouillé a un effet net**, le premier de ce modèle : t100 recule
   de 6 à 25 s selon les hypothèses, sur 9 ou 10 graines sur 10. Les glissades partent de la
   bande mouillée, où les relances dépassent 3,3 m/s², et le domino les propage.
2. **Le domino domine** : 85 des 115 chutes au point par défaut, près de trois par glissade.
   C'est lui qui transforme une glissade en retard.
3. **Les nombres ne sont pas plausibles** : 115 chutes pour 100 baigneurs au point par
   défaut, 57 même à λ_chute = 0,5 /s. L'amplitude dépend entièrement de taux sans source ;
   seuls le sens et la sensibilité sont lisibles.
4. **r_terre n'est pas monotone.** À r_terre = r, il y a deux fois plus de glissades (68
   contre 30) et le plus grand retard (+21 s). Ce n'est pas expliqué.
5. **La bousculade ne dépend pas du sol** : elle touche aussi le témoin, par compression
   devant la porte, et Δ ne croît pas avec elle.
6. **Aucune dépendance décelable au pas de temps** dans une évacuation, pour la glissade
   comme pour le domino. Sur 10 graines, une dépendance de l'ordre de 20 % ne peut pas être
   exclue.

## Portée et limites

Ce que ces balayages permettent d'écrire : **dans notre modèle, et dans la piscine de
référence, le carrelage mouillé n'a pas d'effet mesurable sur l'évacuation**, parce que les
changements de vitesse ont lieu loin du goulot et que la porte n'est saturée que sous un
mètre de large, à 17 m de la bande mouillée. C'est
une conclusion conditionnelle. Elle ne dit pas que le sol mouillé est sans effet en général,
pour quatre raisons :

1. **La référence ne prête au mouillé qu'un effet.** Elle borne l'accélération : on freine et
   on tourne moins vite. Elle ne fait pas tomber : les chutes, sans taux sourcés, ne sont que
   dans la campagne exploratoire (section précédente), où elles donnent au mouillé un effet
   net. Elle ne ralentit pas non plus la marche : `s` est le même sur le sec et le mouillé.
   C'est un choix de protocole, pour isoler l'effet de l'adhérence (#26), pas une
   observation.
2. **La porte n'est encombrée qu'à 0,8 m** (section précédente), et la bande mouillée de
   3 m en est à 17 m. L'effet du mouillé sur la zone d'accumulation elle-même, avec du
   mouillé jusqu'à la porte, reste à mesurer.
3. **La foule est trop rapide au goulot.** E0 mesure un débit 1,9 à 2,5 fois celui de
   Seyfried : nos baigneurs ne ralentissent pas derrière celui qui les précède. La relation
   vitesse–espacement (#58) corrige ce point sur E0. Les balayages du 2 novembre ont été
   faits sans elle. Elle est activée dans la piscine depuis le 10 novembre (#57) et ramène
   le débit à la porte de 3,20 à 2,25 pers/(m·s) (section précédente), encore au-dessus de
   Seyfried.
4. **La porte se bouchait artificiellement** (ci-dessus). Ses montants sont arrondis
   depuis le 13 novembre (#125), et les balayages de porte et de population ont été
   refaits sans aucun bouchage.

Avant de conclure le rapport, il reste donc à combiner une porte saturée (0,8 m) et du
mouillé jusqu'à la porte. L'effet des chutes est mesuré de façon exploratoire (16 novembre) ;
il ne deviendra un résultat qu'avec des taux sourcés.
