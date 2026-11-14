# Planning ViscoCrowd 2026–2027

**État au 10 novembre 2026.** Ce document est la source de référence du planning : tâches,
dates, responsabilités et suivi sont modifiés ici, avec un diff relisible en pull request.
Les créneaux futurs et les affectations marquées **(proposé)** sont une proposition de travail,
à confirmer selon les disponibilités du groupe ; ils ne constituent pas un accord déjà obtenu.

## Calendrier

Convention de planification : **S1 commence le mardi 6 octobre 2026**, date de la spécification.
C'est un repère de calendrier, pas une preuve de la date réelle de début des travaux ou de
l'acceptation du sujet. Au 10 novembre, nous sommes en S6. Les jalons 1 et 2 sont livrés en
avance sur les cibles S2–S5 du planning initial. Le jalon 3, prévu en S6–S7, est publié depuis
le 9 novembre (tag `jalon-3`). Ces créneaux ne restent donc pas réservés à du développement
déjà terminé.

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
| L1 | J0 | Sujet et problématique rédigés | S2 | 13/10/2026 | Groupe | Livré ; questions de cadrage validées le 03/11 (C1) | [Cadrage](../validation-sujet.md) |
| L2 | J0 | Dépôt et méthode de contribution | S2 | 13/10/2026 | Groupe | Livré ; répartition à compléter en C2 | [Contribution](../../CONTRIBUTING.md) |
| L3 | J1 | Mouvement simple, position/vitesse semi-implicites, confinement et dissipation | S2 | 13/10/2026 | Attribution détaillée à consigner dans le rapport | Validé ; sécurisation C3–C4 livrée depuis | [Moteur](../../README.md#validation-du-moteur) |
| L4 | J2 | Contact de deux agents, voisins, groupes denses et tests de stabilité | S2 | 13/10/2026 | Attribution détaillée à consigner dans le rapport | Validé avec limite de contacts multiples #10 | [PR #6](https://github.com/ViscoCrowd/ViscoCrowd-simulation/pull/6), [#10] |
| L5 | J2 | Jacobi vectorisé et Nesterov après 80 balayages | S2 | 13/10/2026 ; suivi clôturé 21/10 | Hamza (suivi #13), décision des trois membres | Validé collectivement ; confirmations personnelles et rapport #46 vérifiés ; historique conservé dans #13 et le mémo de soutenance | [#13], [journal](../journal-decisions.md), [mémo](../repères-soutenance.md) |
| L6 | J5, brique anticipée | Passages et débit sur une ligne, référence de Weidmann | S2 | 13/10/2026 | Shaleena (PR #9 / issue #8) | Livré ; source primaire vérifiée dans #51/#12 ; densité et état de sortie restent ouverts | [PR #9](https://github.com/ViscoCrowd/ViscoCrowd-simulation/pull/9), [#11], [#12] |

<a id="cadrage-et-prerequis"></a>

## Cadrage et prérequis

Les prérequis moteur C3–C4 sont livrés. Le jalon 3 dispose maintenant d'un banc de couloir
avec une carte par bandes réelle, un guidage analytique et un groupe en contact (G1/G5).
Le guidage eikonal et le pilier contraint sont livrés dans les PR #43 et #49.
La brique de géométrie/carte/guidage statique de la piscine est livrée dans #54 et son
intégration dynamique dans #55. Les valeurs C6 sont figées depuis le 6 novembre 2026 (#109),
et les obstacles de la plage sont livrés (#103, #110). Le jalon 3 (C6, G1–G5) est publié sur
`main` le 9 novembre 2026 par la PR #112, avec le tag `jalon-3` et sa release ; `dev` a été
resynchronisée dans #113. Le suivi de répartition C2 reste ouvert.
C1 est levé : l'enseignant a validé SciPy/Voronoï (M1), le dimensionnement et l'inclusion
des chutes en séance le 3 novembre 2026. Le scénario piscine dépend
ensuite du guidage et des milieux validés. Les campagnes E1–E4 dépendent des
mesures de densité, de l'étalonnage E0, de la maîtrise du biais #10 et de la reproductibilité.

| ID | Étape | Tâche / critère de fin | Semaines | Dates cibles | Responsable | État | Référence |
|---|---|---|---|---|---|---|---|
| C1 | Cadrage | Consigner date/canal/destinataires/contenu de l'accord ; obtenir les réponses SciPy/Voronoï, dimensionnement et avis sur les chutes | S2 | Validé le 03/11/2026, consigné le 10/11/2026 | Lenny (coordination du suivi) | Livré : accord oral de O. Pantz en séance le 03/11/2026, sans réserve rapportée, sur SciPy/Voronoï, le dimensionnement et l'inclusion des chutes dans le rendu ; #19 close le 03/11 | [#19], [questions et trace](../validation-sujet.md#trace-de-validation) |
| C2 | Organisation | Consigner la répartition confirmée et les périodes d'entreprise/congés ; ajuster la charge | S2 | Cible 19/10 passée | Lenny (coordination), informations des trois membres | Confirmation cochée dans #20 ; tableau d'auto-évaluation hebdomadaire recopié dans le dépôt, à jour au 10/11 ([auto-évaluation](auto-evaluation.md)) ; répartition des tâches restantes, disponibilités et charge restent à consigner | [#20], calendrier ci-dessus, [auto-évaluation](auto-evaluation.md) |
| C3 | Moteur | Rejeter les valeurs non finies ; tests en projection stricte et permissive | S2 | Livré 19/10/2026 | Hamza ; compléments Shaleena le 20/10 | Livré, issue clôturée | [#16], [PR #21](https://github.com/ViscoCrowd/ViscoCrowd-simulation/pull/21) |
| C4 | Moteur | Protéger les tableaux de State ; tester les alias d'entrée et entre états | S2 | Livré 19/10/2026 | Hamza | Livré, issue clôturée | [#17], [PR #22](https://github.com/ViscoCrowd/ViscoCrowd-simulation/pull/22) |
| C5 | Reproductibilité | Aligner l'interpréteur Docker/Makefile ; exécuter valider et figures dans le conteneur | S2–S3 | Livré 19/10 ; CI revérifiée 21/10 | Hamza ; compléments outillage Shaleena le 20/10 | Livré ; validation et figures exécutées en CI Docker ; versions figées étendues aux jobs Python dans #44 | [#18], [PR #22](https://github.com/ViscoCrowd/ViscoCrowd-simulation/pull/22), [PR #44] |
| C6 | J3 | Définir la géométrie commune moteur/affichage, les paramètres des trois milieux avec unités et les critères de guidage | S4 | 27/10–02/11/2026 | Hamza (proposé) ; valeurs figées par Shaleena avec l'accord du groupe | Livré : contrat et géométrie de couloir avec relecture ; pistes de sources pour l'eau et le sol mouillé déposées le 21/10 ; géométrie/carte/guidage statique livrés dans #54 ; valeurs de référence figées le 06/11/2026 (panique 1,5 ; τ = 0,5 s partout ; vitesse dans l'eau vérifiée dans #71), publiées dans `jalon-3` le 09/11/2026 ; a_max de l'eau toujours à 1,6 m/s² dans `piscine.yaml`, à passer à 1,67 m/s² à la prochaine relance des balayages | [#26], [PR #30](https://github.com/ViscoCrowd/ViscoCrowd-simulation/pull/30) |
| C7 | Reproductibilité | Lire les configurations YAML et sauvegarder les trajectoires .npz ; vérifier leur relecture à graine fixée | S3 | Livré 21/10/2026, anticipé depuis S5 | Lenny ; commit Git des archives Hamza | Livré pour trois bancs, dont couloir avec relecture animée ; provenance du code livrée dans #45 (commit et état des modifications, avec limites documentées) ; population fixe, campagnes piscine à raccorder | [#31], [PR #32](https://github.com/ViscoCrowd/ViscoCrowd-simulation/pull/32), [PR #45] |

## Guidage, milieux et scénario

| ID | Étape | Tâche / critère de fin | Semaines | Dates cibles | Responsable | État | Référence |
|---|---|---|---|---|---|---|---|
| G1 | J3 | Guider un agent dans un couloir sec vers une sortie ; vérifier direction et arrivée | S3 | Livré 21/10/2026, anticipé depuis S6 | Lenny | Livré : guidage analytique sans obstacle, arrivée et convergence testées | [#34], PR #35–#36 |
| G2 | J3 | Calculer le champ eikonal et tester un détour autour d'un obstacle fixe | S6–S7 | Livré 21/10/2026, anticipé depuis S6–S7 | Hamza | Livré dans #43 : Fast Marching d'ordre 1, couloir exact (10⁻¹³ s), convergence mesurée, détour sans contact d'un agent et de 12 agents | Spécification §2.6, [PR #43] |
| G3 | J3 | Adapter la vitesse à l'eau, au sol mouillé et au sec | S2–S7 | Briques livrées 19–21/10 ; intégration piscine livrée le 06/11/2026 | Shaleena ; relecture #30 et banc couloir Lenny ; comparaison un paramètre à la fois Hamza | Livré : assemblage et parcours sec/mouillé/sec livrés ; comparaison séparée de `s`, `τ` et `a_max` livrée dans #50 ; sols vérifiés pendant une évacuation piscine dans #72 ; valeurs figées le 06/11/2026 ; classe `ParametresMilieu` unique dans #106 | [#26], PR #25, #30, #35–#36, [PR #50], PR #72, #106, #109 |
| G4 | J3 | Tester accélération, freinage et virages selon adhérence et relaxation | S3 | Livré 20/10/2026, anticipé depuis S6–S7 | Shaleena | Livré sur paramètres illustratifs ; calibration C6 distincte | [PR #29](https://github.com/ViscoCrowd/ViscoCrowd-simulation/pull/29) |
| G5 | J3 | Coupler guidage et exclusion ; vérifier confinement et contacts en groupe | S3–S7 | Banc livré 21/10 ; obstacle livré le 21/10 ; extension piscine livrée le 06/11/2026 | Lenny (banc), Hamza (obstacle, plage), Shaleena (contrôles) | Livré : sur couloir, 24 agents, contacts et confinement testés ; pilier contourné et contraint livré dans #49 ; obstacles de la plage pris en compte par le guidage et la projection dans #103 ; obstacles laissant un passage plus étroit qu'un diamètre refusés dès la lecture de la configuration dans #110, comme ceux qui recouvrent l'arrivée d'un site dans #114 | [#34], PR #36–#37, [PR #49], PR #103, #110, #114 |
| P1 | J4 | Construire bassin, rebords, échelles, plage et sortie selon C6 | S8 | Brique livrée le 21/10 ; scénario cible 24–30/11/2026 | Hamza (PR #54) | Géométrie, carte et sites livrés dans #54 ; scénario complet livré dans #55 | Spécification §1, [PR #54] |
| P2 | J4 | Définir les transitions entre zones | S8–S9 | Livré le 22/10/2026, anticipé | Hamza, avec Lenny | Livré dans #55 : états eau, franchissement, plage et sorti | Spécification §2.7, PR #55 |
| P3 | J4 | Implémenter capacité unitaire et durée de passage des échelles/rebords | S8–S9 | Livré le 22/10/2026, anticipé | Hamza, avec Lenny | Livré dans #55 ; durées encore à calibrer (#26) | Spécification §2.7, PR #55 |
| P4 | J4 | Faire circuler une foule sur le parcours complet | S8–S9 | Livré le 22/10/2026, anticipé | Hamza, avec Lenny | Livré dans #55 : 100 agents, tous sortis sur les 10 graines de E1 | Jalon 4, PR #55 |
| P5 | J4 | Compter les évacués définitifs et les temps de sortie ; conserver N intérieur + N sorti | S9 | Livré le 22/10–09/11/2026 | Hamza | Livré : observable #47, état absorbant #55, contrôle croisé #81 ; repère `N / (J w)` (J = 1,225, Weidmann) confronté et état absorbant acté dans #105, fusionnée le 09/11/2026 ; #11 close à la main le 10/11/2026, une fusion vers `dev` ne fermant pas l'issue | [#11], [PR #47], PR #55, PR #81, [PR #105] |
| P6 | J4 | Tester passages, blocages et absence de franchissements fantômes | S9 | 01–07/12/2026 | À attribuer avant S8 | En cours : tests de #55 et #81 ; faux bouchages de la porte à corriger (#85) | Jalon 4 / PR #9, #85 |

## Mesures et campagnes

| ID | Étape | Tâche / critère de fin | Semaines | Dates cibles | Responsable | État | Référence |
|---|---|---|---|---|---|---|---|
| M1 | Préparation J5 | Mesurer densité et encombrement, après la décision SciPy/Voronoï C1 | S8–S9 | Livré le 22/10/2026, anticipé | Hamza, avec Lenny et Shaleena (PR #53) | Livré dans #53 ; test de permutation apparié à la place de la borne de 2 % ; usage de SciPy pour Voronoï validé le 03/11 (C1) | [#19], [PR #53], [#10] |
| M2 | Préparation J5 | Corriger le jeu des contacts multiples ou mesurer et borner son influence sur la densité | S8–S9 | Livré le 09/11/2026, anticipé ; diagnostic partiel livré le 21/10 | Hamza (affectation #10) | Livré dans #101 : biais mesuré au goulot E0 sur 10 graines appariées. Entre les tolérances 10⁻⁷ et 10⁻⁶ m, aucun effet décelable (p = 1,000, écart maximal 6,9 × 10⁻⁴ pers/m²). À 10⁻⁵ m, la densité monte de 0,12 % en moyenne. Au pas de 0,005 s au lieu de 0,01 s, l'écart moyen est de +0,021 pers/m² (p = 0,270), toujours sous 3,3 %. #10 à clore à la main, une fusion vers `dev` ne fermant pas l'issue | [#10], [PR #48], [PR #46], [PR #101] |
| M3 | Préparation J5 | Vérifier les constantes de Weidmann dans la source primaire et adapter tests/figures si nécessaire | S8–S9 | Livré le 21/10/2026, anticipé depuis S8–S9 | Hamza, relecture et corrections Lenny | Livré dans #51, issue #12 clôturée : constantes, forme, sommet et domaine conformes (p. 43, 53, 62–64) ; référence et interprétation de la dispersion corrigées ; 78 tests de débit passent ; aucune figure à reprendre | [#12], [PR #51] |
| M4 | J5 | Étalonner un goulot sec seul, avec les mesures qualifiées M1–M3 | S9 | Banc livré le 22/10/2026 ; activation piscine validée le 10/11/2026 | Hamza, avec Lenny pour #58 et #116 | Banc E0 livré (#56) ; relation vitesse–espacement proposée (#58), puis branchée sur la piscine dans #100 le 09/11/2026, avec un meneur cherché seulement dans le même milieu (eau ou plage). Activée dans `piscine.yaml` à T = 0,35 s, dans l’eau et sur la plage, par #116 ; règle, valeur de T et application dans l’eau validées par les trois membres le 10/11/2026 (#57) | E0, [#57], [PR #100], [PR #116](https://github.com/ViscoCrowd/ViscoCrowd-simulation/pull/116) |
| M5 | J5 | Comparer piscine sans et avec sol mouillé | S10–S11 | Première campagne livrée le 03/11/2026 ; refaite le 06/11 au facteur de panique 1,5, puis le 10/11 à T = 0,35 s | Hamza, avec Shaleena ; relance #116 par Lenny | Protocole #77, premiers résultats sur 10 graines dans #86 ; référence régulée #116 : t100 sec = 51,95 ± 1,91 s, mouillé = 51,83 ± 1,68 s ; Δt50 = +0,01 ± 0,02 s, positif sur 8 graines sur 10. E1/E2 à refaire après la correction de la porte (#85) | E1–E2, PR #77, PR #86, PR #116 |
| M6 | J5 | Balayer adhérence, longueur mouillée, sorties et population | S10–S11 | Outil livré le 02/11/2026 ; campagne finale 08–21/12/2026 | Shaleena (proposé dans la relecture de #83) | Outil `balayer-piscine` et premiers balayages livrés ; balayage du temps de relaxation commun aux trois sols (#108), de la vitesse sur sol mouillé et du taux de chute (#104) ajoutés le 06–09/11 ; balayage de T = 0,25, 0,35 et 0,5 s sur les graines 1 à 10 livré le 10/11 (#116) ; porte à arrondir (#85) avant de balayer largeur de porte et population | E3–E4, [balayages](../balayages-piscine.md) |
| M7 | J5 | Répéter sur plusieurs graines et mesurer la variabilité | S10–S11 | 08–21/12/2026 | À attribuer avant S8 | En cours : 10 graines dans #84 et #86 ; à reprendre sur la campagne finale | Spécification §4 |
| M8 | J5 | Comparer débit/densité aux références et discuter le domaine de validité | S11 | 15–21/12/2026 | À attribuer avant S8 | À faire | Spécification §3 et §5 |
| M9 | J5 | Vérifier la sensibilité au pas de temps, à N et aux graines | S11 | 15–21/12/2026 | À attribuer avant S8 | En cours : `dt` au facteur 1,5 mesuré dans #84 ; reste la configuration finale | Spécification §5 |

## Rapport et soutenance

Le [mémo des choix et contre-exemples](../repères-soutenance.md) conserve les renvois
aux anciennes issues, reviews et preuves à reprendre avant la présentation.

| ID | Étape | Tâche / critère de fin | Semaines | Dates cibles | Responsable | État | Référence |
|---|---|---|---|---|---|---|---|
| R1 | J6 | Rédiger moteur, validation et limites au fil du développement ; première version en S5 | S3–S11 | Début 21/10 ; version complète cible 21/12 | Lenny, Hamza (discrétisation, premiers résultats), relecture des trois membres | En cours : chaîne de calcul, validation analytique et mesures du couloir rédigées ; comparaison du mouillé (§ 6, figure 7) livrée dans #50 ; discrétisation (§ 3) et Weidmann (§ 5) livrés dans #46/#51 ; scénario et analyse finale à compléter | [Implémentation](../../report/sections/04-implementation.tex), [validation](../../report/sections/05-validation.tex), [#34], [PR #46], [PR #50], [PR #51] |
| R2 | J6 | Produire figures et tableaux avec unités, paramètres et graines | S10–S11 | 08–21/12/2026 | À attribuer avant S8 | À faire au fil des campagnes | [Manifeste](../../experiments/manifeste.yaml) |
| R3 | J6 | Rédiger l'analyse, répondre à la problématique et discuter les limites | S11 | 15–21/12/2026 | À attribuer avant S8 | À faire | Rapport, résultats et conclusion |
| R4 | J6 | Compléter bibliographie, contributions réelles et usages d'outils | S3–S11 | Début 21/10 ; cible 21/12 | Lenny, informations des trois membres | Usage des outils sur le banc et lors des reviews #43–#54 documenté ; sources de discrétisation et Weidmann vérifiées ; bibliographie finale et proportions à compléter | [Outils](../../report/sections/A2-outils.tex), cahier des charges §7 |
| R5 | J6 | Relire une version complète ; rejouer tests et figures depuis le code livré | S11 | 15–21/12/2026 | À attribuer avant S8 | À faire ; cible interne 21/12 | Rapport et code |
| R6 | J6 | Vérifier les fichiers remis et déposer sur Moodle | S14 | 05/01/2027 avant 23h59 | À attribuer avant S8 | À faire ; marge S12–S13 si corrections | Échéance officielle |
| R7 | J6 | Préparer transparents, démonstration et répartition de parole ; répéter | S14–S15 | 06–18/01/2027 avant 18h00 | À attribuer avant S8 | À faire | Soutenance 19/01/2027 |

<a id="pistes-complémentaires-non-programmées"></a>

## Chutes et pistes complémentaires

Le module de chutes (glissade, domino, relevage, contournement) a été fusionné le 3 novembre
dans #78 et #82, puis complété le 6 novembre par la chute par bousculade et les observables de
cascade (#102). L'enseignant a validé son inclusion dans le rendu en séance le 3 novembre (C1,
[#19]). Il reste désactivé par défaut et non calibré : avant d'en tirer des résultats, il faut
calibrer ses taux et décider de son activation dans les campagnes. Ces deux tâches sont suivies
dans [#130] ; aucune tâche des jalons 3 à 6 n'en dépend.

| Tâche | État | Condition / référence |
|---|---|---|
| Glissade sur sol mouillé | Code livré dans #78 et #82, désactivé par défaut | Addendum chutes §1 ; inclusion validée (C1) |
| Chute après bousculade | Code livré dans #102, désactivé par défaut | Addendum chutes §2 ; inclusion validée (C1) |
| Agent à terre et relevage | Code livré dans #78 et #82, désactivé par défaut | Addendum chutes §3–4 ; inclusion validée (C1) |
| Contournement local d'une personne à terre | Code livré dans #78 et #82, désactivé par défaut | Addendum chutes §5 ; distinct de l'obstacle fixe G2 |
| Propagation des chutes | Code livré dans #78 et #82, désactivé par défaut | Addendum chutes §3 ; inclusion validée (C1) |
| Calibrer les taux de chute et décider de l'activation dans les campagnes | À programmer ([#130]) | Addendum chutes §8 ; balayage de `lambda_chute` outillé dans #104 |
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
[#130]: https://github.com/ViscoCrowd/ViscoCrowd-simulation/issues/130
[#20]: https://github.com/ViscoCrowd/ViscoCrowd-simulation/issues/20
[#26]: https://github.com/ViscoCrowd/ViscoCrowd-simulation/issues/26
[#31]: https://github.com/ViscoCrowd/ViscoCrowd-simulation/issues/31
[#34]: https://github.com/ViscoCrowd/ViscoCrowd-simulation/issues/34
[PR #43]: https://github.com/ViscoCrowd/ViscoCrowd-simulation/pull/43
[PR #44]: https://github.com/ViscoCrowd/ViscoCrowd-simulation/pull/44
[PR #45]: https://github.com/ViscoCrowd/ViscoCrowd-simulation/pull/45
[PR #46]: https://github.com/ViscoCrowd/ViscoCrowd-simulation/pull/46
[PR #47]: https://github.com/ViscoCrowd/ViscoCrowd-simulation/pull/47
[PR #48]: https://github.com/ViscoCrowd/ViscoCrowd-simulation/pull/48
[PR #49]: https://github.com/ViscoCrowd/ViscoCrowd-simulation/pull/49
[PR #50]: https://github.com/ViscoCrowd/ViscoCrowd-simulation/pull/50
[PR #51]: https://github.com/ViscoCrowd/ViscoCrowd-simulation/pull/51

[#57]: https://github.com/ViscoCrowd/ViscoCrowd-simulation/issues/57
[PR #53]: https://github.com/ViscoCrowd/ViscoCrowd-simulation/pull/53
[PR #54]: https://github.com/ViscoCrowd/ViscoCrowd-simulation/pull/54
[PR #100]: https://github.com/ViscoCrowd/ViscoCrowd-simulation/pull/100
[PR #101]: https://github.com/ViscoCrowd/ViscoCrowd-simulation/pull/101
[PR #105]: https://github.com/ViscoCrowd/ViscoCrowd-simulation/pull/105
