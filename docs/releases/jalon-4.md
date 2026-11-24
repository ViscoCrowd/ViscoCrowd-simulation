# Jalon 4 — la piscine et ses campagnes (brouillon)

**Brouillon du 18 novembre 2026, mis à jour le 20, à ne publier qu'après P6** (franchissements
fantômes) et la fusion des PR de la feuille de route qu'on voudra y inclure. Le tag annoté
`jalon-4` désignera le commit de fusion de la PR `dev` → `main`, fusionnée **par commit de
fusion**, jamais en squash ([CONTRIBUTING § 3.4](../../CONTRIBUTING.md)).

## Ce que livre le jalon 4

| Tâche | Contenu | PR |
|---|---|---|
| P1–P4 | Bassin, rebords, échelles, plage et porte ; transitions eau → franchissement → plage → sorti ; capacité unitaire et durée de passage des sites ; 100 baigneurs sur le parcours complet | #54, #55 (avant `jalon-3`) |
| P5 | Sortie définitive, état absorbant, repère analytique N / (J w) | #81, #105 |
| P6 | Passages, blocages, franchissements fantômes : montants de porte arrondis, déblocage des nageurs immobiles | #125, #131 ; **reste à clore** |
| M4 | Régulation vitesse–espacement de Tordeux (T = 0,35 s), étalonnée sur E0, branchée sur la piscine, contrôlée sur N = 40 et 20 | #100, #116, #141 |
| M5 | E1/E2 sec contre mouillé, porte arrondie, a_max de l'eau à 1,67 m/s² | #116, #128 |
| M6 | Balayages : vitesse sur le mouillé, taux de chute, durées de franchissement, adhérence dans l'eau, τ, plage mouillée jusqu'à une porte saturée | #104, #119, #136, #137 |
| M8 | Diagramme fondamental devant E0, devant la porte de la piscine, en écoulement libre sur l'anneau | #126, #133, #149 |
| M9 | Sensibilité au pas de temps sur la référence actuelle | #138 |
| Chutes | Risque de bousculade compté par choc ; indépendance à Δt ; référence sans chutes, campagne exploratoire | #132, #135, #150 |
| Visualisation | Pose longue, duel sec/mouillé, agents à terre, diagramme en direct | #159, #160, #161, #162 |
| Rapport | Introduction, modélisation, validation du moteur, voisins, cohérence dimensionnelle, diagrammes, chiffres de la piscine | #118, #120 à #123, #142, #143, #145 |
| Options (désactivées) | Navigation locale de Moussaïd et al. (2011), profondeur variable, traînée d'eau des baigneurs, choix du site selon la file : dans le code, hors référence ; leur statut se décide dans #158, #192 et #201 | #163, #186, #165, #188 |
| Confirmation | Effet inertiel confirmé sur les graines 11 à 20 ; référence figée sur vingt baigneurs | #172, #175 |
| Campagnes | Faster-is-slower devant une porte saturée | #166 |
| Visualisation (suite) | Chaînes de force devant la porte ; variantes côte à côte ; carte des temps d'arrêt ; intervalles entre sorties ; films de la soutenance en une commande | #164, #182, #178, #177, #197 |
| Outillage | Configurations réduites partagées par les tests ; surcharges au lancement (`--fixer`) ; bilans JSON arrondis ; commandes de visualisation déclarées dans `viz` | #171, #173, #176, #196 |
| Documentation | Démonstration du duel ; réponses de soutenance ; protocole de mesure des franchissements ; porte et règlement des ERP ; attribution des tâches de S8 à S15 | #169, #179, #185, #199, #190 |

## Résultat principal à la date du brouillon

Dans la piscine de référence, le carrelage mouillé n'a pas d'effet mesurable. Quand un sol très
glissant (1 à 2 m/s²) touche la file d'une porte saturée, l'effet inertiel apparaît : −19 % de
débit à 1 m/s², positif sur 10 graines sur 10 (#137). Il est confirmé sur les graines 11 à 20
(#172), et tient de 0,75 à 0,88 m de porte (#198).

## Limites connues, et travaux qui restent sur `dev`

- Taux de chute non calibrés (#130) : le module reste désactivé dans la référence.
- Durées de franchissement sans source : le protocole de mesure est prêt (#185), la séance
  reste à faire.
- Navigation locale (#163) et options du 18 novembre : dans le code, désactivées ; la
  référence ne change pas. Statut à décider (#158, #192, #201).
- Le rapport n'a pas encore sa conclusion définitive (#180).
- En revue au 20 novembre, à inclure si elles sont fusionnées avant la publication : nombre
  d'échelles (#174), conclusion du rapport (#180), temps de réaction (#181) et départs
  échelonnés (#187), menu de paramétrage (#183), figure 8 (#184), feuille de route (#200),
  paliers de débit de E0 (#203), file devant soi (#204), anneau sans voies (#205),
  correctifs d'outillage et de `make demo` (#206, #207).

## Liste des PR fusionnées dans `dev` depuis `jalon-3`

#100, #101, #104, #105, #113, #114, #115, #116, #117, #118, #119, #120, #121, #122, #123, #125,
#126, #128, #129, #131, #132, #133, #134, #135, #136, #137, #138, #139, #141, #142, #143, #144,
#145, #146, #147, #148, #149, #150, #152, #153, #156, #157, #159, #160, #161, #162, #163, #164,
#165, #166, #168, #169, #171, #172, #173, #175, #176, #177, #178, #179, #182, #185, #186, #188,
#189, #190, #196, #197, #199
(69 PR au 20 novembre ; à compléter au moment de la publication).

## Publication (à faire le jour J)

1. Vérifier que toute la CI de `dev` est verte, y compris le rapport.
2. PR `dev` → `main` avec ce périmètre, fusionnée avec `gh pr merge <n> --merge`.
3. `git tag -a jalon-4 <commit de fusion> -m "Jalon 4 — piscine"`, `git push origin jalon-4`.
4. `gh release create jalon-4 --notes-file docs/releases/jalon-4.md`.
5. PR `sync/main-jalon-4` vers `dev`, fusionnée avec un commit de fusion.
