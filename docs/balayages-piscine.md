# Balayages E3/E4 de la piscine (M6)

Au point de référence (`experiments/piscine.yaml`), le carrelage mouillé ne change rien de
mesurable à l'évacuation (#83). Deux raisons, relevées dans [#26](https://github.com/ViscoCrowd/ViscoCrowd-simulation/issues/26) :

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
| `facteur_vitesse` | E4 | – | niveau de panique : multiplie toutes les vitesses souhaitées |
| `largeur_porte` | E4 | m | largeur du goulot |
| `n_agents` | E4 | pers | nombre de baigneurs |
| `dt` | M9 | s | pas de temps : vérifier que les écarts n'en dépendent pas (spec § 5) |

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

Un balayage de 4 valeurs sur 10 graines à 100 agents représente 40 à 80 évacuations, soit
environ 10 s chacune sur un poste récent.

## Premiers résultats

<!-- rempli après les balayages du 2 novembre -->
