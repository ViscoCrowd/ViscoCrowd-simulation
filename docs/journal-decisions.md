# Journal des décisions

Les décisions de modélisation un peu structurantes, les options écartées, et les pistes qui
n'ont pas abouti.

> Les consignes précisent que les pistes explorées sans succès **font partie du travail et que
> leur analyse est valorisée**. Une impasse documentée en octobre est une section de rapport en
> décembre ; la même impasse oubliée n'est rien.

Format : une entrée par décision, la plus récente en haut.

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
