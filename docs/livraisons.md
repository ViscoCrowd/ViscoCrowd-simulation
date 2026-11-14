# Jalons et livraisons

Un jalon **implémenté et validé dans `dev`** n'est **publié** qu'après sa PR vers `main`
et la création de son tag annoté et de sa release. Les critères du jalon restent ceux de la
[spécification § 9](superpowers/specs/2026-10-06-viscocrowd-design.md#9-jalons) ; le
[planning](planning/README.md) suit les tâches et [CONTRIBUTING § 3.4](../CONTRIBUTING.md#34-passer-de-dev-à-main)
décrit les opérations de publication.

## Registre au 10 novembre 2026

| Jalon | État technique | Publication |
|---|---|---|
| 0 — socle et cadrage | Socle présent depuis #1 ; questions de cadrage validées par l'enseignant le 3 novembre ([trace](validation-sujet.md#trace-de-validation), #19) | Aucun tag attestant une clôture complète de J0 |
| 1 — moteur | Livré sur `main` par #1, correctif Makefile #2/#3 inclus | [`jalon-1`](https://github.com/ViscoCrowd/ViscoCrowd-simulation/releases/tag/jalon-1), commit `28252ef6d196caec847e6f957e7282152cf98449` ; repère historique créé le 21 octobre |
| 2 — exclusion | Validé avec limites connues ; corrections et figures #21–#23, correctifs #28 | [`jalon-2`](https://github.com/ViscoCrowd/ViscoCrowd-simulation/releases/tag/jalon-2), publication de rattrapage du 21 octobre ; [provenance, mesures et limites](releases/jalon-2.md) |
| 3 — guidage et milieux | Livré : C6 et G1–G5 ; valeurs de référence figées le 6 novembre (#109), a_max de l'eau provisoire | [`jalon-3`](https://github.com/ViscoCrowd/ViscoCrowd-simulation/releases/tag/jalon-3), commit de fusion `190d29e4b60a0864e20b75288dcc854f7f4dddfc` de la PR #112 le 9 novembre, `dev` resynchronisée dans #113 ; [notes de version](releases/jalon-3.md) |
| 4 — scénario piscine | Scénario, franchissements et sorties livrés (#55, #81) ; repère `N / (J w)` (J = 1,225 pers/(m·s), Weidmann) et état absorbant actés dans #105 ; porte à arrondir (#85) et tests de blocage P6 ouverts | Code présent dans la version `jalon-3`, non revendiqué comme livré ; #105 fusionnée après le tag |
| 5 — campagnes | En cours : E0 (#56), E1/E2 refaits au facteur 1,5 (#86, #109), premiers balayages E3/E4 (#84), balayages de τ (#108), de la vitesse sur sol mouillé et du taux de chute (#104) ; biais de densité borné (#101) ; relation vitesse–espacement branchée sur la piscine (#100), activée à T = 0,35 s et validée par le groupe le 10 novembre, E1/E2 refaits (#116) ; campagne finale à faire (#59) | Code et mesures jusqu'à #109 présents dans la version `jalon-3`, non revendiqués comme livrés ; #100, #101, #104 et #116 fusionnées après le tag |
| 6 — livrables | Rapport en cours ; transparents à préparer | Non publié |

Le module de chutes (#78, #82, #102) est lui aussi présent dans la version `jalon-3` sans y
être revendiqué. Son inclusion dans le rendu a été validée par l'enseignant le 3 novembre
(C1, #19) ; il reste désactivé par défaut et non calibré.

Les anciennes versions restent consultables ; elles ne doivent pas être présentées comme
la version courante ni comme une validation des travaux ultérieurs. La date de création d'un
tag rétrospectif est la date réelle de régularisation, pas celle de l'ancien commit.

## Périmètre de la publication J3

Les dernières pièces du jalon 3 ont été fusionnées dans `dev` après le scénario piscine du
jalon 4 (#55, 22 octobre), et elles en dépendent : sols vérifiés pendant une évacuation
(#72), obstacles de la plage (#103, #110) et valeurs de référence (#109). Aucun instantané
de `dev` ne contient donc le jalon 3 complet sans une partie des jalons 4 et 5. Une branche
`release/jalon-3`, comme pour le rattrapage J2, demanderait de reprendre ces PR sans le
scénario sur lequel elles reposent ; elle est écartée.

Le groupe a donc retenu le 7 novembre 2026 de publier `dev` entier, par commit de fusion, en
**délimitant explicitement la version** (condition 2 de [CONTRIBUTING § 3.4](../CONTRIBUTING.md#34-passer-de-dev-à-main)) :
le tag `jalon-3` atteste le jalon 3 seul. Les jalons 4 et 5 recevront leur propre tag quand ils
seront terminés. Les [notes de version](releases/jalon-3.md) listent ce qui est livré et ce qui
ne l'est pas.

## Audit rétrospectif

Vérifié le 21 octobre 2026 avant régularisation, à partir du graphe Git, des PR et des
contrôles GitHub. Le constat porte sur les traces disponibles, pas sur des échanges supposés.

- **#1 (6 octobre)** a livré directement sur `main` le socle et le moteur. C'est l'amorçage
  du dépôt, antérieur à la méthode d'intégration sur `dev` ajoutée dans #5. Ses contrôles
  sont verts ; aucune revue croisée n'est enregistrée sur cette PR. Aucun tag n'avait été créé.
- **#2 puis #3 (12 octobre)** suivent bien branche → `dev` → `main` pour le correctif
  Makefile. La revue de Shaleena sur #3 a été déposée après sa fusion : ne pas l'annoncer
  comme une approbation préalable. Le tag et la fiche de livraison manquaient.
- **#6 à #38** ont pour base `dev`. La relecture et la validation collective de J2 sont
  tracées dans #6, #15 et le journal ; ses corrections et figures ont été relues dans
  #21, #22 et #23. Sa promotion vers `main` a été oubliée avant le début de J3.
- **#28** a été intégrée par rebase, sous quatre commits, alors que les contributions
  ordinaires doivent être squashées. On garde ces commits et leurs auteurs ; cela ne
  justifie aucune réécriture de branche.
- **La synchronisation après #3**, commit `35d6d08`, a bien rendu `main` ancêtre de `dev`,
  mais ne correspond à aucune PR dans la liste disponible. L'ancienne procédure prescrivait
  ce push direct en contradiction avec l'interdiction générale. Elle est remplacée par une
  PR `sync/` fusionnée avec un commit de merge pour préserver cette ascendance.

Les anciennes approbations ne sont pas réinventées et les écarts ne sont pas effacés.
Le suivi de régularisation, les PR et les résultats nouveaux sont centralisés dans [#39].

## Périmètre du rattrapage J2

Le candidat part de `babd8b0`, dernier instantané de `dev` après les figures de #23 et
avant l'adhérence de #25. Il inclut donc l'exclusion, les voisins, le tassement, les six
figures, la protection de `State`, le contrôle des valeurs non finies et Docker. L'observable
de débit et la maquette graphique déjà livrées sont conservées avec leurs limites explicites.

Les corrections indépendantes de J3 déjà approuvées dans #28 sont reprises avec leur SHA :
`7c8a80d` (validations numériques), `742494d` (outillage), ainsi que la précision du seuil
d'extrapolation à 80 balayages de `bd481dd`. Le refactoring des milieux `d5b313b` n'entre
pas dans ce périmètre. La méthode et ce registre passent d'abord par une PR vers `dev`.

La validation a été rejouée sur le candidat exact : 282 tests rapides passent, six figures
sont produites et la validation du moteur réussit. Les [notes de version](releases/jalon-2.md)
donnent les mesures et les commandes de reproduction.
Lors de ce rattrapage, les contacts multiples (#10), l’état absorbant absent (#11), la source
primaire de Weidmann (#12) et le cadrage (#19) restaient ouverts. Leurs évolutions ultérieures
sont suivies dans le planning et les issues ; l’attribution du tag ne les résolvait pas.

[#39]: https://github.com/ViscoCrowd/ViscoCrowd-simulation/issues/39
