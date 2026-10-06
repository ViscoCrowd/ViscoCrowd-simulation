# Modèle de chute, de relevage et de contournement

**Addendum à la [spécification de conception](superpowers/specs/2026-10-06-viscocrowd-design.md)**
Statut : à valider par le groupe · 6 octobre 2026

---

## Pourquoi ce module change la nature du projet

La zone de carrelage mouillé était modélisée par une simple borne sur l'accélération disponible.
C'est correct, mais incomplet : sur un sol à faible adhérence, un piéton qui demande plus de
traction qu'il n'en dispose ne se contente pas d'accélérer moins — **il glisse et il tombe**.

Et une personne à terre n'est pas un agent ralenti : c'est un **obstacle**, qui réduit la section
utile du passage, que les autres doivent contourner, et qui peut en faire tomber d'autres. C'est
le mécanisme qui transforme une gêne locale en effondrement du débit.

Ce module est donc le chaînon qui relie physiquement la zone mouillée au goulot — c'est-à-dire
exactement ce que la problématique demande d'étudier. Sans lui, « l'inertie du carrelage
mouillé » reste une métaphore ; avec lui, elle a un mécanisme.

---

## 1. Déclenchement de la glissade

### Principe

La biomécanique du glissement repose sur le **coefficient de frottement requis** (RCOF, *required
coefficient of friction*) : la marche exige à chaque pas un rapport entre force tangentielle et
force normale. Si le sol ne peut pas le fournir, le pied part.

Nous transposons directement : l'agent glisse quand l'accélération qu'il **demande** dépasse
celle que le sol peut **fournir**.

```
a_demandée = |U - v| / τ          accélération voulue pour rejoindre la vitesse désirée
a_disponible = μ(x) · g           traction maximale offerte par le sol
```

### Calibration — valeurs sourcées

C'est le point fort de ce module : μ n'est pas un paramètre inventé, il est **mesuré** dans la
littérature, sur des surfaces de piscine précisément, et **pieds nus** — ce qui est exactement
notre situation.

| Surface | DCOF mesuré | Perception | `a_max = μg` |
|---|---|---|---|
| Carrelage mouillé lisse | ≤ 0,34 | « glissant à très glissant » par **tous** les sujets testés | ≈ 2,5–3,3 m·s⁻² |
| Surface à bonne adhérence | ≥ 0,60 | « non glissant » par tous les sujets | ≈ 5,9 m·s⁻² |

Source : étude du *National Floor Safety Institute* sur 70 sujets, surfaces mouillées pieds nus,
conçue pour les sols de piscines, baignoires et spas, avec trois tribomètres homologués
(Kendzior, 2023). Les seuils 0,34 et 0,60 sont des résultats de l'étude, pas des conventions.

**Un rapport d'environ 2 entre adhérence sèche et mouillée** : voilà le contraste que notre
modèle doit porter, et il est désormais justifié plutôt que choisi.

### Probabilité de chute

Glisser n'est pas tomber : on peut se rattraper. Nous proposons une probabilité croissante avec
le dépassement de traction, sur un pas de temps :

```
excès = max(0, a_demandée / a_disponible - 1)
p_chute(Δt) = 1 - exp(-λ_chute · excès · Δt)
```

La forme exponentielle garantit que **la probabilité par unité de temps ne dépend pas de Δt** :
sans cela, raffiner le pas de temps changerait le nombre de chutes, et l'étude de sensibilité à
Δt — exigée par les consignes — serait faussée. C'est un piège classique, et il mérite d'être
signalé dans le rapport.

`λ_chute` est le seul paramètre libre, à calibrer pour obtenir un taux de chute plausible.

---

## 2. Chute par bousculade

Second mécanisme, indépendant du sol : être poussé par la foule. La littérature sur les
mouvements de foule distingue explicitement ces deux voies — chute par perte d'équilibre, et
chute directe par compression (Chen et al., 2024).

Dans notre cadre à exclusion dure, la force de contact n'est pas calculée directement, mais la
**correction de projection** en tient lieu : plus un agent est comprimé, plus la projection doit
le déplacer. Nous utilisons donc la norme de la correction cumulée sur le pas comme indicateur
de compression, et déclenchons une chute au-delà d'un seuil.

C'est élégant parce que ça ne demande aucun mécanisme supplémentaire : l'information est déjà
produite par le solveur.

---

## 3. État « à terre »

Un agent tombé :

- **cesse de se diriger** vers la sortie (vitesse désirée nulle) ;
- **reste une contrainte d'exclusion**, avec un rayon augmenté `r_terre ≈ 1,5 · r` — un corps au
  sol occupe plus d'emprise au sol qu'un corps debout ;
- **se relève** après une durée tirée aléatoirement (§ 4).

### Effet domino

Les travaux sur les bousculades en escalier décrivent un **effet domino** : les chutes se
propagent de proche en proche, et les piétons déséquilibrés précèdent de peu les piétons tombés
(Chen et al., 2024). Nous le reproduisons simplement : un agent en mouvement rapide dont la
trajectoire croise un agent à terre à moins d'une distance d'arrêt a une probabilité de tomber à
son tour.

C'est le mécanisme qui peut faire basculer tout le scénario — et donc le résultat le plus
intéressant à mesurer.

---

## 4. Relevage

### Calibration — valeurs sourcées

| Population | Temps médian pour se relever |
|---|---|
| Adultes de 20 à 50 ans | **3,7 s** |
| Adultes de 60 ans et plus | **5,7 s** |

Source : Becker et al. (2016), analyse vidéo de séquences de relevage sur 14 sujets jeunes et
10 sujets âgés, avec décomposition en sept composantes de mouvement. L'écart entre les deux
groupes est significatif (p < 0,001).

Une étude par capteurs inertiels sur des chutes réelles donne une durée médiane au sol de 10,5 s
pour les chutes suivies d'un relevage réussi (Schwickert et al., 2017) — plus long que les 3,7 s
de laboratoire, ce qui est attendu : la mesure de terrain inclut l'hésitation et la
désorientation après l'impact, pas seulement le geste.

### Distribution retenue

Un temps de relevage est positif et asymétrique à droite : quelques personnes mettent beaucoup
plus longtemps que la médiane, personne ne met moins que zéro. Une **loi log-normale** est donc
le choix naturel, de médiane 3,7 s pour une population de nageurs (plutôt jeunes et valides).

Nous proposons de retenir une dispersion σ telle que le neuvième décile avoisine les 10 s, ce
qui reste cohérent avec les mesures de terrain.

**Tout tirage passe par `viscocrowd.core.rng`**, donc par la graine déclarée. C'est précisément
le genre de mécanisme stochastique qui rendrait les résultats irreproductibles s'il échappait au
contrôle de la graine — et les consignes l'exigent explicitement.

### Conséquence méthodologique

L'introduction d'aléa rend **obligatoire** le protocole multi-graines déjà prévu : au moins 10
graines par point de mesure, et des barres d'erreur sur toutes les figures. Un diagramme
fondamental tracé sur une seule réalisation ne voudrait plus rien dire.

---

## 5. Contournement

Un agent à terre est un obstacle que le champ de guidage ne connaît pas : recalculer l'équation
eikonale à chaque chute serait bien trop coûteux.

**Solution proposée** : une déviation locale. L'agent debout ajoute à sa direction désirée une
composante tangentielle qui l'écarte de l'agent à terre, d'intensité décroissante avec la
distance. Le champ global reste inchangé, le contournement est local.

C'est un compromis assumé, à documenter dans le rapport : le contournement est **réactif** et non
anticipé, donc un agent ne choisira pas un autre itinéraire en voyant un amas de personnes à
terre au loin. Pour notre question — le débit à travers un goulot, où les distances sont courtes
— cette limite est acceptable. Elle ne le serait pas pour étudier le choix de sortie.

---

## 6. Observables ajoutés

| Observable | Unité | Pourquoi |
|---|---|---|
| Taux de chute | chutes·s⁻¹ | mécanisme principal de dégradation du débit |
| Position des chutes | carte 2D | les chutes se concentrent-elles à la sortie de l'eau, sur le carrelage, ou au goulot ? |
| Nombre d'agents à terre | — | mesure directe de la réduction de section utile |
| Taille des cascades | agents | mesure de l'effet domino |
| Débit conditionné | pers·m⁻¹·s⁻¹ | diagramme fondamental avec et sans chutes |

La **carte des chutes** est sans doute la figure la plus parlante du rapport : elle montre
directement où l'enchaînement des milieux crée le danger.

---

## 7. Validation spécifique

Aux critères déjà prévus s'ajoutent :

1. **Indépendance à Δt du taux de chute** — c'est le test qui valide la forme exponentielle de la
   probabilité. Relancer à Δt/2 et Δt/4 : le taux de chute par seconde doit être stable.
2. **Cas limite sans chute** — en fixant μ très grand, le modèle doit redonner **exactement** les
   résultats du modèle sans chute. Un écart signale un couplage parasite.
3. **Cohérence de la distribution de relevage** — vérifier sur un grand nombre de tirages que la
   médiane empirique retrouve bien 3,7 s.
4. **Reproductibilité** — deux exécutions à même graine doivent donner des trajectoires
   identiques au bit près, malgré l'aléa.

---

## 8. Ce qu'il reste à décider

- [ ] Valeur de `λ_chute` : par calibration sur un taux de chute plausible, ou par balayage assumé ?
- [ ] Le rayon au sol `r_terre` : 1,5 · r est une estimation. Trouver une source, ou l'assumer explicitement comme hypothèse.
- [ ] Les agents à terre sont-ils piétinés (blessés, immobilisés définitivement) ou se relèvent-ils toujours ? La littérature modélise les deux ; le second est plus simple et suffit probablement à notre question.
- [ ] Hétérogénéité de la population : faut-il une fraction d'agents plus lents à se relever (la source donne 5,7 s pour les 60 ans et plus) ?

---

## Références

- Kendzior, R. J. (2023). *Assessment of Perceived and Measured Tribometer Readings in Evaluating
  Wet Barefoot Slip Resistance: A Gait-Based Approach*. Standardization: Journal of Research and
  Innovation. — [Consensus](https://consensus.app/papers/details/db6bd8574ea856e5ad2a3d0271aa241b/)
- Chatterjee, S. et al. (2022). *Development of a Tribofidelic Human Heel Surrogate for Barefoot
  Slip Testing*. Journal of Bionic Engineering. — [Consensus](https://consensus.app/papers/details/47ae466b32a95bafad09c8dcc1f48180/)
- Beschorner, K. E. et al. (2022). *Validating the ability of a portable shoe-floor friction
  testing device, NextSTEPS, to predict human slips*. Applied Ergonomics. — [Consensus](https://consensus.app/papers/details/724bf8cc881d5f9b8edfb60b38c4ea93/)
- Becker, C. et al. (2016). *Model development to study strategies of younger and older adults
  getting up from the floor*. Aging Clinical and Experimental Research. — [Consensus](https://consensus.app/papers/details/2b202c77428a5ca8a7bbc75db14a3cf4/)
- Schwickert, L. et al. (2017). *Reading from the Black Box: What Sensors Tell Us about Resting
  and Recovery after Real-World Falls*. Gerontology. — [Consensus](https://consensus.app/papers/details/942c4dc4d5835b77b5b61f5f07449917/)
- Chen, C. et al. (2024). *An extended model for crowded evacuation considering stampede on
  inclined staircases*. Simulation Modelling Practice and Theory. — [Consensus](https://consensus.app/papers/details/6c809b383ee5534ebd552fc47b460414/)
- Chen, C. et al. (2023). *An extended model for crowd evacuation considering crowding and
  stampede damage under the internal crushing*. Physica A. — [Consensus](https://consensus.app/papers/details/03bfe04eccbb53159f9459f985c39754/)
- Guo, C. et al. (2024). *An evacuation model considering pedestrian crowding and stampede under
  terrorist attacks*. Reliability Engineering & System Safety. — [Consensus](https://consensus.app/papers/details/e3f2bce0982158c089981e5e76852d6a/)

> ⚠️ **Toutes ces références doivent être vérifiées sur la source primaire** avant d'être citées
> dans le rapport. Les métadonnées ci-dessus viennent d'un moteur de recherche académique : elles
> servent à retrouver les articles, pas à les remplacer. Les consignes exigent que vous puissiez
> justifier chaque affirmation du rendu.
