# Retrouver et expliquer nos choix

Point du **27 octobre 2026**. Cette fiche prépare la relecture avant soutenance ;
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
| Vitesse–espacement de Tordeux ($T = 0{,}35\text{ s}$) | Sans espacement, le débit E0 vaut 1,9 à 2,5 fois la mesure de Seyfried (+150 %). Avec $T = 0{,}35\text{ s}$, l'écart moyen passe à 2,8 % sur N = 60, validé à 6,6 % sur N = 40 et 9,7 % sur N = 20. Ordre strict par temps eikonal pour exclure les cycles de blocage mutuel. | [#57](https://github.com/ViscoCrowd/ViscoCrowd-simulation/issues/57), [PR #58](https://github.com/ViscoCrowd/ViscoCrowd-simulation/pull/58), [journal](journal-decisions.md) |
| Seuil de saturation du sol mouillé | À $v_0 = 1{,}34\text{ m/s}$ (facteur panique 1), le mouillé freine exactement comme le sec ($0{,}6566\text{ m}$), car l'adhérence ne sature qu'au-delà de $a_{\max} \cdot \tau = 1{,}65\text{ m/s}$. L'effet inertiel n'apparaît qu'au-delà (panique $\ge 1{,}3$, $+9\text{ \%}$ à $2{,}5\text{ m/s}$) ou dans les virages serrés. | [#26](https://github.com/ViscoCrowd/ViscoCrowd-simulation/issues/26), [PR #72](https://github.com/ViscoCrowd/ViscoCrowd-simulation/pull/72), [journal](journal-decisions.md) |
| Refus des archives espacées ($K > 1$) pour les observables | L'archivage tous les $K$ pas allège le disque mais perd les positions intermédiaires. Dériver la vitesse, intégrer la densité de Voronoï ou interpoler un passage sur une archive espacée fausse les résultats physiques. Seuls la relecture et les logs précalculés acceptent $K > 1$. | [#73](https://github.com/ViscoCrowd/ViscoCrowd-simulation/issues/73), [PR #74](https://github.com/ViscoCrowd/ViscoCrowd-simulation/pull/74), [performances](performances.md) |
| Diagnostic rejouable des projections non convergées | Enregistre sans pickle l'instantané fautif sous `.diagnostic.npz` avec domaine, paramètres effectifs et graine. Permet de rejouer et de comparer un budget d'itérations supérieur sans relancer toute la simulation. | [#64](https://github.com/ViscoCrowd/ViscoCrowd-simulation/issues/64), [PR #69](https://github.com/ViscoCrowd/ViscoCrowd-simulation/pull/69), [diagnostic](diagnostic-projection.md) |

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
  corrigé. L'ancienne borne arbitraire de 2 % échouait sur macOS arm64 (moyenne appariée
  0,035154 pers/m², erreur standard 0,059588 sur huit graines) : elle a été remplacée par
  un test de permutation apparié exact sans hypothèse de normalité ($p = 0{,}633$ sur x86-64,
  $0{,}539$ sur arm64). Cela montre l'absence de détection à huit graines, pas une preuve
  d'absence d'effet ; borner l'amplitude sur la géométrie cible reste suivi dans [#10](https://github.com/ViscoCrowd/ViscoCrowd-simulation/issues/10).
- **Piscine (#54/#55).** Les plages trop étroites et les échelles proches d'un coin
  sont refusées pour le rayon considéré. Le scénario complet à quatre états (`EAU`,
  `FRANCHISSEMENT`, `PLAGE`, `SORTI`), la capacité unitaire des sites et la sortie
  absorbante ont été intégrés dans [#55](https://github.com/ViscoCrowd/ViscoCrowd-simulation/pull/55).
  Les valeurs numériques de [#26](https://github.com/ViscoCrowd/ViscoCrowd-simulation/issues/26)
  restent une proposition soumise à la validation collective avant les campagnes finales.

## Relecture avant la présentation

Pour chaque ligne, repartir du problème, dessiner le contre-exemple, expliquer la
formule et ses unités, puis retrouver le test ou la mesure avec sa configuration,
ses graines et sa limite. Relancer les tests lents explicitement lorsqu'ils portent
la conclusion discutée ; la commande habituelle `pytest -m "not slow"` les exclut.
Vérifier enfin que les slides décrivent la version publiée dans le
[registre des livraisons](livraisons.md), et non toutes les propositions encore en PR.

## Questions types du jury et arguments de défense

### Q1 : Pourquoi avoir choisi un algorithme de Jacobi vectorisé plutôt que Gauss-Seidel ?
- **Réponse :** Dans un langage de haut niveau comme Python/NumPy, les boucles scalaires agent par agent de Gauss-Seidel imposent un surcoût d'interpréteur très lourd. Bien que Gauss-Seidel demande moins d'itérations théoriques, notre benchmark mesuré dans #13 montre que Jacobi vectorisé (qui traite simultanément toutes les paires en contact via des opérations NumPy matricielles) s'exécute **environ 2 fois plus vite** à précision égale.

### Q2 : Pourquoi déclencher l'accélération de Nesterov seulement après 80 balayages ?
- **Réponse :** L'extrapolation inertielle de Nesterov est conçue pour des problèmes convexes. Or, la contrainte de non-recouvrement de disques rigides définit un ensemble non convexe. Déclencher Nesterov dès le premier balayage réinjectait de l'énergie cinétique (effet « billard » / rebond parasite d'ordre $10^{-3}$). En retardant Nesterov après 80 balayages de Jacobi pur, les contacts locaux sont déjà amortis et l'accélération ne sert qu'aux empilements profonds : la restitution est divisée par environ 1 100 pour descendre à $9{,}0 \cdot 10^{-7}$ ([PR #46](https://github.com/ViscoCrowd/ViscoCrowd-simulation/pull/46)), pour un surcoût limité à un facteur 2,2 sur le temps de projection.

### Q3 : Pourquoi le sol mouillé n'augmente-t-il pas la distance d'arrêt à vitesse normale ?
- **Réponse :** La dynamique du modèle (§ 2.4) combine relaxation ($\tau = 0{,}5\text{ s}$) et borne d'accélération ($a_{\max} = 3{,}3\text{ m/s}^2$ sur mouillé). L'adhérence ne sature que si l'accélération requise dépasse $a_{\max}$, c'est-à-dire si $(s - v)/\tau > a_{\max}$, soit $v_0 > a_{\max} \cdot \tau = 1{,}65\text{ m/s}$. À la vitesse de Weidmann de $1{,}34\text{ m/s}$, l'agent freine en régime purement exponentiel ($d = v_0 \tau = 0{,}6566\text{ m}$) sans glisser, exactement comme sur le sec. L'effet inertiel et le contraste mouillé/sec n'apparaissent qu'en situation d'urgence/panique ($v_0 > 1{,}65\text{ m/s}$, $+9\text{ \%}$ à $2{,}5\text{ m/s}$) ou lors de virages brusques. C'est un résultat physique du modèle, vérifié dans la PR #72.

### Q4 : Quelle différence fondamentale faites-vous entre le débit au portique et le temps d'évacuation ?
- **Réponse :** Le débit spécifique $J_s$ compte le flux *net* de franchissements à travers une ligne orientée divisé par la largeur et le temps. Il ne renseigne pas sur le nombre de personnes ayant réellement quitté les lieux : un agent refoulé puis ressorti compte 3 passages pour 1 sortie. L'observable rétrospective de sorties définitives (`sorties_definitives`) vérifie que le dernier passage est sortant et que l'agent ne revient plus jamais à l'intérieur. C'est elle qui donne les quantiles robustes $t_{50}$ et $t_{90}$.

### Q5 : Pourquoi la relation vitesse–espacement de Tordeux ($T = 0{,}35\text{ s}$) impose-t-elle un ordre strict par le champ eikonal ?
- **Réponse :** La règle $V(s) = \min(v_0, s/T)$ appliquée naïvement crée des dépendances circulaires (A attend B, B attend C, C attend A) dès que plusieurs personnes se croisent, bouchant tout goulot. En imposant que le meneur suivi soit obligatoirement *plus proche de la sortie* au sens de la distance eikonale ($\phi_j < \phi_i$), la relation « suit » devient un ordre partiel strict sans aucun cycle. Le plus avancé d'un groupe avance toujours sans être ralenti par ceux qui le talonnent.

### Q6 : Que signifie l'écart de 1,69 mm observé sur le choc à trois disques (#10 / #48), et biaise-t-il la densité ?
- **Réponse :** Ce phénomène a justement fait l'objet d'une requalification dans la [PR #48](https://github.com/ViscoCrowd/ViscoCrowd-simulation/pull/48). Sur le triangle sans frottement, l'écart de $1{,}69\text{ mm}$ après impact croît avec le temps : il provient d'une **vitesse résiduelle liée à la tolérance d'arrêt** de la projection, et non d'un défaut statique intrinsèque à Jacobi. Sur un empilement comprimé de 60 agents, perturber un centre de $10^{-12}\text{ m}$ modifie l'arrangement final de plus de $10^{-6}\text{ m}$ (sensibilité aux réarrangements discrets), et le jeu relatif des paires proches ($\sim 4 \cdot 10^{-5}$) ne suffit pas à borner une densité de Voronoï. Nous avons donc testé directement l'effet de la tolérance ($10^{-6}\text{ m}$ contre $10^{-9}\text{ m}$) sur la densité de Voronoï mesurée par un test de permutation apparié exact (`tests/test_densite.py`, aucune différence détectée à 5 % sur huit graines), tout en gardant dans [#10](https://github.com/ViscoCrowd/ViscoCrowd-simulation/issues/10) la vérification d'amplitude sur la géométrie cible du goulot.
