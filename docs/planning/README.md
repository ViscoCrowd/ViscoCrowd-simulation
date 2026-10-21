# Planning ViscoCrowd 2026–2027

**État au 21 octobre 2026.** Ce document est la source de référence du planning : tâches,
dates, responsabilités et suivi sont modifiés ici, avec un diff relisible en pull request.
Les créneaux futurs et les affectations marquées **(proposé)** sont une proposition de travail,
à confirmer selon les disponibilités du groupe ; ils ne constituent pas un accord déjà obtenu.

## Calendrier

Convention de planification : **S1 commence le mardi 6 octobre 2026**, date de la spécification.
C'est un repère de calendrier, pas une preuve de la date réelle de début des travaux ou de
l'acceptation du sujet. Au 21 octobre, nous sommes en S3. Les jalons 1 et 2 sont déjà livrés,
en avance sur les cibles S2–S5 du planning initial ; leurs créneaux ne restent donc pas réservés
à du développement déjà terminé.

| Semaine | Du | Au | Priorité prévue |
|---|---|---|---|
| S1 | 06/10/2026 | 12/10/2026 | Cadrage et socle initial |
| S2 | 13/10/2026 | 19/10/2026 | Trace enseignant, questions ouvertes et répartition |
| S3 | 20/10/2026 | 26/10/2026 | Moteur, Docker, archives et premier couloir guidé livrés ; début du rapport |
| S4 | 27/10/2026 | 02/11/2026 | Contrat de géométrie et paramètres des milieux |
| S5 | 03/11/2026 | 09/11/2026 | Poursuite du rapport et préparation des futurs scénarios sur la chaîne d'archives livrée |
| S6 | 10/11/2026 | 16/11/2026 | Préparer le guidage avec obstacles et poursuivre les milieux ; G1 anticipé en S3 |
| S7 | 17/11/2026 | 23/11/2026 | Guidage avec obstacle et tests des milieux |
| S8 | 24/11/2026 | 30/11/2026 | Scénario piscine et préparation des mesures |
| S9 | 01/12/2026 | 07/12/2026 | Franchissements, goulot sec et qualification des mesures |
| S10 | 08/12/2026 | 14/12/2026 | Campagnes E1–E4, figures et analyse |
| S11 | 15/12/2026 | 21/12/2026 | Sensibilité, relecture et version complète rapport/code |
| S12 | 22/12/2026 | 28/12/2026 | Marge de fin d'année ; aucune livraison principale prévue |
| S13 | 29/12/2026 | 04/01/2027 | Marge et vérification du dépôt |
| S14 | 05/01/2027 | 11/01/2027 | Dépôt rapport/code, puis transparents |
| S15 | 12/01/2027 | 18/01/2027 | Répétitions et dépôt des transparents |

Échéances imposées par le [cahier des charges](../cahier-des-charges.md#2-livrables) :

- **5 janvier 2027, 23h59** : rapport et code sur Moodle.
- **18 janvier 2027, 18h00** : transparents.
- **19 janvier 2027** : soutenance (10 min + 10 min de questions).

La version complète rapport/code est visée au **21 décembre**, avant les semaines de fin
d'année ; S12–S13 servent de marge, et la présentation est préparée après le rendu du rapport.
Les congés et périodes d'entreprise réels ne sont pas disponibles dans le dépôt : cette marge
n'est pas un calendrier de vacances officiel. La charge doit être réévaluée dès que chacun
renseigne ses disponibilités (C2, [#20]). La cible du 19 octobre est passée : les informations
manquantes restent ouvertes et aucune nouvelle disponibilité n'est présumée.

| Membre | Périodes d'entreprise et congés | Action attendue |
|---|---|---|
| Hamza | À renseigner | Confirmer ses disponibilités, notamment S6–S11 et fin décembre |
| Shaleena | À renseigner | Confirmer ses disponibilités, notamment S6–S11 et fin décembre |
| Lenny | À renseigner | Confirmer ses disponibilités, notamment S6–S11 et fin décembre |

## Lecture du suivi

**Livré** décrit une brique présente ; **validé collectivement** décrit une décision du groupe.
Ces états n'impliquent pas l'absence de limites connues. **À faire** et **en suivi** décrivent un
travail restant. **Non programmé** ne réserve aucune semaine et ne bloque aucun jalon.
Les dates des tâches futures sont des cibles, celles des livraisons sont indiquées comme telles.

Le responsable coordonne une tâche, sans en être nécessairement l'unique auteur. Les
affectations existantes de #10, #13 et #8 sont reprises. Lenny coordonne le suivi du cadrage
(C1, [#19]) et la collecte des disponibilités et accords (C2, [#20]). Les affectations de réalisation
restent **proposées** pour les travaux non commencés dont l'accord détaillé n'est pas transcrit.
L'issue [#20] marque la confirmation des responsables comme acquise ; la répartition détaillée,
les disponibilités et la réévaluation de charge restent à consigner. C7 est pris en charge par
Lenny, ainsi que le banc G1/G5 et sa relecture ([#34]) ; les livraisons ci-dessous indiquent
leurs auteurs constatés. Ce tableau ne remplace pas
l'annexe du rapport sur les contributions réellement effectuées et leur proportion.

## Travaux déjà livrés

| ID | Étape | Tâche / livrable | Semaine de constat | Date du constat | Responsable / attribution connue | État | Référence |
|---|---|---|---|---|---|---|---|
| L1 | J0 | Sujet et problématique rédigés | S2 | 13/10/2026 | Groupe | Livré ; trace de l'accord à compléter en C1 | [Cadrage](../validation-sujet.md) |
| L2 | J0 | Dépôt et méthode de contribution | S2 | 13/10/2026 | Groupe | Livré ; répartition à compléter en C2 | [Contribution](../../CONTRIBUTING.md) |
| L3 | J1 | Mouvement simple, position/vitesse semi-implicites, confinement et dissipation | S2 | 13/10/2026 | Attribution détaillée à consigner dans le rapport | Validé ; sécurisation C3–C4 livrée depuis | [Moteur](../../README.md#validation-du-moteur) |
| L4 | J2 | Contact de deux agents, voisins, groupes denses et tests de stabilité | S2 | 13/10/2026 | Attribution détaillée à consigner dans le rapport | Validé avec limite de contacts multiples #10 | [PR #6](https://github.com/ViscoCrowd/ViscoCrowd-simulation/pull/6), [#10] |
| L5 | J2 | Jacobi vectorisé et Nesterov après 80 balayages | S2 | 13/10/2026 | Hamza (suivi #13), décision des trois membres | Validé collectivement ; critères documentaires de l'issue encore ouverts | [#13], [journal](../journal-decisions.md) |
| L6 | J5, brique anticipée | Passages et débit sur une ligne, référence de Weidmann | S2 | 13/10/2026 | Shaleena (PR #9 / issue #8) | Livré ; densité, état de sortie et source primaire restent distincts | [PR #9](https://github.com/ViscoCrowd/ViscoCrowd-simulation/pull/9), [#11], [#12] |

<a id="cadrage-et-prerequis"></a>

## Cadrage et prérequis

Les prérequis moteur C3–C4 sont livrés. Le jalon 3 dispose maintenant d'un banc de couloir
avec une carte par bandes réelle, un guidage analytique et un groupe en contact (G1/G5).
Son intégration piscine dépend encore de la géométrie et des paramètres C6, du guidage
avec obstacles G2 et du suivi de répartition C2.
C1 dépend d'une réponse extérieure et ne bloque que ce qui en dépend réellement : la
mesure de densité M1 (SciPy/Voronoï) et toute inclusion des chutes. Le scénario piscine dépend
ensuite du guidage et des milieux validés. Les campagnes E1–E4 dépendent des
mesures de densité, de l'étalonnage E0, de la maîtrise du biais #10 et de la reproductibilité.

| ID | Étape | Tâche / critère de fin | Semaines | Dates cibles | Responsable | État | Référence |
|---|---|---|---|---|---|---|---|
| C1 | Cadrage | Consigner date/canal/destinataires/contenu de l'accord ; obtenir les réponses SciPy/Voronoï, dimensionnement et avis sur les chutes | S2 | Cible 19/10 passée | Lenny (coordination du suivi) | À compléter ; conditionne M1 et les chutes, pas J3 | [#19], [questions et trace](../validation-sujet.md#trace-de-validation) |
| C2 | Organisation | Consigner la répartition confirmée et les périodes d'entreprise/congés ; ajuster la charge | S2 | Cible 19/10 passée | Lenny (coordination), informations des trois membres | Confirmation cochée dans #20 ; détail, disponibilités et charge restent à consigner | [#20], calendrier ci-dessus |
| C3 | Moteur | Rejeter les valeurs non finies ; tests en projection stricte et permissive | S2 | Livré 19/10/2026 | Hamza ; compléments Shaleena le 20/10 | Livré, issue clôturée | [#16], [PR #21](https://github.com/ViscoCrowd/ViscoCrowd-simulation/pull/21) |
| C4 | Moteur | Protéger les tableaux de State ; tester les alias d'entrée et entre états | S2 | Livré 19/10/2026 | Hamza | Livré, issue clôturée | [#17], [PR #22](https://github.com/ViscoCrowd/ViscoCrowd-simulation/pull/22) |
| C5 | Reproductibilité | Aligner l'interpréteur Docker/Makefile ; exécuter valider et figures dans le conteneur | S2–S3 | Livré 19/10 ; CI revérifiée 21/10 | Hamza ; compléments outillage Shaleena le 20/10 | Livré ; validation et figures exécutées en CI Docker | [#18], [PR #22](https://github.com/ViscoCrowd/ViscoCrowd-simulation/pull/22), [CI #30](https://github.com/ViscoCrowd/ViscoCrowd-simulation/actions/runs/39561365829) |
| C6 | J3 | Définir la géométrie commune moteur/affichage, les paramètres des trois milieux avec unités et les critères de guidage | S4 | 27/10–02/11/2026 | Hamza (proposé) | Contrat et géométrie de couloir avec relecture livrés ; géométrie piscine, calibration et raccordement de sa maquette restent à faire | [#26], [PR #30](https://github.com/ViscoCrowd/ViscoCrowd-simulation/pull/30) |
| C7 | Reproductibilité | Lire les configurations YAML et sauvegarder les trajectoires .npz ; vérifier leur relecture à graine fixée | S3 | Livré 21/10/2026, anticipé depuis S5 | Lenny | Livré pour trois bancs, dont couloir avec relecture animée ; population fixe, campagnes piscine à raccorder | [#31], [PR #32](https://github.com/ViscoCrowd/ViscoCrowd-simulation/pull/32) |

## Guidage, milieux et scénario

| ID | Étape | Tâche / critère de fin | Semaines | Dates cibles | Responsable | État | Référence |
|---|---|---|---|---|---|---|---|
| G1 | J3 | Guider un agent dans un couloir sec vers une sortie ; vérifier direction et arrivée | S3 | Livré 21/10/2026, anticipé depuis S6 | Lenny | Livré : guidage analytique sans obstacle, arrivée et convergence testées | [#34], PR #35–#36 |
| G2 | J3 | Calculer le champ eikonal et tester un détour autour d'un obstacle fixe | S6–S7 | 10–23/11/2026 | Hamza (proposé) | À faire | Spécification §2.6 |
| G3 | J3 | Adapter la vitesse à l'eau, au sol mouillé et au sec | S2–S7 | Briques livrées 19–21/10 ; intégration piscine cible 10–23/11 | Shaleena ; relecture #30 et banc couloir Lenny | Assemblage et parcours sec/mouillé/sec livrés ; calibration et piscine attendues | [#26], PR #25, #30, #35–#36 |
| G4 | J3 | Tester accélération, freinage et virages selon adhérence et relaxation | S3 | Livré 20/10/2026, anticipé depuis S6–S7 | Shaleena | Livré sur paramètres illustratifs ; calibration C6 distincte | [PR #29](https://github.com/ViscoCrowd/ViscoCrowd-simulation/pull/29) |
| G5 | J3 | Coupler guidage et exclusion ; vérifier confinement et contacts en groupe | S3–S7 | Banc livré 21/10 ; extension cible 17–23/11 | Lenny (banc), Hamza (extension proposée) | Livré sur couloir : 24 agents, contacts et confinement testés ; extension piscine à faire | [#34], PR #36–#37 |
| P1 | J4 | Construire bassin, rebords, échelles, plage et sortie selon C6 | S8 | 24–30/11/2026 | À attribuer avant S8 | À faire | Spécification §1 |
| P2 | J4 | Définir les transitions entre zones | S8–S9 | 24/11–07/12/2026 | À attribuer avant S8 | À faire | Spécification §2.7 |
| P3 | J4 | Implémenter capacité unitaire et durée de passage des échelles/rebords | S8–S9 | 24/11–07/12/2026 | À attribuer avant S8 | À faire | Spécification §2.7 |
| P4 | J4 | Faire circuler une foule sur le parcours complet | S8–S9 | 24/11–07/12/2026 | À attribuer avant S8 | À faire | Jalon 4 |
| P5 | J4 | Compter les évacués définitifs et les temps de sortie ; conserver N intérieur + N sorti | S9 | 01–07/12/2026 | À attribuer avant S8 | À faire | [#11] |
| P6 | J4 | Tester passages, blocages et absence de franchissements fantômes | S9 | 01–07/12/2026 | À attribuer avant S8 | À faire | Jalon 4 / PR #9 |

## Mesures et campagnes

| ID | Étape | Tâche / critère de fin | Semaines | Dates cibles | Responsable | État | Référence |
|---|---|---|---|---|---|---|---|
| M1 | Préparation J5 | Mesurer densité et encombrement, après la décision SciPy/Voronoï C1 | S8–S9 | 24/11–07/12/2026 | À attribuer avant S8 | À faire avant les campagnes | Spécification §3 |
| M2 | Préparation J5 | Corriger le jeu des contacts multiples ou mesurer et borner son influence sur la densité | S8–S9 | 24/11–07/12/2026 | Hamza (affectation #10) | En suivi ; requis avant les campagnes | [#10] |
| M3 | Préparation J5 | Vérifier les constantes de Weidmann dans la source primaire et adapter tests/figures si nécessaire | S8–S9 | 24/11–07/12/2026 | À attribuer avant S8 | À faire avant comparaison | [#12] |
| M4 | J5 | Étalonner un goulot sec seul, avec les mesures qualifiées M1–M3 | S9 | 01–07/12/2026 | À attribuer avant S8 | À faire avant E1–E4 | E0 |
| M5 | J5 | Comparer piscine sans et avec sol mouillé | S10–S11 | 08–21/12/2026 | À attribuer avant S8 | À faire après E0 | E1–E2 |
| M6 | J5 | Balayer adhérence, longueur mouillée, sorties et population | S10–S11 | 08–21/12/2026 | À attribuer avant S8 | À faire | E3–E4 |
| M7 | J5 | Répéter sur plusieurs graines et mesurer la variabilité | S10–S11 | 08–21/12/2026 | À attribuer avant S8 | À faire avec M5–M6 | Spécification §4 |
| M8 | J5 | Comparer débit/densité aux références et discuter le domaine de validité | S11 | 15–21/12/2026 | À attribuer avant S8 | À faire | Spécification §3 et §5 |
| M9 | J5 | Vérifier la sensibilité au pas de temps, à N et aux graines | S11 | 15–21/12/2026 | À attribuer avant S8 | À faire | Spécification §5 |

## Rapport et soutenance

| ID | Étape | Tâche / critère de fin | Semaines | Dates cibles | Responsable | État | Référence |
|---|---|---|---|---|---|---|---|
| R1 | J6 | Rédiger moteur, validation et limites au fil du développement ; première version en S5 | S3–S11 | Début 21/10 ; version complète cible 21/12 | Lenny, relecture des trois membres | En cours : chaîne de calcul, validation analytique et mesures du couloir rédigées | [Implémentation](../../report/sections/04-implementation.tex), [validation](../../report/sections/05-validation.tex), [#34] |
| R2 | J6 | Produire figures et tableaux avec unités, paramètres et graines | S10–S11 | 08–21/12/2026 | À attribuer avant S8 | À faire au fil des campagnes | [Manifeste](../../experiments/manifeste.yaml) |
| R3 | J6 | Rédiger l'analyse, répondre à la problématique et discuter les limites | S11 | 15–21/12/2026 | À attribuer avant S8 | À faire | Rapport, résultats et conclusion |
| R4 | J6 | Compléter bibliographie, contributions réelles et usages d'outils | S3–S11 | Début 21/10 ; cible 21/12 | Lenny, informations des trois membres | Usage des outils sur le banc documenté ; bibliographie et proportions à compléter | [Outils](../../report/sections/A2-outils.tex), cahier des charges §7 |
| R5 | J6 | Relire une version complète ; rejouer tests et figures depuis le code livré | S11 | 15–21/12/2026 | À attribuer avant S8 | À faire ; cible interne 21/12 | Rapport et code |
| R6 | J6 | Vérifier les fichiers remis et déposer sur Moodle | S14 | 05/01/2027 avant 23h59 | À attribuer avant S8 | À faire ; marge S12–S13 si corrections | Échéance officielle |
| R7 | J6 | Préparer transparents, démonstration et répartition de parole ; répéter | S14–S15 | 06–18/01/2027 avant 18h00 | À attribuer avant S8 | À faire | Soutenance 19/01/2027 |

## Pistes complémentaires non programmées

Les cinq tâches de l'addendum chutes quittent les créneaux S7–S9 du planning initial. Aucune
tâche des jalons 3 à 6 n'en dépend. C1 ([#19]) recueille l'avis sur l'extension ; une décision ultérieure
du groupe doit préciser la capacité disponible ou les tâches retirées avant de lui affecter
des dates. Une avance sur le moteur ne suffit pas à valider un changement de modèle.

| Tâche | État | Condition / référence |
|---|---|---|
| Glissade sur sol mouillé | Non programmé | Addendum chutes §1, décision C1 |
| Chute après bousculade | Non programmé | Addendum chutes §2, décision C1 |
| Agent à terre et relevage | Non programmé | Addendum chutes §3–4, décision C1 |
| Contournement local d'une personne à terre | Non programmé | Addendum chutes §5 ; distinct de l'obstacle fixe G2 |
| Propagation des chutes | Non programmé | Addendum chutes §3, décision C1 |
| Anticipation du mouvement futur des voisins | Non programmé | Extension au-delà du contournement réactif |
| Trébuchement distinct sur obstacle | Non programmé | Mécanisme absent de la spécification actuelle |

## Mise à jour et archive

Modifier ce document sur une branche de documentation. Toute livraison ou décision change
l'état de la ligne correspondante et ajoute sa référence (PR, issue ou compte rendu).
Réexaminer les dates et dépendances quand une tâche glisse ; une échéance passée ne signifie
jamais qu'une tâche est terminée.

Le [classeur initial du 13 octobre](archives/planning-initial-2026-10-13.xlsx) est conservé
**uniquement comme archive historique**, avec ses statuts et créneaux d'origine. Il contient
des informations périmées et ne doit pas servir au suivi courant. Il n'est pas une vue dérivée
du Markdown. Une éventuelle nouvelle vue Excel devra être générée depuis ce document et
vérifiée contre lui ; elle ne deviendra pas une seconde source à modifier séparément.

Les fichiers temporaires Excel `~$…` ne doivent pas être ajoutés aux commits.

[#10]: https://github.com/ViscoCrowd/ViscoCrowd-simulation/issues/10
[#11]: https://github.com/ViscoCrowd/ViscoCrowd-simulation/issues/11
[#12]: https://github.com/ViscoCrowd/ViscoCrowd-simulation/issues/12
[#13]: https://github.com/ViscoCrowd/ViscoCrowd-simulation/issues/13
[#16]: https://github.com/ViscoCrowd/ViscoCrowd-simulation/issues/16
[#17]: https://github.com/ViscoCrowd/ViscoCrowd-simulation/issues/17
[#18]: https://github.com/ViscoCrowd/ViscoCrowd-simulation/issues/18
[#19]: https://github.com/ViscoCrowd/ViscoCrowd-simulation/issues/19
[#20]: https://github.com/ViscoCrowd/ViscoCrowd-simulation/issues/20
[#26]: https://github.com/ViscoCrowd/ViscoCrowd-simulation/issues/26
[#31]: https://github.com/ViscoCrowd/ViscoCrowd-simulation/issues/31
[#34]: https://github.com/ViscoCrowd/ViscoCrowd-simulation/issues/34
