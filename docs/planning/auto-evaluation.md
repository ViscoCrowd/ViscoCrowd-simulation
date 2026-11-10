# Auto-évaluation hebdomadaire

Ce fichier recopie le tableau récapitulatif que le groupe remplit à chaque séance du mardi
(10h15, 2 h). Jusqu'au 3 novembre, il était tenu dans un classeur partagé. Il est maintenant
suivi ici pour que chaque semaine passe par une PR et reste relisible.

Le tableau dit ce que chacun a fait. Il ne remplace pas l'annexe du rapport sur la répartition
réelle du travail et ses proportions (tâche R4 du [planning](README.md)). Les numéros renvoient
aux PR et issues du dépôt.

Les trois premières semaines sont reprises telles quelles du classeur. Certaines cellules y
étaient coupées à l'export : on les recopie jusqu'à la coupure, sans compléter de mémoire.

## Semaine du 21 septembre 2026, séance du 22/09

| Membre | Travail réalisé | Temps |
|---|---|---|
| Hamza KARROUCHI | Recherche sur le sujet ; création du GitHub et du drive commun ; création du logo | 2 h |
| Shaleena LESUEUR | Recherche sur le sujet ; création du GitHub et du drive commun ; création du logo | 2 h |
| Lenny MONGRANDI | Recherche sur le sujet ; création du GitHub et du drive commun ; création du logo | 2 h |

## Semaine du 5 octobre 2026, séance du 06/10

Le classeur intitule cette semaine « 7 octobre ».

| Membre | Travail réalisé | Temps |
|---|---|---|
| Hamza KARROUCHI | Réflexion commune sur les valeurs à prendre en compte dans la simulation ; initialisation du dépôt (cellule coupée) | 2 h |
| Shaleena LESUEUR | Réflexion commune sur les valeurs à prendre en compte dans la simulation ; tunnel de Pantz (cellule coupée) | 2 h |
| Lenny MONGRANDI | Réflexion commune sur les valeurs à prendre en compte dans la simulation ; tunnel de Pantz (cellule coupée) | 2 h |

## Semaine du 12 octobre 2026, séance du 13/10

| Membre | Travail réalisé | Temps |
|---|---|---|
| Hamza KARROUCHI | Moteur : exclusion entre agents par projection itérative accélérée (#6, avec Lenny). Dépôt : CI sur `dev` et procédure de passage `dev` → `main` (#5), resynchronisation de `dev` après #3, identités Git unifiées par `.mailmap` (#14) | 2 h |
| Shaleena LESUEUR | Mesures : débit à travers une ligne et référence de Weidmann (#9). Documentation : spécification alignée sur la méthode de Jacobi (#7), relecture du correctif du Makefile (#3) | 2 h |
| Lenny MONGRANDI | Interface : aperçu de la piscine avec réglage des paramètres et chronomètre (#4). Moteur : participation à l'exclusion entre agents (#6). Organisation : commande d'aide du Makefile (#2, #3), critères de validation et planning clarifiés (#15, avec Hamza) | 2 h |

## Semaine du 19 octobre 2026, séance du 20/10

| Membre | Travail réalisé | Temps |
|---|---|---|
| Hamza KARROUCHI | Moteur, avec Lenny : refus des positions et rayons non finis (#21), immuabilité de `State` et commande Docker (#22), figures du jalon 2 et contrôle de la dérive des dépendances (#23). Guidage et piscine : champ eikonal (#43), contournement du pilier (#49), géométrie et champs de guidage de la piscine (#54), évacuation complète avec passages un par un (#55, avec Lenny). Mesures : provenance des archives (#45), sorties définitives (#47), densité de Voronoï (#53, avec Lenny et Shaleena), goulot sec E0 selon Seyfried (#56), relation vitesse–espacement calée sur E0 (#58, avec Lenny), comparaison du sol mouillé (#50). Tests et documentation : sensibilité des contacts (#48), discrétisation dans le rapport (#46), constantes de Weidmann vérifiées (#51), suivi des livraisons et versions figées dans la CI (#44, #52, #60) | 2 h |
| Shaleena LESUEUR | Milieux : accélération bornée par l'adhérence (#25), virages et convergence en pas de temps (#29), guidage et carte des milieux assemblés (#30). Fiabilisation : paramètres non finis refusés dans la projection, la boîte et le débit ; docstrings et spécification remises d'accord avec le code ; devcontainer et Dockerfile réparés. Sources : vitesse de marche dans l'eau vérifiée (C6, #71). Outillage : scénarios lents sous Windows en CI (#66), participation à Voronoï (#53) et aux outils de relecture et de campagnes (#67, #68, #70) | 2 h |
| Lenny MONGRANDI | Couloir : géométrie et carte des milieux (#35), foule guidée sur plusieurs milieux (#36), validation rédigée (#38). Interface : échelle du plan et sortie éloignée (#27), animation et export des trajectoires (#37), relecture des évacuations piscine archivées (#67). Entrées/sorties : simulations depuis YAML et archives (#32), reprise d'une campagne interrompue (#68), mesures de performances et archives allégées (#70), PR empilées et scénarios lents en CI (#66), début de l'outil de rejeu des projections en échec (#69). Livraisons : cycle `dev`/`main`/tags/releases (#40), publication du jalon 2 (#41, #42), suivi et planning (#24, #33), co-auteur des correctifs #21 à #23, #55 et #58 | 2 h |

## Semaine du 26 octobre 2026, séance du 27/10

| Membre | Travail réalisé | Temps |
|---|---|---|
| Hamza KARROUCHI | Chutes (module facultatif) : glissade, effet domino, relevage et contournement ; intégration au scénario piscine et carte 2D des incidents. Qualité : tirages aléatoires centralisés et appels directs interdits ; test croisé de la sortie absorbante et de la conservation des effectifs (#11). Relecture de #69 (modifications demandées puis approbation) et de #72 | 2 h |
| Shaleena LESUEUR | Aucune contribution tracée dans le dépôt cette semaine (à compléter si travail hors dépôt) | 2 h |
| Lenny MONGRANDI | Aucune contribution tracée dans le dépôt cette semaine (à compléter si travail hors dépôt) | 2 h |

## Semaine du 2 novembre 2026, séance du 03/11

| Membre | Travail réalisé | Temps |
|---|---|---|
| Hamza KARROUCHI | Piscine : protocole apparié E1/E2 sec contre mouillé (#77, avec Shaleena), résultats sur 10 graines dans le rapport (#83), corrections de l'estimateur j_s, du tableau E2 et de l'analyse des virages. Mesures : archives à pas espacés refusées et filtrage des agents actifs (#74). Chutes : fusion du modèle et de son intégration (#78, #82). Outillage : `numpy.random` refusé hors de `core.rng` (#80), contrôle croisé des sorties absorbantes (#81), script PowerShell (#76, avec Shaleena). Documentation : tests lents de la CI (#79), repères de soutenance et compilation du rapport sur `dev` (#75, avec Shaleena) | 2 h |
| Shaleena LESUEUR | Campagnes : balayage de la piscine un paramètre à la fois contre un témoin sec (M6, #84) ; premiers balayages E3/E4, qui font apparaître le bouchage de la porte à 0,8 m. Tests : chaque sol vérifié pendant une évacuation (G3, #72). Relecture : chiffres des repères de soutenance (#75), options de pytest dans `run.ps1` (#76), participation à E1/E2 (#77) et au diagnostic des projections (#69), branches en cours remises à jour avec `dev` | 2 h |
| Lenny MONGRANDI | Relecture et intégration : 7 branches mises à jour avec `dev` avant fusion ; chute bornée par l'adhérence, vérifications, mesures et limites ajoutées au modèle de chutes ; test d'invariant corrigé pour détecter tout usage de `numpy.random` ; périmètre réel des tests lents et écarts de relecture des sorties documentés. Diagnostic et rapport : fusion de l'outil de rejeu des projections en échec (#69), résultats E1/E2 intégrés au rapport (#86) | 2 h |

## Semaine du 9 novembre 2026, séance du 10/11

Cette semaine couvre ce qui a été fait après la séance du 3 novembre, jusqu'au 10 novembre.
Elle est reconstituée à partir des PR fusionnées et des relectures enregistrées sur GitHub.

| Membre | Travail réalisé | Temps |
|---|---|---|
| Hamza KARROUCHI | Piscine : relation vitesse–espacement branchée sur le scénario, avec un meneur cherché seulement dans le même milieu (eau ou plage) ; désactivée par défaut dans `piscine.yaml` (#100, #57). Obstacles fixes sur la plage (G5, #103). Densité : biais lié à la tolérance mesuré au goulot sur 10 graines, sans effet décelable entre 10⁻⁷ et 10⁻⁶ m (p = 1,000) et un écart de +0,021 pers/m² au pas de 0,005 s (#101, #10). Chutes : chute par bousculade et observables de cascade (#102). Balayages : vitesse sur sol mouillé et taux de chute ajoutés (#104). Sortie : repère `N / (1,3 w)` documenté et confronté au débit maximal de Weidmann, état absorbant acté (#105, #11). Relectures de #94, #95 et de la publication du jalon 3 (#112) | 2 h |
| Shaleena LESUEUR | Valeurs de référence C6 figées et E1/E2 refaits au facteur de panique 1,5 (#109). Balayage du temps de relaxation commun aux trois sols (#108). Interface : `ParametresMilieu` du modèle réutilisé (#106). CLI : sorties en UTF-8 même redirigées sous Windows (#107). Obstacles refusés dès la lecture s'ils laissent un passage trop étroit (#110) ou recouvrent l'arrivée d'un site (#114). Publication du jalon 3 : préparation (#111), PR `dev` → `main` (#112), tag `jalon-3` et release, resynchronisation (#113). Relectures de #91 à #95, #97 à #99, et de #100 à #105 avec modifications demandées avant approbation | 2 h |
| Lenny MONGRANDI | Fin de la séance du 3/11 : seuils des chutes déplacés dans `ParametresChutes` (#88), états sans légende refusés dans les mesures de densité (#89), fonctions de campagne rendues publiques pour le balayage (#90), effectifs par état recomptés depuis les événements (#91), repères de soutenance et README actualisés (#92, #93), simulation lancée et relue depuis le Makefile (#97), sensibilité des observables à l'espacement K des archives (#98), planning aligné au 3/11 (#99). Après relecture, explication du débit E1 présentée comme une hypothèse dans le rapport (#94) et préfixes de branche alignés sur les types de commit (#95). Le 9/11 : branches de #101 et #105 remises à jour avec `dev`, effet de la tolérance relâchée à 10⁻⁵ m signalé (#10), freinage présenté comme une hypothèse et décision du 7/11 datée (#11) ; approbation de #100, #104 et #114. Ce tableau et la mise à jour du planning au 10/11 | 2 h |
