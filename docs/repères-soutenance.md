# Retrouver et expliquer nos choix

Point du **21 octobre 2026**. Cette fiche prépare la relecture avant soutenance ;
elle renvoie aux preuves et aux échanges, y compris aux hypothèses abandonnées.
Une issue fermée reste consultable. Le [journal](journal-decisions.md), les reviews
et les commits restent la trace détaillée ; on ne les réécrit pas pour effacer un essai.

## Décisions à savoir défendre

| Choix | Pourquoi, avec la portée des chiffres | Preuves à reprendre |
|---|---|---|
| Jacobi vectorisé | Davantage de balayages, mais environ deux fois moins de temps que Gauss-Seidel dans l'implémentation NumPy mesurée. Recherche d'une configuration admissible, sans garantie générale d'optimalité euclidienne. | [#13](https://github.com/ViscoCrowd/ViscoCrowd-simulation/issues/13), [rapport § 3](../report/sections/03-discretisation.tex) |
| Nesterov après 80 balayages | Sur le banc comparé au déclenchement immédiat : temps de projection multiplié par 2,2, restitution divisée par environ 1 100. Compromis empirique ; les taux théoriques convexes ne prouvent pas la convergence de nos contacts non convexes. | Tableaux de [#13](https://github.com/ViscoCrowd/ViscoCrowd-simulation/issues/13), [PR #46](https://github.com/ViscoCrowd/ViscoCrowd-simulation/pull/46) |
| Relecture de la vitesse après projection | Le déplacement admissible donne la vitesse suivante. Un choc contraint la vitesse normale relative ; deux disques à 2 et 0 m/s peuvent continuer ensemble à 1 m/s, sans s'arrêter absolument. | [Rapport § 3.4](../report/sections/03-discretisation.tex), [revue #46](https://github.com/ViscoCrowd/ViscoCrowd-simulation/pull/46) |
| Fast Marching et interpolation du guidage | Calcul d'ordre 1 ; aux crêtes, moyenner des directions opposées pouvait immobiliser un agent entre les nœuds. Le départage corrigé est local et déterministe, sans garantie de trajet continu optimal. | [#43](https://github.com/ViscoCrowd/ViscoCrowd-simulation/pull/43), `tests/test_eikonal.py` |
| Obstacle imposé dans la projection | Le guidage seul n'empêche pas les voisins de pousser un agent dans le pilier. Le domaine doit donc porter cette contrainte, avec vérification des espacements compatibles avec les diamètres. | [#49](https://github.com/ViscoCrowd/ViscoCrowd-simulation/pull/49), `experiments/couloir_obstacle.yaml` |
| Milieux comparés un paramètre à la fois | Même population et graines appariées pour séparer vitesse, relaxation et adhérence. Une mesure manquante refuse le protocole entier. Les paires·s sont une durée cumulée de contacts, pas une densité. | [#50](https://github.com/ViscoCrowd/ViscoCrowd-simulation/pull/50), [rapport § 6](../report/sections/06-resultats.tex) |
| Sortie définitive distincte du flux | Un aller-retour peut produire plusieurs passages pour un seul évacué. L'observable rétrospective traite les retours, mais ne réalise pas le retrait des agents du moteur. | [#47](https://github.com/ViscoCrowd/ViscoCrowd-simulation/pull/47), [#11](https://github.com/ViscoCrowd/ViscoCrowd-simulation/issues/11) |
| Provenance des archives | Commit et état des modifications sont capturés avant le calcul et revérifiés avant archivage. Ils ne constituent pas un hash complet d'un arbre modifié ni une surveillance continue. | [#45](https://github.com/ViscoCrowd/ViscoCrowd-simulation/pull/45), `tests/test_provenance.py` |
| Source primaire de Weidmann | Constantes 1,34 m/s, 1,913 pers/m² et 5,4 pers/m² contrôlées. Les 52 moyennes de vitesse et les 17 écarts-types de 12 sources sont deux statistiques distinctes ; 0,26 m/s n'est pas une tolérance universelle de validation. | [#51](https://github.com/ViscoCrowd/ViscoCrowd-simulation/pull/51), [#12](https://github.com/ViscoCrowd/ViscoCrowd-simulation/issues/12) |

Les confirmations de compréhension sont conservées dans [#13](https://github.com/ViscoCrowd/ViscoCrowd-simulation/issues/13) :
Shaleena le 19 octobre, Lenny le 21 octobre. Elles n'empêchent pas de reprendre
ensemble chaque démonstration avant la soutenance.

## Ce que les contre-exemples ont changé

- **Contacts multiples (#10/#48).** L'ancien diagnostic de défaut de position immobile
  a été requalifié en vitesse résiduelle liée à la tolérance. La décroissance en Δt²
  du jeu moyen d'une foule n'est pas reproduite. Perturber un agent de 10⁻¹² m change
  l'arrangement final de plus de 10⁻⁶ m ; cela mesure une sensibilité, pas une preuve
  de chaos ni une cause propre au processeur. Les 58 tests de projection passent,
  diagnostic lent compris. Le jeu des paires proches ne borne pas une densité.
- **Densité (#53).** Le double comptage de cellules pour des centres confondus a été
  corrigé. Le test lent de la borne de 2 % échoue sur macOS arm64 : moyenne appariée
  0,035154 pers/m², erreur standard 0,059588. La PR reste en demande de corrections
  scientifiques ; une CI rapide verte ne valide pas cette conclusion. L'incertitude,
  le protocole et la géométrie cible restent à traiter dans [#10](https://github.com/ViscoCrowd/ViscoCrowd-simulation/issues/10).
- **Piscine (#54).** Les plages trop étroites et les échelles proches d'un coin
  doivent être refusées pour le rayon considéré. La géométrie et les champs statiques
  n'implémentent pas encore les files, la capacité des passages ni la sortie absorbante.
  Les valeurs de [#26](https://github.com/ViscoCrowd/ViscoCrowd-simulation/issues/26)
  restent une proposition, distincte de la calibration collective.

## Relecture avant la présentation

Pour chaque ligne, repartir du problème, dessiner le contre-exemple, expliquer la
formule et ses unités, puis retrouver le test ou la mesure avec sa configuration,
ses graines et sa limite. Relancer les tests lents explicitement lorsqu'ils portent
la conclusion discutée ; la commande habituelle `pytest -m "not slow"` les exclut.
Vérifier enfin que les slides décrivent la version publiée dans le
[registre des livraisons](livraisons.md), et non toutes les propositions encore en PR.
