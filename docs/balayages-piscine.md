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
| `facteur_vitesse` | E4 | – | niveau de panique : multiplie toutes les vitesses souhaitées |
| `largeur_porte` | E4 | m | largeur du goulot |
| `n_agents` | E4 | pers | nombre de baigneurs |
| `temps_espacement` | E4 | s | temps d'espacement T de la relation vitesse–espacement (Tordeux et al.) ; 0,35 s, étalonné sur E0 (#58), dans le YAML depuis le 10 novembre (#57). `temps_espacement: null` dans le YAML la désactive ; `--fixer` n'accepte pas `null` |
| `relaxation` | M9 | s | temps de relaxation τ, **commun** à l'eau, au mouillé et au sec (témoin compris) : vérifier que les conclusions tiennent quand τ varie |
| `dt` | M9 | s | pas de temps : vérifier que les écarts n'en dépendent pas (spec § 5) |

**Balayer `lambda_chute` active les chutes.** `experiments/piscine.yaml` n'a pas de section
`chutes` : le balayage la crée, et toutes les autres valeurs du module (domino, relevage,
contournement) restent celles par défaut de `ParametresChutes`. Ces valeurs ne sont pas
calibrées : comme le précise [`modele-chutes.md`](modele-chutes.md), aucun chiffre obtenu
avec ce module ne peut servir de résultat avant sa calibration. L'enseignant a validé son
inclusion dans le rendu le 3 novembre (#19), pas ses valeurs. Le témoin sec garde les
**mêmes** chutes que le mouillé, si bien que Δ ne mesure que le sol.

Le nombre d'échelles n'est pas balayé : il faudrait d'abord choisir où placer les échelles
ajoutées, ce qui est un choix de scénario à faire en groupe.

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
sortis, en s), le débit à la porte, en pers/(m·s), et le nombre de baigneurs encore présents
à la fin de `duree`. Le débit utilise le même estimateur que le goulot E0 (`debit_seyfried`,
ΔN/(Δt·b)), pour que les deux restent comparables.

Le tableau affiche, pour chaque valeur, `t100` du mouillé, la moyenne ± écart-type de chaque
Δ, les non-sortis (total sur les graines, mouillé/témoin) et le nombre de graines où le
mouillé est plus lent (`Δ t100 > 0`). Le JSON garde toutes
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
| 200 | 47,61 ± 0,44 | 73,99 ± 0,56 | 84,78 ± 1,52 | 2,85 ± 0,05 | 0,07 ± 0,24, 8/10 |

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

## Sensibilité à τ et à la vitesse sur le mouillé (14 novembre 2026)

Commit `3d6d43a`, sans modification locale, macOS arm64 ; `experiments/piscine.yaml` de
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
   d'inertie, mais un effet de prudence, que le modèle impose par hypothèse.
3. **Sur la fin de l'évacuation, l'effet se dilue.** Δ t100 change de signe d'une graine à
   l'autre, avec un écart-type de 1 s : la porte et l'extraction de l'eau imposent le rythme.

## Portée et limites

Ce que ces balayages permettent d'écrire : **dans notre modèle, et dans la piscine de
référence, le carrelage mouillé n'a pas d'effet mesurable sur l'évacuation**, parce que les
changements de vitesse ont lieu loin du goulot et que la porte n'est saturée que sous un
mètre de large, à 17 m de la bande mouillée. C'est
une conclusion conditionnelle. Elle ne dit pas que le sol mouillé est sans effet en général,
pour quatre raisons :

1. **Le modèle ne prête au mouillé qu'un effet.** Il borne l'accélération : on freine et on
   tourne moins vite. Il ne fait pas tomber (modèle de chutes, #78 et #82, pas encore
   fusionné), et il ne ralentit pas la marche : `s` est le même sur le sec et le mouillé.
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
mouillé jusqu'à la porte, et à mesurer l'effet des chutes.
