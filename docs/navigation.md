# Navigation locale des baigneurs (#158)

**Statut** : module facultatif (`navigation:` dans le YAML de la piscine et du goulot E0,
`null` par défaut). La référence n'est pas modifiée : l'activer est une décision de groupe
(#158), à prendre au vu de la validation ci-dessous.

## Le problème

Le guidage eikonal donne à tous le même plus court chemin vers la porte. Sur la plage, ce
chemin longe le bord du bassin à un rayon près, puis va en ligne droite du coin du bassin à
la porte. Comme rien n'écartait un agent de cette ligne (vitesses identiques, aucune
anticipation, régulation qui fait suivre le précédent), les baigneurs marchaient **en file
indienne contre le bord, puis en deux lignes parfaites vers la porte**. Sur dix graines,
93 % des positions de plage le long du bassin étaient à moins de 1 cm du plus près
possible, et le flux faisait 6 cm d'épaisseur.

## Le modèle : Moussaïd, Helbing et Theraulaz (2011)

*How simple rules determine pedestrian behavior and crowd disasters*, PNAS 108(17),
p. 6884-6888, vérifié sur l'original (`moussaid2011` dans la bibliographie). Deux
heuristiques fondées sur la vision :

1. **Direction.** Dans son champ de vision, de −φ à +φ autour de sa ligne de visée, le
   piéton choisit la direction α qui minimise la distance à sa destination
   `d(α)² = d_max² + f(α)² − 2 d_max f(α) cos(α₀ − α)`, où α₀ est la direction de la
   destination et f(α) la distance à la première collision s'il marchait dans la direction
   α à sa vitesse souhaitée, compte tenu de la vitesse et de la taille des autres,
   plafonnée à l'horizon d_max.
2. **Vitesse.** `v_des = min(v0, d_h / τ)`, où d_h est la distance au premier obstacle
   dans la direction choisie, à l'instant t.

La vitesse relaxe ensuite vers `v_des e_des`, comme dans tout le modèle (τ et a_max du
sol). Valeurs de l'article, reprises par défaut : τ = 0,5 s, φ = 75°, d_max = 10 m
(fig. 2), vitesse souhaitée tirée selon une loi normale de coefficient de variation
0,2/1,3 = 0,15 (fig. 3).

## Ce qui est adapté, et pourquoi

| Article | Ici | Pourquoi |
|---|---|---|
| Destination : un point | Direction du champ eikonal | La porte est derrière le coin du bassin : le champ donne la direction du plus court chemin, que l'heuristique corrige localement |
| Forces de contact k g(r_i + r_j − d_ij) | Projection du moteur | L'exclusion dure du cours reste inchangée |
| Heuristiques : tous les piétons | Agents sur la plage seulement | Nager n'est pas marcher ; les nageurs gardent le champ de l'eau |
| Vitesse individuelle : tous les piétons | Tous les agents actifs, **nageurs compris** | Un seul tirage par agent, gardé de l'eau à la plage. Il change aussi l'ordre d'arrivée aux échelles et aux rebords : la mesure sépare donc les deux effets (variante sans dispersion) |
| v0 ~ N(1,3 ; 0,2) m/s | Vitesse du sol × facteur individuel ~ N(1 ; 0,15), tronqué à ±3σ | Les sols et le facteur de panique gardent leur sens ; la troncature garde le déplacement par pas sous r/5 |
| — | Régulation T de Tordeux remplacée sur la plage | La seconde heuristique en est la version 2D, avec τ = 0,5 s au lieu de T = 0,35 s |
| Seconde heuristique : tous les piétons | Seuls les agents **plus avancés vers la sortie** (temps eikonal restant) | Sans cela, devant un goulot étroit, deux voisins côte à côte s'attendaient l'un l'autre, à l'arrêt, et E0 se figeait (voir la validation). L'article en sort par ses forces de contact, que la projection n'a pas : elle ne pousse pas un agent arrêté. C'est la règle d'ordre de la régulation T (`model.espacement`). Le choix de direction, lui, évite tout le monde |
| — | Marge de 1 mm face aux parois | La projection tolère 10⁻⁶ m de recouvrement ; sans marge, un agent posé contre le bassin voyait toutes ses directions bouchées |

Les obstacles vus sont les murs, le bassin, les montants de la porte (coins arrondis, comme
la projection depuis #125), les obstacles fixes et les autres agents de la plage. Une
première version à coins vifs figeait les baigneurs qui glissaient le long du coin d'un
montant, et la porte se bouchait.

## Mesure sur la piscine (17 novembre 2026, complétée le 18)

Référence `experiments/piscine.yaml` (régulée, T = 0,35 s), graines 1 à 10, commit
`0cb0490` sans modification locale, Windows, 12 évacuations en parallèle. Script et bilan :
[`mesures/navigation-2026-11-17/`](mesures/navigation-2026-11-17/) (`mesurer.py`,
`resultats.json`, `sortie.txt`).

```bash
python docs/mesures/navigation-2026-11-17/mesurer.py experiments/piscine.yaml
```

| | Référence | Navigation | Navigation sans dispersion | Navigation, Δt/2 | Navigation, sol sec | Navigation, fig. 3 (45°, 8 m) |
|---|---|---|---|---|---|---|
| Positions de plage contre le bord du bassin | 92,9 ± 3,3 % | **9,0 ± 1,5 %** | 9,4 ± 1,8 % | 8,7 % | 9,1 % | 9,0 % |
| Épaisseur du flux (écart interquartile latéral) | 0,06 m | **0,77 m** | 0,69 m | 0,77 m | 0,76 m | 0,66 m |
| t50 (s) | 31,43 ± 0,52 | 30,68 ± 0,73 | 29,75 ± 1,04 | 30,66 ± 0,79 | 30,40 ± 0,61 | 30,64 ± 0,85 |
| t90 (s) | 45,40 ± 0,76 | 43,24 ± 0,71 | 41,78 ± 0,89 | 43,27 ± 1,08 | 42,59 ± 0,95 | 43,03 ± 1,08 |
| t100 (s) | 51,28 ± 1,87 | 47,17 ± 0,77 | 44,93 ± 0,91 | 47,09 ± 1,13 | 46,33 ± 0,95 | 47,24 ± 1,30 |
| Débit à la porte (pers/(m·s)) | 2,28 ± 0,10 | 2,46 ± 0,07 | 2,76 ± 0,10 | 2,47 ± 0,07 | 2,52 ± 0,09 | 2,46 ± 0,11 |
| Calcul par évacuation | 30 s | 75 s | 67 s | 157 s | 80 s | 73 s |

Les cinq variantes de la première mesure (commit `907ec49`, avant la fusion de `dev`)
redonnent ses valeurs au bit près ; seuls les temps de calcul changent. « Sans
dispersion » : `navigation: {dispersion_vitesse: 0}`, tous les agents à la
vitesse du sol. Elle sépare les deux changements qu'apporte la navigation (revue de
#163) : les heuristiques, sur la plage seulement, et la vitesse individuelle, qui vaut
aussi dans l'eau.

Écarts appariés, graine par graine. Entre parenthèses : nombre de graines du signe de la
moyenne, puis deux valeurs p, la permutation exacte des signes sur la moyenne et le test
de signe exact de [`criteres-acceptation.md`](criteres-acceptation.md) (§ 3), qui seul
décide d'une détection. Calculés par `mesurer.py` (`sortie.txt`).

| | Δ t50 (s) | Δ t100 (s) | Δ débit (pers/(m·s)) |
|---|---|---|---|
| Navigation − référence | −0,74 ± 0,74 (10/10 ; 0,002 / 0,002) | **−4,11 ± 1,67** (10/10 ; 0,002 / 0,002) | +0,18 ± 0,11 (10/10 ; 0,002 / 0,002) |
| Sans dispersion − référence (heuristiques seules) | −1,68 ± 0,88 (10/10 ; 0,002 / 0,002) | **−6,34 ± 1,76** (10/10 ; 0,002 / 0,002) | +0,48 ± 0,13 (10/10 ; 0,002 / 0,002) |
| Navigation − sans dispersion (effet de la dispersion) | +0,93 ± 0,93 (9/10 ; 0,014 / 0,021) | **+2,23 ± 0,96** (10/10 ; 0,002 / 0,002) | −0,30 ± 0,09 (10/10 ; 0,002 / 0,002) |
| Δt/2 − Δt (navigation) | −0,02 ± 0,65 (6/10 ; 0,90 / 0,75) | −0,07 ± 1,03 (5/10 ; 0,82 / 1,00) | +0,01 ± 0,08 (5/10 ; 0,83 / 1,00) |
| Mouillé − sec (navigation) | +0,28 ± 0,80 (7/10 ; 0,28 / 0,34) | +0,84 ± 1,10 (8/10 ; 0,04 / 0,11) | −0,06 ± 0,08 (7/10 ; 0,04 / 0,34) |
| Fig. 3 − fig. 2 | −0,04 ± 0,87 (6/10 ; 0,87 / 0,75) | +0,08 ± 1,09 (6/10 ; 0,84 / 0,75) | −0,00 ± 0,08 (7/10 ; 0,88 / 0,34) |

![Graine 1, à 20, 28 et 36 s : en haut la référence, en bas la navigation](mesures/navigation-2026-11-17/avant-apres.png)

*Graine 1, à 20, 28 et 36 s. En haut, la référence : deux files contre le bassin, puis deux lignes vers la porte. En bas, la navigation : des flux diffus, puis une foule devant la porte. Pointillés : limite de la bande mouillée.*

## Validation

Les heuristiques font marcher les baigneurs de façon plus naturelle ; reste à savoir si
elles donnent les bons débits et les bonnes vitesses. Deux bancs du projet le mesurent,
avec les valeurs de l'article et **sans aucun réglage**.

### Goulot E0, comparé à Seyfried et al. (2009)

`experiments/goulot.yaml`, sans régulation T (`temps_espacement: null`), avec la
navigation ; graines 1 à 10, commit `907ec49` sans modification locale. Script et bilan :
`mesures/navigation-2026-11-17/e0.py`, `e0.json`, `e0.txt`. Deux variantes : τ = 0,5 s
(l'article) et τ = 0,35 s pour la seconde heuristique, la valeur de T étalonnée pour E0.

```bash
python docs/mesures/navigation-2026-11-17/e0.py experiments/goulot.yaml
```

**Premier essai, sans la règle d'ordre** (même protocole, code non archivé) : la foule se
figeait devant les goulots étroits. À N = 40 et b = 0,8 m, 10 graines sur 10 bouchaient ;
à N = 60 et b = 0,8 ou 0,9 m, 9 sur 10. Deux voisins se voyaient l'un l'autre comme
premier obstacle et s'arrêtaient ensemble. D'où la règle d'ordre du tableau des
adaptations. Avec elle :

| N | b (m) | Écoulements (τ = 0,5) | J_s, τ = 0,5 s | Écoulements (τ = 0,35) | J_s, τ = 0,35 s | Seyfried |
|---|---|---|---|---|---|---|
| 20 | 0,8 | 10/10 | 1,29 ± 0,10 | 10/10 | 1,39 ± 0,29 | 1,86 |
| 20 | 0,9 | 10/10 | 1,28 ± 0,25 | 10/10 | 1,59 ± 0,17 | 2,06 |
| 20 | 1,0 | 10/10 | 1,51 ± 0,09 | 10/10 | 1,72 ± 0,10 | 2,19 |
| 20 | 1,1 | 10/10 | 1,49 ± 0,09 | 10/10 | 1,76 ± 0,10 | 1,78 |
| 20 | 1,2 | 10/10 | 1,56 ± 0,09 | 10/10 | 1,74 ± 0,13 | 2,31 |
| 40 | 0,8 | 9/10 | 1,24 ± 0,08 | 9/10 | 1,34 ± 0,10 | 1,77 |
| 40 | 0,9 | 10/10 | 1,23 ± 0,18 | 10/10 | 1,53 ± 0,10 | 1,91 |
| 40 | 1,0 | 10/10 | 1,46 ± 0,06 | 10/10 | 1,63 ± 0,06 | 2,08 |
| 40 | 1,1 | 10/10 | 1,51 ± 0,06 | 10/10 | 1,74 ± 0,07 | 1,93 |
| 40 | 1,2 | 10/10 | 1,48 ± 0,09 | 10/10 | 1,73 ± 0,12 | 1,81 |
| 60 | 0,8 | **4/10** | 1,30 ± 0,01 | **6/10** | 1,42 ± 0,04 | 1,61 |
| 60 | 0,9 | 10/10 | 1,28 ± 0,07 | 10/10 | 1,49 ± 0,08 | 1,86 |
| 60 | 1,0 | 10/10 | 1,42 ± 0,04 | 10/10 | 1,61 ± 0,07 | 1,90 |
| 60 | 1,1 | 10/10 | 1,45 ± 0,05 | 10/10 | 1,68 ± 0,05 | 1,93 |
| 60 | 1,2 | 10/10 | 1,48 ± 0,07 | 10/10 | 1,70 ± 0,08 | 1,97 |

J_s en pers/(m·s), estimateur de la publication, moyenne ± écart-type sur les écoulements.
Aucun recouvrement des murs au-delà de 10⁻¹⁵ m.

- **La règle d'ordre supprime presque tous les bouchages** : 288 simulations sur 300
  s'écoulent. Les 12 restantes sont toutes à b = 0,8 m, dont 10 à N = 60.
- **Avec les valeurs de l'article, le débit est de 16 à 38 % sous Seyfried.** La
  régulation T actuelle, étalonnée sur ce banc, en est à −7 à +3 % (N = 60, journal).
- **τ = 0,35 s rattrape environ la moitié de l'écart** (1 à 25 % sous Seyfried). C'est
  attendu : à jeu égal, d_h/τ autorise une vitesse 1,4 fois plus grande. Le reste n'est
  pas expliqué. Pistes non mesurées : devant l'ouverture, les agents s'écartent les uns
  des autres au lieu de se serrer ; et les plus lents, avec la dispersion des vitesses,
  imposent leur cadence dans le goulot.

### Anneau, comparé à Weidmann (1993)

Banc de #149 (couloir circulaire de 5 à 7 m, densité imposée), sans régulation T, avec la
navigation (`scenarios/anneau.py`) : destination le long de la tangente, murs circulaires
vus par l'heuristique. Graines 1 à 10, 40 s, vitesse mesurée de 20 à 40 s ; commit
`b91ff1f` sans modification locale, 20 simulations en parallèle, 2 h 30. Script et bilan :
`mesures/navigation-2026-11-17/anneau.py`, `anneau.json`, `anneau.txt`.

```bash
python docs/mesures/navigation-2026-11-17/anneau.py experiments/anneau.yaml
```

Le premier bilan (graines 1 à 3) avait été calculé sur une branche locale (`f186b33`),
avant la fusion de #149. Le code versé dans le dépôt redonne ses 27 points au bit près, et
`tests/test_anneau.py` vérifie le premier (test lent).

| ρ (pers/m²) | 0,25 | 0,50 | 0,99 | 1,50 | 2,00 | 2,49 | 3,00 | 3,50 | 4,01 |
|---|---|---|---|---|---|---|---|---|---|
| v navigation (m/s) | 1,20 | 1,17 | 1,11 | 1,00 | 0,83 | 0,65 | 0,49 | 0,36 | 0,26 |
| v Weidmann | 1,34 | 1,30 | 1,06 | 0,81 | 0,61 | 0,45 | 0,33 | 0,23 | 0,16 |
| v référence T (#149, 10 graines) | 1,34 | 1,34 | 1,34 | 1,34 | 1,34 | 0,58 | 0,43 | 0,31 | 0,20 |
| J navigation (pers/(m·s)) | 0,30 | 0,59 | 1,10 | 1,49 | 1,66 | 1,61 | 1,46 | 1,26 | 1,04 |
| J Weidmann | 0,34 | 0,65 | 1,06 | 1,21 | 1,21 | 1,13 | 0,99 | 0,82 | 0,62 |

Écart-type entre graines : de 0,048 m/s (0,25 pers/m²) à 0,004 m/s (4 pers/m²). À faible
densité, il vient surtout du tirage des vitesses individuelles : avec 19 agents, la
moyenne des facteurs varie d'une graine à l'autre (corrélation 0,92 avec la vitesse
mesurée). Rapportée à la vitesse souhaitée moyenne tirée, la vitesse vaut 0,90 ± 0,014.
Dérive entre les deux moitiés de la fenêtre : 4,3 % au plus.

- **La foule ralentit progressivement dès les faibles densités**, comme chez Weidmann. La
  référence, elle, garde v0 jusqu'à 2 pers/m², puis chute d'un coup. Le débit maximal
  passe de 2,68 (référence) à 1,66 pers/(m·s), pour 1,21 chez Weidmann.
- **Au-dessus de 1,5 pers/m², la navigation va trop vite** : de 23 % (1,5 pers/m²) à
  67 % (4 pers/m²) au-dessus de Weidmann, plus que la référence sur la branche
  congestionnée (28 à 33 %).
- **À faible densité, 10 % sous v0** (1,20 contre 1,34 m/s). Les agents longent le mur
  intérieur (63 % des positions à moins de 8 cm, graine 1), et l'heuristique leur demande
  0,92 v0 en moyenne. Cause probable, non vérifiée : sur l'anneau, la destination est la
  tangente, une droite que le mur courbe coupe. Sur une plage droite, un agent seul
  marche à v0 (`tests/test_navigation.py`).

#### Pourquoi trop vite au-delà de 1,5 pers/m² ?

Deux pistes, testées chacune seule sur les graines 1 à 3 (19 novembre, commit `5aa0ed1`
sans modification locale ; `diagnostic-weidmann.py`, `.json`, `.txt`) :

- **la densité d'arrêt.** Des disques de 0,2 m ne s'arrêtent qu'empilés au plus serré,
  vers 7,2 pers/m² ; Weidmann s'arrête à 5,4 pers/m². Variante : disques de 0,23 m, le
  rayon dont l'empilement compact donne 5,4 pers/m² ;
- **le temps d'anticipation** de la seconde heuristique, v = d_h / τ. Variante :
  τ = 0,7 s au lieu de 0,5 s.

| ρ (pers/m²) | Weidmann (m/s) | r = 0,2 m, τ = 0,5 s | r = 0,23 m | τ = 0,7 s |
|---|---|---|---|---|
| 1,50 | 0,81 | 0,99 (+23 %) | 0,89 (+11 %) | 0,84 (+4 %) |
| 2,00 | 0,61 | 0,83 (+37 %) | 0,65 (+8 %) | 0,66 (+9 %) |
| 2,49 | 0,45 | 0,65 (+42 %) | 0,45 (−1 %) | 0,51 (+13 %) |
| 3,00 | 0,33 | 0,49 (+47 %) | 0,29 (−12 %) | 0,39 (+18 %) |
| 3,50 | 0,23 | 0,36 (+54 %) | 0,18 (−25 %) | 0,28 (+21 %) |

Écart-type entre graines : 0,017 m/s au plus ; dérive : 4,4 % au plus ; aucun
recouvrement au-delà de la tolérance (10⁻⁶ m).

- **La densité d'arrêt fait la forme de l'écart.** Avec des disques à peine plus gros
  (+15 % de rayon), l'écart ne croît plus avec la densité : la courbe croise Weidmann vers
  2,5 pers/m², puis passe dessous. Elle corrige trop, parce qu'une foule désordonnée se
  bloque avant l'empilement compact. La vitesse aux fortes densités est très sensible au
  rayon : −10 % à 1,5 pers/m², −51 % à 3,5 pers/m².
- **τ en fixe le niveau, pas la forme** : environ −20 % à toutes les densités, et l'écart
  croît toujours (+4 % puis +21 %).
- **Aucune des deux ne cale toute la courbe**, et ce n'est pas un réglage à retenir. Le
  rayon de 0,2 m vaut pour tout le projet (T étalonné sur E0, campagnes), et caler r ou τ
  sur l'anneau ajusterait le modèle sur la courbe qui sert à le valider. Surtout, le
  5,4 pers/m² de Weidmann est la densité où l'on cesse de marcher en conditions normales,
  pas celle où les corps se touchent : il rapporte des débits bien plus élevés quand on
  presse les sujets (p. 64). Ce qui manque au modèle est un espace personnel, que des
  disques plus gros ne représentent pas. À écrire comme limite : **aux fortes densités, le
  modèle va trop vite parce que ses agents ne s'arrêtent qu'au contact.**

## Pour une activation : τ étalonné sur E0 (19 novembre)

Mesures pour la décision de #158, commit `275fc3d` sans modification locale. Scripts et
bilans : [`mesures/navigation-2026-11-19/`](mesures/navigation-2026-11-19/).

**E0.** Même protocole que pour T : τ, le temps d'anticipation de la seconde heuristique,
est choisi sur N = 60, puis le critère du § 4 des
[critères d'acceptation](criteres-acceptation.md) (écart moyen absolu de J_s à Seyfried
≤ 10 %, 10 graines) se juge sur N = 40 et N = 20. 600 simulations (`e0-tau.py`).

| τ (s) | N = 60 (étalonnage) | N = 40 | N = 20 | Non-écoulements |
|---|---|---|---|---|
| 0,15 | 6,3 % | 8,7 % | 8,5 % | 1/150 |
| **0,20** | **2,9 %** | **7,5 %** | **9,9 %** | 1/150 |
| 0,25 | 7,1 % | 8,4 % | 12,9 % | 0/150 |
| 0,30 | 11,3 % | 11,9 % | 15,8 % | 2/150 |
| *T = 0,35 s, référence (#141)* | | *5,7 %* | *7,3 %* | |

À τ = 0,20 s, la navigation valide E0, un peu moins bien que T : à N = 20, elle est juste
sous le seuil.

**Piscine à τ = 0,20 s**, graines 1 à 10 (`piscine-tau.py`) : 12 % des positions de plage
contre le bord du bassin (93 % dans la référence) ; t50 = 28,1 s et t100 = 44,3 s, soit
−3,3 et −7,0 s (10/10) ; débit à la porte 2,69 pers/(m·s) au lieu de 2,28. Mouillé − sec :
Δt50 = +0,04 ± 0,59 s, Δt100 = −0,02 ± 0,40 s, rien de détecté. Comme dans la référence
(Δt50 = −0,01 ± 0,07 s), le mouillé ne change presque rien. Les temps absolus changent
d'environ 10 %, pas la conclusion.

**Le plafond d'adhérence du mouillé sert-il ?** Le mouillé ne diffère du sec que par a_max
(3,3 contre 5,9 m/s²). On a relevé à chaque pas l'accélération voulue |u − v|/τ des
agents sur la bande mouillée, graines 1 à 10 (`adherence.py`, qui ne change pas les
trajectoires : mêmes t50).

| | Référence | Navigation (τ = 0,5 s) |
|---|---|---|
| Temps passé sur la bande mouillée, par baigneur | 11,5 s | 8,1 s |
| Pas freinés par l'adhérence (accélération voulue > 3,3 m/s²) | 0,54 % (≈ 6 pas) | 1,05 % (≈ 9 pas) |
| Pas où même le sec freinerait (> 5,9 m/s²) | 0 % | 0 % |

Dans les deux modèles, l'adhérence ne freine qu'environ un dixième de seconde par
baigneur, surtout au redémarrage au pied de l'échelle (passer de 0 à 2 m/s en 0,5 s
demande 4 m/s²). La file indienne ne masque donc pas l'effet du mouillé : c'est le modèle
du mouillé, par la seule adhérence, qui agit peu.

### Les deux conditions de Lenny (#158)

Mesures demandées dans #158 avant d'adopter la navigation comme référence. Scripts écrits
avant le calcul (question et critère dans leur docstring), bilans :
[`mesures/navigation-2026-11-24/`](mesures/navigation-2026-11-24/). Commit `ec738e7`,
sans modification locale ; il a été rebasé ensuite sur dev sans changement de `src/` ni
d'`experiments/` (même empreinte des sources).

**1. L'anneau à τ = 0,20 s** (`anneau-tau020.py`, même protocole que ci-dessus, graines 1
à 10, 80 min). Écart de la vitesse à Weidmann :

| ρ (pers/m²) | 0,25 | 0,50 | 0,99 | 1,50 | 2,00 | 2,49 | 3,00 | 3,50 | 4,01 |
|---|---|---|---|---|---|---|---|---|---|
| v navigation, τ = 0,20 s (m/s) | 1,28 | 1,27 | 1,23 | 1,18 | 1,11 | 1,02 | 0,84 | 0,64 | 0,48 |
| écart, τ = 0,20 s | −4 % | −2 % | +16 % | +47 % | +84 % | +124 % | +152 % | +172 % | +206 % |
| écart, τ = 0,5 s | −10 % | −10 % | +4 % | +23 % | +37 % | +42 % | +47 % | +53 % | +67 % |
| écart, référence T | 0 % | +3 % | +26 % | +66 % | +121 % | +28 % | +30 % | +33 % | +29 % |

Écart-type entre graines de 0,043 m/s au plus, dérive entre les deux moitiés de la fenêtre
de 6,1 % au plus, recouvrement ≤ 10⁻⁶ m. **Le τ qui valide E0 fait aller la foule 2 à 3 fois
trop vite au-delà de 2,5 pers/m²**, bien plus que la référence (+30 %). La navigation ne
fait mieux que T qu'entre 1 et 2 pers/m², où elle ralentit progressivement au lieu de
garder v0. E0 et Weidmann tirent τ en sens opposé.

**2. L'effet du mouillé tient-il à Δt/2 ?** (`frottement-dt.py`). Avec le frottement de
marche de #201 (RCOF = 0,20 retranché de a_max sur le mouillé et le sec), l'effet du mouillé
devient détectable sur la référence ; la question est de savoir s'il survit à un pas de
temps deux fois plus fin. Mouillé − sec (s), graines 1 à 10 :

| Modèle | Grandeur | Δt | Δt/2 | Δt/2 − Δt (apparié) |
|---|---|---|---|---|
| Référence T | t50 | +0,469 ± 0,362 (9/10) | +0,474 ± 0,370 (9/10) | +0,004 ± 0,081 |
| Référence T | t90 | +0,987 ± 0,681 (9/10) | +1,015 ± 0,608 (10/10) | +0,028 ± 0,134 |
| Référence T | t100 | +0,717 ± 0,806 (9/10) | +0,763 ± 0,720 (9/10) | +0,047 ± 0,167 |
| Navigation τ = 0,20 s | t50 | +0,759 ± 0,646 (9/10) | +0,499 ± 0,470 (9/10) | −0,260 ± 0,521 |
| Navigation τ = 0,20 s | t90 | +1,657 ± 1,290 (9/10) | +0,540 ± 0,729 (9/10) | −1,118 ± 1,170 |
| Navigation τ = 0,20 s | t100 | +0,717 ± 0,889 (10/10) | −0,011 ± 1,050 (7/10) | −0,728 ± 1,688 |

La première ligne redonne les chiffres du prototype de #201 (+0,469 et +0,474 s) : la
reproduction par la seule configuration est fidèle. t90 se lit dans le `.json` ; le `.txt`
n'imprime que t50 et t100, les deux grandeurs du critère. Violation maximale 7,1 × 10⁻¹⁵ m.

Selon le critère fixé avant le calcul (§ 3, critère 2 des
[critères d'acceptation](criteres-acceptation.md)), **la référence est robuste au pas de
temps sur les trois grandeurs ; la navigation ne l'est pas sur t100** (7/10 à Δt/2), et son
effet sur t90 est divisé par trois. Avec la navigation, une partie de l'effet du mouillé
mesuré à Δt dépend donc du pas de temps. Hypothèse, non vérifiée : la direction rechoisie à
chaque pas, par crans de 5°, donne des à-coups qui butent sur le plafond d'adhérence, et
leur fréquence dépend de Δt. Les temps d'évacuation eux-mêmes ne dépendent pas de Δt (§
« Ce qu'on en retient », point 3) : seul l'écart mouillé − sec est fragile.

**Conséquence pour #158** : aucune des deux conditions n'est remplie. Ces mesures vont dans
le sens de la proposition de Lenny : garder T comme référence, et la navigation à
τ = 0,20 s comme test de robustesse, présentée au § 6 avec ces deux limites.

## Ce qu'on en retient

1. **La file indienne disparaît.** Les baigneurs s'écartent du bord du bassin (9 % contre
   93 %) et le flux s'élargit d'un facteur treize. Visuellement, les deux lignes parfaites
   deviennent des flux diffus, puis une foule qui se resserre devant la porte.
2. **L'évacuation est plus rapide**, de 4 s sur t100 (10 graines sur 10), et la porte
   écoule plus : 2,46 contre 2,28 pers/(m·s). **Le gain vient des heuristiques, pas de la
   dispersion des vitesses** : sans dispersion, t100 avance de 6,3 s (10/10) ; la
   dispersion en reprend 2,2 s (10/10) et abaisse le débit de 0,30 pers/(m·s). La
   file indienne disparaît aussi sans dispersion (9,4 % contre le bord). Explication
   possible du gain, non mesurée : en utilisant la largeur de la plage, les baigneurs
   arrivent à la porte de front plutôt qu'en deux files. Celle du ralentissement dû à la
   dispersion, non mesurée non plus : les plus lents imposent leur cadence aux échelles
   et à la porte, comme le suggère E0 ci-dessus.
3. **Ni le pas de temps ni le choix fig. 2 / fig. 3 de l'article ne changent rien de
   décelable** : moins que l'écart-type entre graines sur t50, t100 et le débit.
4. **Le sol mouillé ralentirait peut-être la fin de l'évacuation**, mais ce n'est pas une
   détection : Δt100 = +0,84 ± 1,10 s sur 8 graines sur 10, p = 0,04 par permutation
   mais p = 0,11 au test de signe du § 3 des critères, qui demande au plus une graine
   contraire sur dix. Rien sur t50 (7/10, p = 0,34) ni sur le débit (7/10, p = 0,34).
   C'est de plus une comparaison exploratoire, hors de la comparaison principale (E1/E2
   sur la référence) : une indication, à confirmer sur dix nouvelles graines (11 à 20)
   avant d'en parler dans le rapport.
5. **La validation est mitigée.** La forme du ralentissement avec la densité se rapproche
   de Weidmann, ce que la référence ne fait pas. Mais au goulot, les valeurs de l'article
   donnent un débit de 16 à 38 % sous Seyfried, que la référence atteint par étalonnage.
   Activer la navigation, c'est choisir des trajectoires réalistes au prix de cet écart,
   ou régler τ sur E0 comme on a réglé T. Sur l'anneau, l'excès de vitesse au-delà de
   1,5 pers/m² vient surtout de la densité d'arrêt des disques (7,2 contre 5,4 pers/m²) :
   les agents ne s'arrêtent qu'au contact.

## Limites

- **Pas d'espace personnel** : un agent ne s'arrête qu'au contact. Aux fortes densités,
  la foule va donc trop vite (anneau : +23 à +67 % au-delà de 1,5 pers/m² à τ = 0,5 s,
  +47 à +206 % à τ = 0,20 s), et des disques plus gros ne corrigent pas le bon mécanisme
  (diagnostic ci-dessus).
- **L'effet du mouillé n'est pas robuste au pas de temps** avec la navigation (Δt100 de
  +0,72 à −0,01 s quand Δt est divisé par deux), alors qu'il l'est avec la référence.
- **E0 avec la navigation est sous Seyfried**, et N = 60 à b = 0,8 m bouche encore 4 à
  6 fois sur 10. Le même modèle donne 2,46 pers/(m·s) à la porte de la piscine et 1,48
  dans E0 à b = 1,2 m : la porte est une ouverture dans un mur, E0 un couloir de 2,8 m,
  et la foule n'y arrive pas de la même façon ; les deux ne se comparent pas directement.
- **Coût de calcul** : environ 2,5 fois plus long par évacuation, à cause des distances
  libres calculées dans 31 directions pour chaque baigneur de la plage.
- **Les nageurs** ne naviguent pas : dans l'eau, le guidage reste celui du champ, et la
  régulation T y reste active quand `temps_espacement` est fixé. Leur vitesse souhaitée
  est pourtant dispersée (facteur individuel).
- **Les agents en franchissement sont invisibles** pour les heuristiques : seuls les
  agents de la plage sont passés à `vitesses_souhaitees`. Un baigneur qui monte une
  échelle ou passe un rebord n'est vu par personne sur la plage ; seule la projection
  empêche qu'on le traverse, sans qu'un voisin l'anticipe.
- **La distance gardée au bord du bassin** n'est pas imposée. Elle vient de l'évitement des
  autres et de la dispersion des vitesses ; aucune source ne la fixe ici.
- **L'anneau** part des voies concentriques de #149 : #167 doit vérifier, pour la
  référence, l'effet de ce départ ordonné. Avec la navigation, les agents quittent leur
  voie de départ pour longer le mur intérieur (ci-dessus), mais l'effet du départ n'est
  pas mesuré non plus.
