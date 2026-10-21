# Journal des décisions

Les décisions de modélisation un peu structurantes, les options écartées, et les pistes qui
n'ont pas abouti.

> Les consignes précisent que les pistes explorées sans succès **font partie du travail et que
> leur analyse est valorisée**. Une impasse documentée en octobre est une section de rapport en
> décembre ; la même impasse oubliée n'est rien.

Format : une entrée par décision, la plus récente en haut.

---

## 2026-10-21 — Imposer l'obstacle dans la projection et l'intégrer au banc de couloir (G2/G5)

**Décision.** Un obstacle rectangulaire devient une contrainte du domaine, comme une paroi :
`ObstacleRectangle.repousser` ramène tout centre qui le chevauche au bord du rectangle
gonflé d'un rayon, aux coins arrondis. L'extérieur d'un rectangle n'est pas convexe, mais
cette projection est explicite et exacte. `Couloir` projette les parois puis les obstacles ;
ce second pas reste exact pour les parois tant qu'un diamètre d'agent sépare chaque obstacle
des parois et des autres obstacles, ce que le scénario vérifie avant le calcul.

Le guidage seul ne suffisait pas : mesuré sur le banc, des agents **touchent** le pilier
(distance au pilier égale au rayon à 10⁻¹⁶ m près), poussés par leurs voisins. Sans la
contrainte, rien n'aurait empêché l'un d'eux d'y entrer.

**Configuration.** Le scénario `couloir` déclare désormais `guidage` (`aval` ou `eikonal`),
`pas_guidage` et `obstacles` dans son YAML, sans valeur implicite. Des obstacles exigent le
guidage eikonal. Au-delà de la section de sortie, où le champ est nul, les agents reprennent
la direction (1, 0) pour continuer en aval comme dans le banc G1.

**Compatibilité de relecture.** Les anciennes archives v1 sans les trois champs
de guidage restent affichables comme banc analytique sans obstacle. Cette adaptation
est limitée à la lecture, ne modifie pas les métadonnées et ne masque pas un champ
manquant dans une archive moderne. Les nouveaux YAML restent explicites.
Les méthodes publiques de projection et de violation d'obstacle refusent aussi
les rayons non finis ou non positifs, même si la population est vide.

**Mesures** (`experiments/couloir_obstacle.yaml`, pilier de 1 × 1 m au milieu de la bande
mouillée, Δt = 0,01 s, 16 s). 24 agents sortis sur 24, 12 de chaque côté ; recouvrement
maximal 9,9998·10⁻⁷ m pour une tolérance de 10⁻⁶ m ; violation des parois et du pilier
5,6·10⁻¹⁷ m ; aucune non-convergence (87 balayages au plus) ; premier et dernier passage
à 7,177 et 9,380 s, contre 7,225 et 9,228 s sans pilier. Sans obstacle, le guidage eikonal
redonne la trajectoire du guidage analytique **bit à bit**. Calcul : 1,1 s.

**Portée.** Valeurs illustratives, comme le banc sans obstacle. Le partage 12/12 vient de la
symétrie du pilier et de la population ; il ne mesure encore aucun arbitrage entre milieux.

---

## 2026-10-21 — Calculer le guidage par Fast Marching et contourner un obstacle (G2)

**Décision d'implémentation.** `model/eikonal.py` résout `|∇φ| = 1/F` par Fast Marching
du premier ordre sur une grille régulière, écrit par le groupe (spec § 2.6). La vitesse `F`
est la vitesse souhaitée du milieu sous chaque nœud ; un obstacle est un ensemble de nœuds
où `F = 0`, retirés jusqu'à une marge égale au rayon des agents pour que le champ guide les
centres sans que les disques touchent l'obstacle. La direction est `−∇φ/|∇φ|`, prise par les
mêmes différences amont que le schéma puis interpolée bilinéairement aux positions.

**Options écartées.** Un gradient centré mélange les deux côtés d'une crête, et donne un
vecteur nul derrière un obstacle symétrique : l'agent pousse alors contre la face. Le
gradient amont choisit toujours le voisin d'indice inférieur en cas d'égalité, ce qui brise
la symétrie de façon déterministe. Un schéma d'ordre 2 n'a pas été retenu : l'ordre 1 est
exact sur le cas couloir et suffit aux détours mesurés ; il reste une amélioration possible.

**Mesures** (`tests/test_eikonal.py`). Couloir sec/mouillé/sec : `φ` égale l'intégrale de
`1/F` à 10⁻¹³ près et la direction reproduit exactement `direction_aval` de G1. Source
ponctuelle : erreur maximale 0,103 ; 0,062 ; 0,037 s pour h = 0,1 ; 0,05 ; 0,025 m, direction
à 3,6° au pire au pas le plus fin. Ombre d'un obstacle de 1 × 1,5 m : erreur maximale 0,131 ;
0,090 ; 0,050 s sur environ 11 s de parcours. Le schéma surestime `φ` (écart minimal mesuré
−3·10⁻¹⁴ s). Un agent de rayon 0,2 m guidé à 1,5 m/s contourne l'obstacle sans le toucher
(marge minimale 1,9 cm), y compris depuis l'axe de symétrie, et arrive 0,34 s après le temps
du contour à vitesse constante, soit environ `τ` = 0,3 s de mise en vitesse. Un groupe de
12 agents en contact contourne aussi l'obstacle, avec 6,7 cm de marge et aucune
non-convergence. Coût : 0,16 s pour les 99 086 nœuds de l'emprise de la piscine à h = 0,1 m.

**Limites.** Dans `model/eikonal.py`, l'obstacle n'est qu'une zone que le guidage évite ;
le banc de couloir l'ajoute aussi à la projection (entrée suivante). Le champ est statique ;
il ne tient compte ni de la densité ni de la capacité des franchissements (P3). Un agent hors
de la grille reçoit la direction du bord le plus proche ; un agent au cœur de la sortie reçoit
une direction nulle. La géométrie piscine (C6) reste à raccorder.

**Correction après revue de la PR #43, le 21 octobre (Lenny).** Le départage amont aux
nœuds ne suffisait pas : l'interpolation pouvait moyenner deux directions opposées et
immobiliser un agent accessible. Sur une grille de pas 1 m, avec des sorties en x = 0 et
x = 4 m, le point (2,5 ; 0,5) recevait une direction nulle. Un agent au repos en
(4,5 ; 0,125) devant l'obstacle [5,6] × [-0,5,0,5], avec h = 0,25 m et une marge de
0,25 m, restait également immobile pendant les 10 s du test.

Lorsque deux gradients non nuls qui contribuent à l'interpolation forment un angle
obtus (produit scalaire normalisé < −10⁻¹²), le guidage choisit maintenant le gradient
du nœud contributeur de plus petit temps de parcours. Les égalités sont départagées
dans l'ordre fixe des quatre nœuds. Les poids nuls sont exclus : un nœud de sortie ne
récupère donc pas artificiellement la direction de ses voisins. Ailleurs, l'interpolation
bilinéaire est conservée. Ce choix local évite l'annulation de branches opposées ; ce
n'est pas une garantie d'optimalité du chemin continu ni une contrainte dure d'obstacle.

Les régressions couvrent deux sorties selon chacun des axes, les perturbations de
position de ±10⁻¹⁰ m autour du point d'annulation et le détour d'un agent initialement
au repos entre les nœuds. Le test du groupe mesure aussi toutes les distances entre
paires, indépendamment des diagnostics de la projection : recouvrement maximal
9,99189 × 10⁻⁷ m, marge à l'obstacle 6,689 cm, 12/12 arrivés. L'évaluation des directions
de 500 agents coûte environ 0,21 ms par appel sur le poste de revue (médiane de trois
séries de 1 000 appels, Python 3.14.4) ; les temps dépendent de l'environnement.

---

## 2026-10-21 — Relire le couloir à partir des archives

**Réalisation (PR #37).** La vue du couloir lit les positions, rayons et instants du
NPZ sans appeler le simulateur. Lire/Pause et le curseur servent à examiner un contact
ou une transition ; les exports GIF/PNG permettent de partager la démonstration sans
environnement graphique. Le compteur reprend l'observable de passage et ne prétend
pas mesurer une évacuation définitive. Les paramètres affichés restent illustratifs.

L'échantillonnage de la lecture utilise le dernier instant archivé inférieur ou égal
au temps demandé, même pour des archives irrégulières ; le dernier instant est inclus
dans le GIF. La résolution du GIF est fixée explicitement : un test a révélé sa dépendance
aux réglages globaux des figures scientifiques. Les contrôles de lecture sont testés
sans fenêtre et les exports inspectés ; la fenêtre native reste à essayer sur les postes.

---

## 2026-10-21 — Coupler la foule guidée aux milieux et à l'exclusion

**Réalisation (suivi #34).** Le banc `experiments/couloir.yaml` initialise une grille
de disques perturbée par une graine explicite, avec une marge garantissant son admissibilité.
Le guidage vers l'aval, la carte par bandes et le pas libre des milieux alimentent ensuite
l'exclusion existante en mode strict. Aucun paramètre de scénario n'est implicite.

On exige Δt ≤ min(τ) pour une relaxation monotone sans saturation, puis un déplacement
souhaité et mesuré par pas ≤ rayon/5, comme garde-fou pratique contre les pas trop grands.
La convergence est testée séparément : la trajectoire d'un agent en milieu uniforme
approche à l'ordre 1 la solution `x(t) = x₀ + s [t − τ (1 − exp(−t/τ))]` sans saturation.

**Mesures du démonstrateur.** 24 agents, Δt = 0,01 s, 14 s simulées : 24 passages distincts
de la section x = 12 m, entre 7,225 et 9,228 s ; recouvrement maximal 9,99457·10⁻⁷ m,
aucune non-convergence et aucune violation de paroi. Des contacts ont effectivement lieu.
Les différences de vitesse et d'adhérence entre bandes sont illustratives et ne permettent
pas d'attribuer séparément un effet à l'adhérence ; ce n'est pas une campagne E0–E4.

---

## 2026-10-21 — Valider le guidage sur un couloir prolongé en aval

**Décision d'implémentation (G1, suivi #34).** Le premier banc guidé est un couloir
rectiligne sans obstacle : paroi amont en x = 0, parois latérales en y = ±largeur/2,
section de sortie en x = longueur. Les parois latérales et le mouvement se prolongent
en aval. Les agents ne sont pas retirés à la sortie : on peut mesurer un passage avec
l'observable existante sans préjuger de l'état absorbant du futur scénario (#11).

La direction est (1, 0). C'est la direction analytique du champ de temps de parcours
quand la vitesse positive ne dépend que de x. Ce cas ne remplace pas le calcul eikonal
avec obstacles de G2. La carte par bandes attribue une frontière à la zone de droite ;
le milieu sous le centre est lu au début du pas, conformément à #30. La géométrie
fournit aussi le segment de mesure et sera reprise par la relecture graphique.

**Portée.** Cette brique prépare le test couplé guidage/milieux/exclusion. Elle ne fixe
ni la géométrie commune de la piscine ni les paramètres physiques de C6 ; les valeurs
du banc devront être explicites dans son YAML, avec des tests de convergence séparés.

---

## 2026-10-21 — Livrer la chaîne YAML et trajectoires persistées (C7)

**Réalisation.** La décision de séparation calcul/observables du 6 octobre est désormais
implémentée pour les bancs `bille_boite` et `tassement` (PR #32, issue #31).
L'archive NPZ v1 conserve les tableaux SI et des métadonnées JSON, avec tous les paramètres
effectifs, la graine et les versions Python/NumPy/ViscoCrowd. Le choix de tableaux numériques
et de JSON permet une relecture sans pickle. Un résultat non convergé n'est pas publié ;
les fichiers existants ne sont pas écrasés.

**Validation.** Deux exécutions du tassement (36 agents, Δt = 0,002 s, durée 2,5 s, graine 1)
produisent exactement les mêmes tableaux : 1 251 instants, recouvrement maximal
9,9998254·10⁻⁷ m, aucune non-convergence et aucune violation des parois. Les tests vérifient
aussi le rejeu à partir des paramètres archivés, la relecture et l'énergie calculée hors ligne.

**Limites.** Même environnement requis pour l'égalité exacte ; population fixe et historique
en mémoire. Le format ne constitue ni une reprise de calcul ni un état d'évacuation. Le futur
scénario piscine et les campagnes devront utiliser cette chaîne. Les bancs de production des
figures existantes restent inchangés ; aucune nouvelle figure du rapport n'est ajoutée.

---

## 2026-10-21 — Assembler guidage et milieux au début du pas

**Décision d'implémentation (PR #30, suivi #26).** Le guidage fournit une direction
unitaire ou exactement nulle ; la carte fournit le milieu sous chaque agent. L'assemblage
forme `U = facteur_vitesse × vitesse_du_milieu × direction` puis applique l'accélération
bornée avant la projection. Une direction non nulle de norme différente de 1 (à 10⁻⁹ près)
est rejetée : accepter un gradient trop court modifierait silencieusement la vitesse voulue.

Le milieu est évalué en `xⁿ`, au début du pas explicite. Un changement de sol s'applique
donc au pas suivant. Découper le pas exactement à chaque frontière demanderait un contrat
géométrique supplémentaire ; ce n'est pas retenu dans cet assemblage. Le test de freinage
sec → mouillé mesure l'erreur en raffinant Δt, car le contraste d'adhérence l'amplifie.
Pour les valeurs illustratives du test, le point d'arrêt analytique est 0,540 m et l'erreur
reste sous `(8 m/s) × Δt` pour Δt = 2·10⁻³, 10⁻³ et 5·10⁻⁴ s.

**Portée.** Les valeurs de test ne sont pas une calibration. La géométrie, le vrai guidage
et les valeurs physiques restent suivis en C6/G1/G2 ; G3 n'est pas terminé. La classe
`model.milieu.ParametresMilieu` exige des valeurs complètes et valides ; la classe d'affichage
`ui.parametres.ParametresMilieu` accepte encore des champs non renseignés pour la maquette.
Leur raccordement reste à faire avec C6, sans rendre facultatifs les paramètres du moteur.
Cette entrée décrit le code intégré et ne présume pas une validation collective du modèle.

---

## 2026-10-19 — Donner une échelle commune au plan et éloigner la sortie

**Décision.** Remplacer les proportions libres du croquis par un dessin où une unité vaut
un mètre. `DimensionsPlan` rassemble les dimensions provisoires : bassin 25 × 12,5 m,
plages donnant une emprise de 48 × 20,5 m, échelle de 0,50 × 1 m, sortie de 1,20 m et rayon
humain de référence de 0,20 m. Une barre de 5 m et un disque de diamètre 0,40 m, placé
hors de l'emprise dans la légende, partagent les coordonnées du plan. Le panneau reprend
le rayon de référence, le nombre d'échelles et la largeur de sortie effectivement dessinés.

**Pourquoi.** Les symboles d'échelle et de sortie étaient trop grands par rapport aux
personnes envisagées. Une unité commune rend leurs proportions comparables, y compris
après un zoom ou un redimensionnement de la fenêtre.
Le bassin de 25 × 12,5 m reprend un format réel de piscine municipale, présent notamment
à La Plaine et Mourlon selon la [Ville de Paris](https://mairie15.paris.fr/pages/equipements-sportifs-13195).
Les plages conservent 3 m à gauche, 4 m en haut et en bas ; la distance du bord droit du
bassin au mur de sortie passe de 7 à 20 m. Elle réserve de la place au futur parcours
mouillé puis sec, y compris pour des personnes franchissant le rebord au lieu de l'échelle.
Cette longueur reste réglable avec `plage_sortie` et l'emprise totale en découle.
Une cote sur le plan rend cette distance lisible. Elle ne préjuge pas du temps d'évacuation.

Le panneau de paramètres est replié par défaut et accessible avec un bouton dans l'en-tête.
La vue récupère ainsi sa largeur sans réduire le bassin ni déformer les distances.
Un clic est retenu plutôt que le survol pour pouvoir laisser les valeurs affichées.
La bascule conserve les limites de zoom ; `afficher_parametres=True` ouvre directement
le panneau, notamment pour les exports. Aucun paramètre physique n'est modifié par ce bouton.

**Portée.** Ce sont des dimensions de travail pour l'interface, pas une calibration validée
par le groupe. La géométrie physique commune (C6) reste à définir et à raccorder au moteur.
Le plan reste sans population ni mouvement ; le cadre extérieur reste continu derrière
le symbole de sortie, conformément au croquis. La séparation entre sol mouillé et sol sec
et leurs effets sur les trajectoires ne sont pas encore implémentés dans cet aperçu.

---

## 2026-10-13 — Consigner le cadrage et la validation collective du jalon 2

**Cadrage.** Le statut du sujet, la trace disponible et les réponses encore manquantes sont
centralisés dans la [fiche de cadrage](validation-sujet.md#trace-de-validation).
Le complément de trace et les réponses de l'enseignant sont suivis dans
l'[issue #19](https://github.com/ViscoCrowd/ViscoCrowd-simulation/issues/19), cible au 19 octobre ;
elles conditionnent la mesure de densité et l'extension aux chutes, pas le jalon 3.

**Décisions collectives.** Les trois membres ont accepté Jacobi vectorisé et l'extrapolation
de Nesterov retardée, déclenchée après 80 balayages. Jacobi est retenu pour les meilleures
performances d'exécution observées avec NumPy, malgré davantage de balayages que Gauss-Seidel ;
cette justification concerne l'implémentation mesurée. Le rang 80 conserve le compromis mesuré
entre performance et respect du comportement de choc mou. Les performances pourront être
réexaminées pendant les campagnes de simulation si nécessaire.

**Portée scientifique.** L'algorithme recherche une configuration admissible à la tolérance
près, sans garantie générale d'optimalité euclidienne. Cela n'exclut pas un résultat exact dans
certains cas, notamment pour une paire isolée. Les limites de contacts multiples suivies dans
l'[issue #10](https://github.com/ViscoCrowd/ViscoCrowd-simulation/issues/10) restent à traiter.

**Conséquence.** Le socle du jalon 0 est livré, sa trace de validation reste à compléter.
Les jalons 1 et 2 sont validés avec les limites documentées ; les jalons 3 à 6 restent à
développer ou à finaliser. Les corrections [#16](https://github.com/ViscoCrowd/ViscoCrowd-simulation/issues/16)
et [#17](https://github.com/ViscoCrowd/ViscoCrowd-simulation/issues/17) sont requises avant le
jalon 3. Cette confirmation actualise le statut « à faire valider » de l'entrée du 12 octobre.
L'[issue #13](https://github.com/ViscoCrowd/ViscoCrowd-simulation/issues/13) reste ouverte jusqu'à
la fusion des mises à jour documentaires et la vérification des critères restants, dont la
capacité de chacun à réexpliquer les choix et les mesures.

---

## 2026-10-12 — Projection d'exclusion : Jacobi, pondération symétrique, extrapolation retardée

**Décision.** La projection sur « pas de recouvrement » (`geometry/projection.py`) traite toutes
les paires **en même temps** (Jacobi vectorisé), chaque correction vaut **exactement** le
recouvrement, les corrections d'une paire sont pondérées par `1/max(c_i, c_j)` où `c_k` est le
nombre de contacts de l'agent `k`, et l'extrapolation de Nesterov ne s'allume **qu'au-delà de
80 balayages**, avec une rampe repartant de zéro.

**Écart avec la spec.** La spec § 2.5 annonçait du Gauss-Seidel projeté. On a préféré Jacobi, qui
se vectorise en NumPy (Gauss-Seidel impose une boucle Python paire par paire). Mesuré : Jacobi
demande **plus de balayages** (35 à 125 contre 13 à 19 de 12 à 600 agents) mais reste **environ
deux fois plus rapide** en temps réel (1,46 ms contre 2,66 ms à 12 agents ; 7,87 ms contre
16,08 ms à 600). Un portage de Gauss-Seidel en code compilé inverserait la conclusion.

**Ce qui est garanti, et ce qui ne l'est pas.** Point important pour le rapport : le résultat
n'est **pas** la projection euclidienne de `x_libre` sur K, c'est-à-dire l'argmin de
`|x − x_libre|`. Rien dans l'algorithme ne minimise le déplacement, et aucun balayage ne peut
rapprocher deux disques qu'un précédent a trop écartés, puisque les corrections ne font
qu'écarter. Comparaison avec Gauss-Seidel, pris comme oracle de test :

| Configuration | ‖ΔX‖ Jacobi | ‖ΔX‖ Gauss-Seidel | Écart des solutions |
|---|---|---|---|
| 3 disques alignés | 1,4141·10⁻² | 1,4141·10⁻² | 4,5·10⁻⁷ m |
| Triangle serré | **0,9999·10⁻²** | 1,1770·10⁻² | 2,0·10⁻³ m |
| Amas de 12 | 7,5924·10⁻² | **7,5044·10⁻²** | 6,1·10⁻³ m |
| Amas de 100 | 1,2109·10⁻¹ | **1,1924·10⁻¹** | 1,4·10⁻² m |

Aucune des deux ne domine : sur le triangle serré, c'est Jacobi qui déplace le moins. Donc aucune
n'est le minimiseur. Le rapport doit écrire **« configuration admissible obtenue par projections
successives »**, et non « projection de Gauss-Seidel » ni « projection euclidienne sur K ».
Un test (`TestComparaisonGaussSeidel`) échouera si une méthode se met à dominer l'autre partout,
ce qui serait l'indice qu'elle approche le minimiseur.

**Ce qui n'a pas marché, et ce qu'on en a tiré.**

- *Jacobi simple* : un tas posé sur le sol reçoit à chaque pas une poussée de gravité de
  g·Δt² ≈ 4·10⁻⁶ m, et l'information « le sol retient tout » ne remonte que d'un contact par
  balayage. Pour ramener un tas de 64 disques sous 10⁻⁶ m, il fallait **642 à plus de 3000
  balayages** ; **716 projections sur 1500 échouaient** sur le tas de 36 disques. L'accélération
  n'est donc pas un confort, elle conditionne l'usage de la méthode.
- *Sur-relaxation* (corriger de 1,3 × le recouvrement) : plus rapide, **mais refusée**. Elle
  sépare les disques au-delà du contact, donc la vitesse relue v = Δx/Δt contient un rebond
  artificiel : le choc cesse d'être mou. Deux disques qui se rencontrent finissaient à 0,56 m au
  lieu de 0,20 m.
- *Moyenne des corrections par agent* (première version) : **abandonnée**, elle ne conserve pas
  le centre de gravité. Diviser les corrections reçues par un agent par son nombre de contacts
  n'est pas symétrique en (i, j) : dès que deux voisins n'ont pas le même nombre de contacts, les
  deux réactions d'une paire cessent d'être opposées et **la foule entière dérive** — 2,2·10⁻³ m
  mesurés sur un amas de 12 disques, 1,6·10⁻⁴ m sur 100, sans aucune force extérieure. La
  pondération par paire `1/max(c_i, c_j)` amortit autant mais reste symétrique : dérive ramenée à
  10⁻¹⁷ m, pour environ 30 % de balayages en plus.
- *Extrapolation de Nesterov allumée dès le premier balayage* : **corrigée**. Elle écarte elle
  aussi les disques au-delà du contact, et ce jeu est définitif. Un choc de trois disques alignés
  laissait **1,27·10⁻² m de jeu et 1,06·10⁻² m/s de vitesse résiduelle**, soit 1 % de la vitesse
  d'arrivée restituée. Le test du choc à **deux** disques ne pouvait pas le voir : une paire
  isolée est corrigée exactement en un balayage, l'artefact n'apparaît qu'à partir de trois corps.
  C'était le cas de figure signalé en relecture de la PR #6.
- *Garder la meilleure configuration admissible rencontrée* (celle qui minimise `|x − x_libre|`,
  en continuant quelques balayages après l'admissibilité) : **sans effet**, testé et écarté. Le
  premier itéré admissible est déjà celui qui a dépassé, et comme les corrections ne font
  qu'écarter, aucun itéré ultérieur n'est plus proche. Confirme que le dépassement est structurel
  et non un accident de convergence.
- *Retarder l'extrapolation sans faire repartir sa rampe* : **aggravait les chaînes longues**. Au
  déclenchement, β sautait directement à 80/83 = 0,96, donc le premier balayage extrapolé
  dépassait largement le contact : 7,7·10⁻⁴ de restitution sur une chaîne de 12 disques, contre
  2,4·10⁻⁵ sans aucun retard. Faire repartir la rampe de zéro (`k = rang − 80`) rend le gain
  monotone.

**Correctif retenu et son réglage.** Énergie cinétique résiduelle après un choc, rapportée à
l'énergie d'arrivée, pire cas sur des chaînes convergentes de 3 à 32 disques à quantité de
mouvement nulle, plus un triangle à trois contacts mutuels :

| Rang de déclenchement | Pire restitution | Balayages (tas de 64) | Temps |
|---|---|---|---|
| 0 (immédiat) | 1,0·10⁻³ | 91 | 5,3 s |
| 20 | 4,3·10⁻⁵ | 113 | — |
| 40 | 2,9·10⁻⁵ | 134 | 8,3 s |
| **80 (retenu)** | **9,0·10⁻⁷** | 168 | 11,7 s |

Au-delà de 80 le gain plafonne tandis que le budget d'itérations se consomme. Le budget par
défaut passe de 200 à 300 balayages pour garder de la marge sur les 186 que demande le tas.

**Mesures retenues** (36 disques de 0,07 m dans une boîte de 2 m, Δt = 2·10⁻³ s, graine 1) :
recouvrement résiduel ≤ 10⁻⁶ m (tolérance), parois à 0,0 m, 182 balayages au maximum,
0 projection non convergée sur 1500, énergie cinétique finale du tas 7,0·10⁻⁶ J, paires en
contact tangentes à 5,0·10⁻⁶ m près.

**Limites connues.**

- Près de l'empilement maximal (≳ 75 % de la surface), la projection n'atteint plus la tolérance
  dans le budget. Elle le **signale** : `non_convergences` et `recouvrement_max` sont publiés, le
  mode `strict=True` lève `ProjectionNonConvergee` dès le premier échec, et
  `verifier_convergence()` permet de contrôler après coup une simulation qu'on n'a pas voulu
  interrompre. Une trajectoire non convergée ne doit alimenter aucune figure du rapport.
- Les **chaînes longues** de contacts, seules extrapolées, gardent une restitution de l'ordre de
  10⁻⁶ de l'énergie d'arrivée.
- Trois contacts **mutuels** corrigés dans le même balayage laissent un défaut de **position**,
  indépendant de l'extrapolation : le triangle finit tangent à 1,7·10⁻³ m près, sans mouvement
  résiduel. Ce défaut sature et ne décroît **pas** avec Δt, contrairement au jeu du tas
  (5,0·10⁻⁶ m à Δt = 2·10⁻³ s contre 2,5·10⁻⁵ m à Δt = 4·10⁻³ s, soit une décroissance en Δt²).
- Le critère Δt de la spec (|v|·Δt ≪ r) reste à la charge du scénario : à Δt = 4·10⁻² s les
  disques traversent leurs voisins et la projection ne peut plus rien.
- L'invariant d'énergie du tassement est **peu sensible** : la dissipation d'ensemble (14 J) masque
  une création locale. C'est pourquoi `TestChocMultiple` mesure la restitution sur des chocs
  **isolés**, rapportée à l'énergie d'arrivée.

**À faire valider par le groupe.** L'écart de méthode avec la spec § 2.5 (traité par la PR #7), et
le choix du rang 80, qui échange 2,2 × le temps de projection contre 1 100 × moins de restitution.

---

## 2026-10-12 — Ajouter un aperçu graphique limité à l'interface

**Décision.** Créer une vue schématique de la piscine dans `ui/`, accessible par
`viscocrowd interface` ou `make interface`. Suivant le croquis fourni, elle représente
un bassin noir à contour blanc, une échelle à barreaux et une sortie à droite,
avec un repère d'orientation et un cadre extérieur continu. Le fond noir permettra
de distinguer les futurs agents blancs. Les sols ne sont pas encore différenciés.
Les coordonnées sont des choix de présentation, sans valeur de calibration physique.

Un panneau affiche les paramètres facultatifs de population, de géométrie, de milieu,
de franchissement et de calcul. Ils sont vides par défaut et transmis à la vue par
`ParametresAffichage`. Le chronomètre reçoit un temps simulé en secondes ; il reste
à zéro sans donnée du moteur. Il ne mesure pas le temps d'ouverture de la fenêtre.

**Pourquoi.** Visualiser rapidement la disposition avant de développer le scénario
de foule. Matplotlib est déjà une dépendance du projet et permet cet aperçu sans
introduire de bibliothèque supplémentaire. Le moteur et les scénarios restent indépendants
de l'affichage ; la commande ne lance aucune simulation.

**Périmètre.** Cette maquette étend le périmètre documentaire initial. Le pilotage
interactif du moteur, les déplacements d'agents et les mesures d'évacuation restent
hors de cette première interface. L'affichage graphique est chargé uniquement à la
demande pour conserver l'exécution des tests et des validations sans écran.

---

## 2026-10-06 — Le critère d'entraînement du sujet a un domaine de validité

**Contexte.** Le sujet d'introduction donne comme critère de validation n° 2 : « après quelques
secondes, tous les chocs ayant dissipé l'énergie disponible, la bille doit se stabiliser dans un
coin de la boîte et tourner solidairement avec elle ». Notre test écrit à partir de cet énoncé
échouait, avec un écart à la vitesse d'entraînement de 1,86 m·s⁻¹ au lieu des 0,05 attendus.

**Investigation.** Plutôt que de desserrer le seuil du test, nous avons mesuré l'écart en
fonction de la vitesse angulaire :

| ω (rad·s⁻¹) | ω²R/g | écart moyen (m·s⁻¹) | distance finale au centre (m) |
|---:|---:|---:|---:|
| 0 | 0,00 | 0,000 | 0,996 |
| 1 | 0,10 | 1,854 | 1,283 |
| 3 | 0,92 | 0,032 | 1,321 |
| 5 | 2,55 | 0,002 | 1,344 |
| 10 | 10,19 | 0,007 | 1,344 |
| 20 | 40,77 | 0,027 | 1,344 |

**Décision.** Le critère n'est pas faux : il vaut dans le régime où la force centrifuge domine la
gravité, soit ω²R ≳ g. Or les paramètres suggérés par le sujet (ω = 1 rad·s⁻¹, R = 1 m) donnent
ω²R/g = 0,10 — la gravité y domine d'un facteur dix, et la bille glisse le long des parois en
dégringolant de coin en coin au fil de la rotation, sans jamais se caler.

La transition est nette autour de ω²R/g ≈ 1. Dans le régime centrifuge, la distance finale au
centre vaut 1,3435 m, soit exactement √2 × (R − r) : la bille est bien au coin, au millimètre
près.

**Conséquence.** Deux tests distincts, un par régime, plutôt qu'un seuil affaibli. Le test en
régime gravitaire vérifie que la bille n'est *pas* entraînée, ce qui fixe une conclusion
physique au lieu d'une tolérance arbitraire.

**À retenir pour le rapport.** Bon exemple d'analyse critique d'un résultat de simulation : un
critère de validation a toujours un domaine de validité, et le délimiter fait partie de la
validation.

---

## 2026-10-06 — Projection sur convexe plutôt que forces sociales

**Options considérées.**

1. *Projection sur l'ensemble admissible* (Maury & Venel), dans le prolongement du cours.
2. *Modèle de forces sociales* (Helbing) : répulsion exponentielle et relaxation vers la vitesse
   désirée.
3. *Hybride* : forces pour le comportement, projection corrective en fin de pas.

**Décision : option 1.**

**Pourquoi.** Le modèle de forces sociales ne garantit pas la non-interpénétration : en panique,
les forces saturent et les agents se chevauchent. Il faudrait alors mesurer et justifier ce
recouvrement, alors que les consignes demandent précisément d'établir son absence. La projection
l'exclut **par construction**, ce qui transforme un critère d'évaluation en propriété acquise.

L'option 3 a été écartée par YAGNI : deux mécanismes concurrents rendent impossible d'attribuer
un effet observé à l'un plutôt qu'à l'autre, ce qui est exactement ce qu'une soutenance met à
l'épreuve.

---

## 2026-10-06 — Les trajectoires sont persistées, les observables calculés hors ligne

**Décision.** La boucle de simulation écrit les trajectoires sur disque ; les observables sont
calculés dans un second temps, à partir de ces fichiers.

**Pourquoi.** Un diagramme fondamental demande un balayage de paramètres sur plusieurs graines.
Si les observables étaient calculés au vol, ajouter une mesure ou corriger une définition de
densité imposerait de relancer toutes les simulations. Séparer les deux rend aussi
`observables/` testable sur des données synthétiques, sans faire tourner le moteur.

**Coût accepté.** De l'espace disque, et une étape de plus dans la chaîne de production des
figures.
