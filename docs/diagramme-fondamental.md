# Diagramme fondamental devant le goulot E0 (M8, #124)

E0 compare le **débit global** du goulot à Seyfried et al. (2009) ([`goulot.yaml`](../experiments/goulot.yaml), journal, entrée E0). La problématique porte, elle, sur le **diagramme fondamental**, la relation entre la densité d'une foule et sa vitesse ou son débit (spec § 3). `viscocrowd diagramme-goulot` mesure cette relation devant le goulot sec et la confronte à Weidmann (1993).

## Commande

```bash
viscocrowd diagramme-goulot experiments/goulot.yaml \
  --sortie data/m8/diagramme.json --figure data/m8
```

Par défaut : les cinq largeurs du protocole (0,8 à 1,2 m), dix graines à partir de celle du YAML, la zone `x ∈ [6,0 ; 7,8] m`, `y ∈ [1,5 ; 3,5] m`, un instant toutes les 0,1 s à partir de 3 s, et des classes de 0,25 pers/m². Les 50 simulations prennent environ 5 min en séquence. Les mesures ci-dessous ont été lancées une largeur par processus, ce qui donne exactement les mêmes séries.

## Mesure

- **Points.** À chaque instant retenu : densité et vitesse de Voronoï dans la zone (Steffen et Seyfried 2010, `mesures_voronoi`), avec le débit spécifique `J = ρ v`. La vitesse d'un agent est son déplacement réalisé sur le pas précédent, c'est-à-dire la vitesse du modèle relue après la projection.
- **Classes.** `observables.diagramme.classer` donne la moyenne et l'écart-type de chaque classe de densité. Les points d'une même simulation sont corrélés : **l'écart-type décrit la dispersion des états, pas l'incertitude sur la moyenne**.
- **Trois choix, à discuter avant toute conclusion :**
  1. **Zone** : l'entonnoir où #101 a mesuré le biais de densité. Les cellules sont bornées par les murs de la salle, mur percé compris. C'est exact sur trois côtés et approché près de l'ouverture, où les agents déjà engagés dans le goulot ne comptent pas.
  2. **Début à 3 s** : à t = 0, la foule est au repos à 3,3 pers/m², puis le bloc démarre d'un seul tenant. En commençant à 1 s, 396 points formaient une branche à fort débit (ρ > 3,3 pers/m², J > 1,3 pers/(m·s)), tous entre 1,0 et 1,9 s. À partir de 3 s, il n'en reste aucun.
  3. **Pas de mesure de 0,1 s** : des instants plus serrés ne seraient pas plus indépendants.
  4. **Pas de borne de fin** : la mesure court jusqu'à la sortie du dernier agent. Or E0 n'a pas de phase stationnaire : 60 agents partent à 3,3 pers/m² et la salle se vide sans palier. Sur la graine 1 à b = 1,2 m, la densité de la zone vaut 4,6 pers/m² à 3 s, 2,3 à 11 s, 1,0 à 22 s et 0,02 à 27 s. Chaque point est donc un instant d'une file qui se vide, et non un état d'équilibre comme ceux que mesurent Weidmann ou Seyfried. Pour chaque largeur, 99 à 100 % des points à ρ < 1 pers/m² tombent dans le dernier tiers de leur série (634 sur 4 288 à b = 0,8 m, 500 sur 2 513 à 1,2 m) : **les classes sous 1 pers/m² décrivent la fin de la vidange**, quand les derniers agents suivent ceux déjà engagés dans le goulot.

## Résultats du 13 novembre 2026

Commit `259c5f8`, sans modification locale, Windows 11, Python 3.12.10, NumPy 2.5.4, SciPy 1.18.1. `goulot.yaml` de référence (60 agents, T = 0,35 s). Graines 1 à 10, 50 écoulements, **15 641 points**. Bilans par largeur et figure dans [`mesures/diagramme-e0-2026-11-13/`](mesures/diagramme-e0-2026-11-13/).

![Diagramme fondamental devant le goulot E0](mesures/diagramme-e0-2026-11-13/fig08_diagramme_fondamental.png)

Toutes largeurs confondues, en classes de 0,5 pers/m² :

| ρ moyen (pers/m²) | Points | v (m/s) | v Weidmann | J (pers/(m·s)) | J Weidmann |
|---|---|---|---|---|---|
| 0,21 | 1601 | 0,83 ± 0,35 | 1,34 | 0,15 ± 0,13 | 0,28 |
| 0,77 | 1000 | 0,59 ± 0,22 | 1,18 | 0,45 ± 0,17 | 0,91 |
| 1,29 | 2140 | 0,49 ± 0,14 | 0,91 | 0,62 ± 0,19 | 1,17 |
| 1,75 | 2627 | 0,40 ± 0,12 | 0,70 | 0,69 ± 0,19 | 1,23 |
| 2,24 | 2659 | 0,29 ± 0,09 | 0,53 | 0,64 ± 0,20 | 1,18 |
| 2,74 | 1886 | 0,21 ± 0,07 | 0,39 | 0,58 ± 0,19 | 1,07 |
| 3,23 | 1233 | 0,19 ± 0,06 | 0,29 | 0,60 ± 0,20 | 0,92 |
| 3,75 | 763 | 0,18 ± 0,06 | 0,19 | 0,69 ± 0,22 | 0,73 |
| 4,27 | 817 | 0,12 ± 0,04 | 0,12 | 0,52 ± 0,18 | 0,51 |
| 4,75 | 765 | 0,09 ± 0,03 | 0,06 | 0,43 ± 0,13 | 0,30 |
| 5,09 | 150 | 0,08 ± 0,01 | 0,03 | 0,41 ± 0,06 | 0,15 |

Vitesse moyenne de la classe autour de 1 pers/m², par largeur : 0,36 m/s (b = 0,8 m), 0,54 (0,9), 0,64 (1,0), 0,65 (1,1) et 0,83 m/s (1,2).

## Ce que ces mesures disent, et ce qu'elles ne disent pas

- **Sous 3 pers/m², la vitesse vaut 50 à 62 % de celle de Weidmann**. Sous 1 pers/m², ce sont les derniers agents de la vidange, pas une foule clairsemée (choix 4). Le débit plafonne vers 0,7 pers/(m·s), contre 1,23. Les deux se rejoignent vers 4 pers/m², et au-delà de 4,5 pers/m² la vitesse dépasse celle de Weidmann. Le modèle n'a pas de densité d'arrêt : seul l'empilement compact des disques, 7,2 pers/m², l'arrête. Weidmann, lui, s'arrête à 5,4 pers/m².
- **À densité égale, la vitesse dépend de la largeur du goulot**, du simple au double entre 0,8 et 1,2 m. Devant un goulot, l'écoulement est réglé par la capacité du goulot, et non par la seule densité locale. Une partie de cet écart tient aussi à la vidange : un goulot large vide la salle plus vite, si bien qu'à 1 pers/m² on ne compare pas le même moment de l'évacuation.
- **Ce n'est donc pas une comparaison dans le domaine de Weidmann.** Ses relations valent « sans contrainte extérieure », pour une marche unidirectionnelle (p. 64). L'entonnoir devant un goulot n'en relève pas. Ces chiffres ne valident ni ne réfutent le modèle face à Weidmann. Ils décrivent la file d'attente devant un goulot.
- **Pour comparer dans le domaine de Weidmann**, il faudrait une mesure en écoulement libre unidirectionnel, par exemple dans le couloir, à plusieurs densités imposées. C'est la prochaine étape proposée dans #124, avec la mesure devant la porte de la piscine.

---

# Devant la porte de la piscine : mouillé contre sec (#124)

La question de la problématique : le carrelage mouillé déplace-t-il le diagramme fondamental devant la porte ? `viscocrowd diagramme-piscine` mesure la densité et la vitesse de Voronoï devant la porte, pour la piscine mouillée (E2) et pour le témoin entièrement sec (E1), appariés graine par graine (`scenarios/diagramme_piscine.py`).

```bash
viscocrowd diagramme-piscine experiments/piscine.yaml --graines 1 2 3 4 5 6 7 8 9 10 \
  --sortie data/m8/piscine.json
viscocrowd diagramme-piscine experiments/piscine.yaml --graines 1 2 3 4 5 6 7 8 9 10 \
  --fixer largeur_porte=0.8 --sortie data/m8/piscine-0.8.json
```

## Méthode

- **Salle de Voronoï.** La plage n'est pas convexe, puisque le bassin y fait un trou. On prend donc le rectangle de la plage qui va de 10 m avant le mur de la porte jusqu'à ce mur, sur toute la largeur (`x ∈ [38 ; 48] m`). Il ne contient ni le bassin ni les points de réintroduction : la commande refuse tout recul qui les atteindrait, et tout obstacle dans la salle. Les nageurs, les agents sur un bord, les agents déjà sortis et les plagistes plus loin de la porte n'ont pas de cellule. La mesure est exacte près de la porte, et approchée sur le bord gauche du rectangle, à 8 m de la zone.
- **Zone.** 1,8 m sur 2 m devant la porte, centrée sur son axe, à 0,2 m du mur, comme celle de E0.
- **Instants.** Toute l'évacuation, un instant toutes les 0,1 s. Comme pour E0, il n'y a pas de phase stationnaire : la file se forme puis se vide.

## Résultats du 14 novembre 2026

Code du commit `0ff523d` (les bilans indiquent `modifications_locales: true`, car ce module a été mesuré juste avant d'être commité, sans autre changement), sur la branche de #126, à jour avec `dev` après #128. macOS arm64, Python 3.14.4. Graines 1 à 10, 20 évacuations par largeur. Bilans dans [`mesures/diagramme-piscine-2026-11-14/`](mesures/diagramme-piscine-2026-11-14/).

**Porte de 1,2 m (référence), 8 339 points.** Pas de file : la porte n'est jamais saturée (E4, #128).

| ρ (pers/m²) | Points sec / mouillé | v sec (m/s) | v mouillé (m/s) | v Weidmann |
|---|---|---|---|---|
| 0,12 | 2615 / 2574 | 1,97 ± 0,11 | 1,97 ± 0,11 | 1,34 |
| 0,38 | 1264 / 1292 | 1,60 ± 0,27 | 1,61 ± 0,26 | 1,33 |
| 0,62 | 248 / 256 | 1,28 ± 0,20 | 1,28 ± 0,20 | 1,25 |
| 0,88 | 40 / 38 | 1,12 ± 0,17 | 1,13 ± 0,17 | 1,13 |

**Porte de 0,8 m (saturée), 12 189 points.** Une branche congestionnée apparaît.

| ρ (pers/m²) | Points sec / mouillé | v sec (m/s) | v mouillé (m/s) | v Weidmann |
|---|---|---|---|---|
| 0,12 | 1066 / 1092 | 1,68 ± 0,45 | 1,67 ± 0,46 | 1,34 |
| 0,38 | 302 / 281 | 0,92 ± 0,44 | 0,96 ± 0,43 | 1,33 |
| 0,62 | 628 / 776 | 0,69 ± 0,19 | 0,67 ± 0,17 | 1,25 |
| 0,88 | 2973 / 2863 | 0,58 ± 0,07 | 0,58 ± 0,08 | 1,13 |
| 1,12 | 757 / 707 | 0,54 ± 0,10 | 0,54 ± 0,10 | 0,99 |
| 1,38 | 264 / 276 | 0,50 ± 0,07 | 0,50 ± 0,07 | 0,87 |
| 1,62 | 88 / 92 | 0,46 ± 0,09 | 0,45 ± 0,09 | 0,75 |
| 1,88 | 14 / 10 | 0,39 ± 0,03 | 0,40 ± 0,03 | 0,65 |

(Écart-type = dispersion des états, pas incertitude. Classes de 0,25 pers/m², centre de classe indiqué.)

## Ce que ces mesures disent, et ce qu'elles ne disent pas

- **Le carrelage mouillé ne déplace pas le diagramme devant la porte**, ni à 1,2 m ni à 0,8 m : dans chaque classe, les vitesses du sec et du mouillé diffèrent de quelques centièmes de m/s, bien moins que leur dispersion. C'est cohérent avec E1/E2 et E4 (§ 6 du rapport) : la bande mouillée est à 17 m de la porte, et les agents l'ont quittée bien avant la file.
- **À 1,2 m, la zone ne voit presque que de la marche libre.** Sous 0,5 pers/m², la vitesse vaut celle souhaitée en panique (2,0 m/s), au-dessus de Weidmann, qui décrit une marche ordinaire.
- **À 0,8 m, la file freine fort.** Entre 0,6 et 1,9 pers/m², la vitesse vaut 45 à 60 % de celle de Weidmann. Ce n'est pas une comparaison dans son domaine (foule contrainte par une porte saturée, en panique), mais c'est la branche congestionnée que la problématique demande de comparer entre sec et mouillé.
- **La densité reste modérée** (sous 2 pers/m²) parce que la zone couvre aussi les côtés de la porte, où la foule est plus clairsemée qu'en son centre. Une zone plus étroite, sur l'axe, donnerait des densités plus fortes : c'est l'un des choix à discuter.
- Une bande mouillée qui atteint la porte saturée (`--fixer largeur_porte=0.8 largeur_mouillee=20`) est la configuration où l'hypothèse inertielle aurait le plus de chances d'apparaître. Elle n'est pas mesurée ici.
