# Jalons et livraisons

Un jalon **implémenté et validé dans `dev`** n'est **publié** qu'après sa PR vers `main`
et la création de son tag annoté et de sa release. Les critères du jalon restent ceux de la
[spécification § 9](superpowers/specs/2026-10-06-viscocrowd-design.md#9-jalons) ; le
[planning](planning/README.md) suit les tâches et [CONTRIBUTING § 3.4](../CONTRIBUTING.md#34-passer-de-dev-à-main)
décrit les opérations de publication.

## Registre au 21 octobre 2026

| Jalon | État technique | Publication |
|---|---|---|
| 0 — socle et cadrage | Socle présent depuis #1 ; trace enseignant encore incomplète (#19) | Aucun tag attestant une clôture complète de J0 |
| 1 — moteur | Livré sur `main` par #1, correctif Makefile #2/#3 inclus | [`jalon-1`](https://github.com/ViscoCrowd/ViscoCrowd-simulation/releases/tag/jalon-1), commit `28252ef6d196caec847e6f957e7282152cf98449` ; repère historique créé le 21 octobre |
| 2 — exclusion | Validé dans `dev`, avec limites connues ; corrections et figures #21–#23 | Rattrapage suivi dans [#39] : instantané `babd8b0` et correctifs relus de #28 ; publication `jalon-2` à terminer |
| 3 — guidage et milieux | En cours : adhérence et couloir G1/G5 livrés ; eikonal avec obstacles et intégration piscine manquants | Reste sur `dev`, pas de tag de jalon terminé |
| 4 à 6 | Scénario complet, campagnes et livrables finaux à réaliser | Non publiés |

Les anciennes versions restent consultables ; elles ne doivent pas être présentées comme
la version courante ni comme une validation des travaux ultérieurs. La date de création d'un
tag rétrospectif est la date réelle de régularisation, pas celle de l'ancien commit.

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

La validation est rejouée sur le candidat exact ; la release doit donner ses propres chiffres.
Le défaut résiduel de contacts multiples (#10), l'état absorbant absent (#11), la source
primaire de Weidmann (#12) et le cadrage (#19) restent visibles. Aucun de ces éléments n'est
déclaré résolu par l'attribution d'un tag.

[#39]: https://github.com/ViscoCrowd/ViscoCrowd-simulation/issues/39
