# Jalon 4 — scénario piscine

Publication du 24 novembre 2026. Le tag annoté `jalon-4` désigne le commit de fusion de la PR
`dev` → `main`, fusionnée **par commit de fusion**, jamais en squash
([CONTRIBUTING § 3.4](../../CONTRIBUTING.md#34-passer-de-dev-à-main)). **Il atteste le jalon 4
seul**, P1 à P6 : la version contient aussi des travaux des jalons 5 et 6, présents mais pas
terminés (voir plus bas).

## Pourquoi la version contient plus que le jalon 4

Comme pour `jalon-3`, les campagnes du jalon 5 et le rapport du jalon 6 ont avancé sur `dev`
en même temps que le scénario, et ils s'appuient sur lui. Aucun instantané de `dev` ne
contient le jalon 4 complet sans eux. La dernière pièce du jalon 4, les tests P6 (#210), a été
fusionnée le 24 novembre, après la plupart des campagnes. Le groupe publie donc `dev` entier
et délimite la version dans ces notes et dans le [registre des livraisons](../livraisons.md).

## Ce que livre le jalon 4

| Tâche | Contenu | PR |
|---|---|---|
| P1 | Bassin, rebords, échelles, plage et porte selon C6 ; nombre d'échelles réglable dans la configuration | #54, #55, #174 |
| P2 | Transitions eau → franchissement → plage → sorti, à sens unique | #55 |
| P3 | Capacité unitaire et durée de passage des échelles et des rebords | #55 |
| P4 | Une foule sur le parcours complet : 100 baigneurs, tous sortis | #55 |
| P5 | Sortie définitive, état absorbant, contrôle croisé sur les positions, repère analytique N / (J w) avec J = 1,225 pers/(m·s) (Weidmann) | #47, #55, #81, #105 |
| P6 | Passages, blocages et absence de franchissements fantômes : montants de porte arrondis (#85), déblocage des nageurs immobiles (#127), contrôle complet du parcours sur 7 configurations rapides et 4 lentes | #125, #131, #210 |

### P6 en chiffres (#210)

`tests/test_p6_parcours.py` vérifie, pour chaque agent : sortie avant la durée maximale, site
saisi à portée (0,25 m, ou 0,65 m par la seule règle de déblocage), présence exacte sur le site
pendant le franchissement, réintroduction exacte au point d'arrivée, aucun saut de plus de
0,1 m sans changement d'état, et sortie dans l'embrasure de la porte. Le contrôle échoue sur
quatre parcours faussés exprès.

| Configuration | N | t100 | Plus grand saut | Saisie la plus lointaine |
|---|---|---|---|---|
| Référence | 100 | 53,7 s | 0,020 m | 0,260 m |
| Sans régulation | 200 | 62,0 s | 0,024 m | 0,260 m |
| Sans régulation, graine 4 (cas de #127) | 200 | 58,3 s | 0,024 m | 0,259 m |
| Navigation, choix du site et temps de réaction ensemble | 100 | 49,3 s | 0,027 m | 0,261 m |
| Porte de 0,8 m, sans échelle, chutes actives : 7 configurations rapides | 30 à 40 | 29,9 à 33,8 s | ≤ 0,025 m | ≤ 0,260 m |

Le blocage de #127 (13 baigneurs sur 200 restés sous l'échelle du haut, graine 4, sans
régulation) ne se reproduit plus : les 200 sortent en 58,3 s, avec ou sans la règle de
déblocage. La règle reste couverte par les tests d'arche de `tests/test_piscine_scenario.py`.

## Présent dans la version, mais pas livré

Ces travaux recevront leur propre tag quand leur jalon sera terminé.

- **Jalon 5, campagnes.** Régulation vitesse–espacement de Tordeux (T = 0,35 s), étalonnée
  sur E0 et branchée sur la piscine (M4 : #100, #116, #141) ; E1/E2 sec contre mouillé avec la
  porte arrondie et a_max de l'eau à 1,67 m/s² (M5 : #116, #128) ; balayages de la vitesse sur
  le mouillé, du taux de chute, des durées de franchissement, de l'adhérence, de τ et de la
  plage mouillée (M6 : #104, #119, #136, #137) ; diagrammes fondamentaux devant E0, devant la
  porte et sur l'anneau (M8 : #126, #133, #149, #203, #205) ; sensibilité au pas de temps
  (M9 : #138) ; effet inertiel confirmé sur les graines 11 à 20 et départs échelonnés (#172,
  #187) ; *faster-is-slower* (#166). **Restent ouverts** la campagne finale sur plusieurs
  graines (M7, #59), la sensibilité à N et aux graines sur la configuration finale (M9) et le
  domaine de validité (M8).
- **Options du modèle, désactivées dans la référence.** Navigation locale de Moussaïd et al.
  (2011), profondeur variable, égouttage, choix du site selon la file d'attente, temps de
  réaction (#163, #165, #181, #186, #188, #204). Leur statut se décide dans #158, #192 et #201.
- **Chutes** (#132, #135, #150) : risque compté par choc, indépendant de Δt ; module
  désactivé dans la référence, taux non calibrés (#130).
- **Jalon 6, livrables.** Rapport : introduction, modélisation, validation, diagrammes,
  chiffres de la piscine, conclusion et résumé (#118, #120 à #123, #142, #143, #145, #180,
  #184) ; réponses de soutenance (#179). Figures finales (R2), relecture complète (R5) et
  transparents (R7) restent à faire.
- **Outillage et visualisation.** Pose longue, duel sec/mouillé, agents à terre, diagramme
  en direct, chaînes de force, variantes côte à côte, carte des temps d'arrêt, intervalles
  entre sorties, films de soutenance, menu de paramétrage, surcharges au lancement, CI
  parallèle (#159 à #162, #164, #173, #177, #178, #182, #183, #196, #197, #206 à #208).

## Résultat principal à la date de publication

Résultat de campagne (jalon 5), provisoire jusqu'à la campagne finale. Dans la piscine de
référence, le carrelage mouillé n'a pas d'effet mesurable. Quand un sol très glissant (1 à
2 m/s²) touche la file d'une porte saturée, l'effet inertiel apparaît : −19 % de débit à
1 m/s², positif sur 10 graines sur 10 (#137). Il est confirmé sur les graines 11 à 20 (#172),
il a besoin d'une file pour exister (#187) et il tient de 0,75 à 0,88 m de porte (#203).

## Relecture

78 des 85 PR fusionnées depuis `jalon-3` ont une revue croisée enregistrée sur GitHub. Sept
n'en ont pas, et la revue de la PR de publication doit les couvrir : #113 (synchronisation
après `jalon-3`), #141 (régulation contrôlée sur N = 40 et 20), #168 (vitesse de relecture et
`make maquette`), #208 (CI parallèle), #209 (tolérance du bilan de l'anneau) **#210 (tests
P6)**, la pièce qui clôt ce jalon, et #211 (ces notes).

## Validation du candidat

Mesurée le 24 novembre 2026 sur le commit `03b4093` de `dev` (fusion de #210), Python
3.14.4, macOS 27, 8 cœurs, poste de Lenny. La CI utilise Python 3.12 et les versions de
`requirements.lock.txt`.

| Contrôle | Résultat |
|---|---|
| Ruff et formatage | conformes |
| Tests rapides | 1 285 passent en 1 min 20 s sur 8 processus ; 12 tests lents exclus |
| dont P6 (`tests/test_p6_parcours.py`) | 12 rapides, 26 s sur un seul processus |
| Tests lents | 12 passent en 2 min 35 s sur 8 processus, dont les 4 de P6 |
| Validation du moteur et figures | code retour 0, tous les critères chiffrés sous leur seuil, 6 PNG, 49 s |
| Piscine de référence, `experiments/piscine.yaml` | 100 baigneurs, tous sortis, t100 = 53,7 s |

Les contrôles CI de la PR de publication doivent être verts avant fusion : style,
tests/invariants, figures, validation dans le conteneur et compilation du rapport.

## Reproduire cette version

Depuis un clone, choisir le tag, puis installer selon le README :

```bash
git switch --detach jalon-4
make install
make lint test valider
make test-lents
make simu                 # piscine de référence, 100 baigneurs
make rejouer
docker compose run --rm viscocrowd make valider
```

## Limites connues

- **Durées de franchissement sans source** (4 s au rebord, 2 s à l'échelle) : le protocole
  de mesure est prêt (#185), la séance reste à faire.
- **Taux de chute non calibrés** (#130) : le module reste désactivé dans la référence.
- **Champ de guidage statique** : il ignore l'attente devant un site occupé ; le choix du
  site selon la file existe en option (#188, #204), hors référence.
- **Règle de déblocage sans source** (2 s d'immobilité, 0,65 m) : elle ne se déclenche dans
  aucune des configurations de P6, mais elle reste active par défaut.
- **Une seule porte** : la porte de secours est prévue après le rendu (#193).

## Liste des PR fusionnées dans `dev` depuis `jalon-3`

#100, #101, #104, #105, #113, #114, #115, #116, #117, #118, #119, #120, #121, #122, #123, #125,
#126, #128, #129, #131, #132, #133, #134, #135, #136, #137, #138, #139, #141, #142, #143, #144,
#145, #146, #147, #148, #149, #150, #152, #153, #156, #157, #159, #160, #161, #162, #163, #164,
#165, #166, #168, #169, #171, #172, #173, #174, #175, #176, #177, #178, #179, #180, #181, #182,
#183, #184, #185, #186, #187, #188, #189, #190, #196, #197, #199, #200, #203, #204, #205, #206,
#207, #208, #209, #210, #211 (85 PR, dont ces notes).
