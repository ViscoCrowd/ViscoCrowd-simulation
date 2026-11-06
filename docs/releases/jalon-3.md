# Jalon 3 — guidage eikonal et milieux

Publication du 7 novembre 2026. Le tag annoté `jalon-3` désigne le commit de fusion de la PR
`dev` → `main`. **Il atteste le jalon 3 seul** : la version contient aussi des travaux des
jalons 4 et 5, présents mais pas terminés (voir plus bas).

## Pourquoi la version contient plus que le jalon 3

Les dernières pièces du jalon 3 ont été fusionnées après le scénario piscine du jalon 4
(#55, 22 octobre), et elles en dépendent : sols vérifiés pendant une évacuation (#72),
obstacles de la plage (#103, #110) et valeurs de référence (#109). Aucun instantané de `dev`
ne contient le jalon 3 complet sans une partie des jalons 4 et 5. Une branche
`release/jalon-3`, comme pour le rattrapage du jalon 2, aurait dû reprendre ces PR sans le
scénario sur lequel elles reposent.

Le groupe a donc choisi de publier `dev` entier, par commit de fusion comme le demande
[CONTRIBUTING § 3.4](../../CONTRIBUTING.md#34-passer-de-dev-à-main), en délimitant la version
dans ces notes et dans le [registre des livraisons](../livraisons.md#périmètre-de-la-publication-j3).

## Ce que livre le jalon 3

| Tâche | Contenu | PR |
|---|---|---|
| C6 | Géométrie commune moteur/affichage, paramètres des trois milieux avec unités, critères de guidage ; vitesse dans l'eau vérifiée sur sa source ; une seule classe `ParametresMilieu` pour le modèle et l'interface ; valeurs de référence figées le 6 novembre | #30, #54, #71, #106, #109 |
| G1 | Guidage d'un agent dans un couloir sec ; direction et arrivée testées | #35, #36 |
| G2 | Champ eikonal par Fast Marching d'ordre 1 ; temps exact sur le couloir (10⁻¹³ s), convergence mesurée, détour sans contact d'un agent et de 12 agents | #43 |
| G3 | Vitesse libre selon le sol (eau, mouillé, sec) ; parcours sec/mouillé/sec ; effets séparés de `s`, `τ` et `a_max` (figure 7 du rapport) ; chaque sol vérifié pendant une évacuation de la piscine | #25, #30, #50, #72 |
| G4 | Accélération, freinage et virages bornés par l'adhérence, convergence en Δt | #29 |
| G5 | Guidage couplé à l'exclusion : 24 agents en contact dans le couloir, pilier contourné et imposé dans la projection, obstacles de la plage pris en compte par le guidage et la projection, obstacles laissant un passage plus étroit qu'un diamètre refusés à la lecture | #36, #37, #49, #103, #110 |

### Valeurs de référence (`experiments/piscine.yaml`)

| | Vitesse souhaitée | τ | a_max |
|---|---|---|---|
| Eau (petit bain, 0,7 m) | 0,69 m/s (Shirvani 2020) | 0,5 s | 1,6 m/s², provisoire |
| Sol mouillé | 1,34 m/s | 0,5 s | 3,3 m/s² (0,34 g, Kendzior 2023) |
| Sol sec | 1,34 m/s (Weidmann 1993) | 0,5 s | 5,9 m/s² (0,60 g, Kendzior 2023) |

Le facteur de panique vaut 1,5, soit 2,0 m/s souhaités sur les plages (Helbing et al. 2000).
Le [journal des décisions](../journal-decisions.md), entrée du 6 novembre, justifie chaque
valeur et les options écartées.

## Présent dans la version, mais pas livré

- **Jalon 4, scénario piscine** : scénario complet, franchissements à capacité unitaire et
  sortie absorbante (#55, #81). Restent ouverts la porte qui se bouche à cause de ses coins
  vifs (#85), le repère `N / (1,3 w)` (#11, PR #105 en correction) et les tests de blocage P6.
- **Jalon 5, campagnes** : étalonnage E0 (#56), comparaison E1/E2 refaite au facteur 1,5
  (#86, #109), premiers balayages E3/E4 (#84) et outil de balayage de τ (#108). Restent ouverts
  la campagne finale (#59), le biais de densité (#10) et la relation vitesse–espacement (#57).
- **Chutes** (#78, #82, #102) : module désactivé par défaut, en attente de la décision C1 (#19).

Ces travaux recevront leur propre tag lorsque leur jalon sera terminé.

## Relecture

Revues croisées enregistrées sur GitHub : #25 (Hamza, Lenny), #30 (Lenny), #43, #49, #50 et
#54 (Lenny), #72 (Hamza), #103 (Shaleena). Les PR #29, #35, #36, #37, #71, #106, #109 et
#110 n'en ont pas : la revue de la PR de publication par Hamza ou Lenny doit les couvrir.

## Validation du candidat

Mesurée le 7 novembre 2026 sur le commit `9ae1713` de `dev`, Python 3.14.2, Windows 11, poste
de Shaleena. La CI utilise Python 3.12.

| Contrôle | Résultat |
|---|---|
| Ruff et formatage | conformes |
| Tests rapides | 942 passent en 9 min 1 s ; 6 tests lents exclus |
| dont tests du guidage et des milieux | 231, dans 9 fichiers (eikonal, milieux, couloir, obstacle, géométrie piscine, comparaison du mouillé) |
| Tests lents | 6 passent en 8 min ; la CI les a aussi passés sur ce commit |
| Validation du moteur | code retour 0, 27,9 s |
| Validation et production des figures | code retour 0, 6 PNG, 1 min 39 s |
| Couloir guidé, `experiments/couloir.yaml` | 24 agents, 14 s simulées, code retour 0 |
| Couloir avec pilier, `experiments/couloir_obstacle.yaml` | 24 agents, 16 s simulées, code retour 0 |
| Effet séparé du mouillé, `comparer-mouille` | code retour 0, 29,7 s ; les six variantes redonnent au millième de seconde près le tableau du rapport (t50 de 7,082 s en référence, 8,368 s avec la vitesse seule) |

Les contrôles CI de la PR de publication doivent être verts avant fusion : style,
tests/invariants, figures, validation dans le conteneur et compilation du rapport.

## Reproduire cette version

Depuis un clone, choisir le tag, puis installer selon le README :

```bash
git switch --detach jalon-3
make install
make lint test valider
make figures
python -m viscocrowd.cli simuler experiments/couloir.yaml --sortie data/couloir.npz
python -m viscocrowd.cli simuler experiments/couloir_obstacle.yaml --sortie data/couloir_obstacle.npz
python -m viscocrowd.cli rejouer data/couloir_obstacle.npz
python -m viscocrowd.cli comparer-mouille experiments/couloir.yaml
docker compose run --rm viscocrowd make valider
```

## Limites

- **a_max de l'eau provisoire** : 1,6 m/s² au lieu de 1,67 (0,34 g × poids apparent ≈ 0,5).
  Le changement est prévu à la prochaine relance des balayages.
- **τ commun aux trois sols** : aucune source ne donne un τ propre au mouillé ou à l'eau.
  L'outil de balayage existe (#108), mais la mesure de sensibilité reste à lancer.
- **Vitesse identique sur le mouillé et le sec** : c'est un choix de protocole, pour isoler
  l'adhérence. Un balayage de la vitesse sur le mouillé est en revue (#104).
- **Champ de guidage statique** : il ignore l'attente devant un site occupé et la congestion.
  Le Fast Marching est d'ordre 1.
- **Durées de franchissement non sourcées** (4 s au rebord, 2 s à l'échelle) : elles sont
  balayées en E4.
- **Effet du sol mouillé en marche nominale** : +0,02 ± 0,01 s sur t50, réel mais
  négligeable, tant que l'adhérence du mouillé reste à 3,3 m/s² et que la porte n'est pas
  encombrée.

Le planning courant et les livraisons suivantes sont consultables sur la branche `dev`.
