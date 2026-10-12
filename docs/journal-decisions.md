# Journal des décisions

Les décisions de modélisation un peu structurantes, les options écartées, et les pistes qui
n'ont pas abouti.

> Les consignes précisent que les pistes explorées sans succès **font partie du travail et que
> leur analyse est valorisée**. Une impasse documentée en octobre est une section de rapport en
> décembre ; la même impasse oubliée n'est rien.

Format : une entrée par décision, la plus récente en haut.

---

## 2026-10-12 — Projection d'exclusion : Jacobi accéléré, sans sur-relaxation

**Décision.** La projection sur « pas de recouvrement » (`geometry/projection.py`) traite toutes
les paires **en même temps** (Jacobi vectorisé, moyenne des corrections pour un agent à plusieurs
contacts), accélérée par une **extrapolation de Nesterov**, et chaque correction vaut **exactement**
le recouvrement.

**Écart avec la spec.** La spec § 2.5 annonçait du Gauss-Seidel projeté. On a préféré Jacobi, qui se
vectorise en NumPy (Gauss-Seidel impose une boucle Python paire par paire). Les deux itèrent vers le
même ensemble admissible, mais pas forcément vers le même point : à rediscuter si le rapport veut
affirmer « projection de Gauss-Seidel ».

**Ce qui n'a pas marché, et ce qu'on en a tiré.**

- *Jacobi simple* : un tas posé sur le sol reçoit à chaque pas une poussée de gravité de
  g·Δt² ≈ 4·10⁻⁶ m, et l'information « le sol retient tout » ne remonte que d'un contact par
  balayage. Pour ramener un tas de 64 disques sous 10⁻⁶ m, il fallait **642 à plus de 3000 balayages** (selon le
  tas mesuré) ; 76 à 88 % des projections n'aboutissaient pas dans un budget de 200.
- *Sur-relaxation* (corriger de 1,3 × le recouvrement) : plus rapide, **mais refusée**. Elle sépare
  les disques au-delà du contact, donc la vitesse relue v = Δx/Δt contient un rebond artificiel : le
  choc cesse d'être mou. Un test le détecte : deux disques qui se rencontrent finissent à 0,56 m au
  lieu de 0,20 m.
- *Extrapolation de Nesterov* (rang k, coefficient k/(k+3), sans extrapolation au premier
  balayage) : **≈ 100 balayages** pour le même tas, 0 projection non convergée sur 1500. Elle ne change
  que le chemin, pas la correction appliquée à une paire isolée, qui reste exacte en un balayage.

**Mesures retenues** (36 disques de 0,07 m dans une boîte de 2 m, Δt = 2·10⁻³ s) : recouvrement
résiduel ≤ 10⁻⁶ m (tolérance), parois à 0,0 m, 47 balayages au maximum, hauteur du tas stable à
1 cm près quand Δt est doublé.

**Limites connues.**

- Près de l'empilement maximal (≳ 75 % de la surface), la projection n'atteint plus la tolérance dans
  le budget : elle le **signale** (`non_convergences`, `recouvrement_max`) sans lever d'exception.
- Le critère Δt de la spec (|v|·Δt ≪ r) reste à la charge du scénario : à Δt = 4·10⁻² s les disques
  traversent leurs voisins et la projection ne peut plus rien.
- L'invariant d'énergie du tassement est **peu sensible** : il ne détecte pas la sur-relaxation ×1,3
  (c'est le test du choc à deux disques qui la voit). À renforcer.

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
