# Retrouver et expliquer nos choix

Point du **3 novembre 2026**. Cette fiche prépare la relecture avant soutenance ;
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
| Vitesse–espacement de Tordeux ($T = 0{,}35\text{ s}$) | Sans espacement, le débit E0 vaut 1,9 à 2,5 fois la mesure de Seyfried (écart moyen de 119 %). Avec $T = 0{,}35\text{ s}$, l'écart moyen tombe à 2,8 % sur N = 60 : c'est un **ajustement** sur les données qui ont servi à choisir T, pas une validation. Contrôle partiel sur N = 40 (6,6 %) et N = 20 (9,7 %) : un seul protocole, sol sec, trois graines. La règle reste une proposition à valider (#57), branchée seulement sur E0. Ordre strict par temps eikonal pour exclure les cycles de blocage mutuel. | [#57](https://github.com/ViscoCrowd/ViscoCrowd-simulation/issues/57), [PR #58](https://github.com/ViscoCrowd/ViscoCrowd-simulation/pull/58), [journal](journal-decisions.md) |
| Seuil de saturation du sol mouillé | À $v_0 = 1{,}34\text{ m/s}$ (facteur panique 1), un agent seul s'arrête en $0{,}6566\text{ m}$ sur le mouillé comme sur le sec : freiner jusqu'à l'arrêt demande $v_0/\tau$, qui ne dépasse $a_{\max}$ que si $v_0 > a_{\max} \cdot \tau = 1{,}65\text{ m/s}$ (facteur $> 1{,}23$). L'adhérence sature quand même lors des relances et des virages serrés (au-delà d'environ 76°) : 0,03 % des pas sur le mouillé au facteur 1. À $2{,}5\text{ m/s}$, un agent seul freine sur 9 % de distance en plus. Sur l'évacuation complète de la piscine, aucun effet net du mouillé jusqu'au facteur 2,5. | [#26](https://github.com/ViscoCrowd/ViscoCrowd-simulation/issues/26), [PR #72](https://github.com/ViscoCrowd/ViscoCrowd-simulation/pull/72), [PR #84](https://github.com/ViscoCrowd/ViscoCrowd-simulation/pull/84), [journal](journal-decisions.md) |
| Archives espacées ($K > 1$) et observables | L'archivage tous les $K$ pas allège le disque mais perd les positions intermédiaires : une vitesse dérivée, une densité instantanée ou un passage interpolé sur une telle archive serait faux. Les fonctions `*_trajectoire` livrées dans la PR #74 refusent ces archives pour les mesures physiques. Les fonctions sur tableaux ne peuvent pas le vérifier, et l'étude de sensibilité à $K$ reste ouverte dans #73. | [#73](https://github.com/ViscoCrowd/ViscoCrowd-simulation/issues/73), [PR #74](https://github.com/ViscoCrowd/ViscoCrowd-simulation/pull/74), [performances](performances.md) |
| Diagnostic rejouable des projections non convergées | Enregistre sans pickle l'instantané fautif sous `.diagnostic.npz`, avec les paramètres effectifs ; le domaine est reconstruit (tassement, couloir, piscine) et aucune fonction n'est chargée depuis l'archive. Le rejeu sert à comprendre l'échec et à comparer un budget d'itérations plus grand. Il ne rend pas le calcul d'origine publiable : il faut corriger, relancer et valider la simulation complète. | [#64](https://github.com/ViscoCrowd/ViscoCrowd-simulation/issues/64), [PR #69](https://github.com/ViscoCrowd/ViscoCrowd-simulation/pull/69), [diagnostic](diagnostic-projection.md) |

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
  absorbante sont implémentés dans [#55](https://github.com/ViscoCrowd/ViscoCrowd-simulation/pull/55).
  Le contrôle croisé avec l'observable rétrospective est livré dans [#81](https://github.com/ViscoCrowd/ViscoCrowd-simulation/pull/81) :
  mêmes agents sortis, écart inférieur à un pas de temps. La sortie absorbante est actée, et le repère `N / (J w)` est confronté au goulot et à la piscine avec le débit maximal de Weidmann, J = 1,225 ([#11](https://github.com/ViscoCrowd/ViscoCrowd-simulation/issues/11)).
  Les valeurs numériques de [#26](https://github.com/ViscoCrowd/ViscoCrowd-simulation/issues/26)
  restent une proposition soumise à la validation collective avant les campagnes finales.
- **Porte de la piscine (#85).** Au facteur de panique 1,5, une porte de 0,8 m se bouche sur 8 graines
  sur 10 en arches statiques, comme la première géométrie de E0. Les coins vifs des montants sont la
  cause probable : tant qu'ils ne sont pas corrigés, les balayages de porte et de population (E4) ne
  mesurent pas un comportement de foule.
- **Chutes (#78/#82).** Le module existe sur `dev`, désactivé par défaut. La médiane de relevage
  vient de Becker et al. (2016) ; les taux de chute et de cascade ne sont pas calibrés. L'enseignant a validé son inclusion dans le rendu en séance le 3 novembre
  ([#19](https://github.com/ViscoCrowd/ViscoCrowd-simulation/issues/19), [trace](validation-sujet.md#trace-de-validation)). Tant que ses taux ne sont pas calibrés, ses chiffres ne sont pas des résultats.

## Relecture avant la présentation

Pour chaque ligne, repartir du problème, dessiner le contre-exemple, expliquer la
formule et ses unités, puis retrouver le test ou la mesure avec sa configuration,
ses graines et sa limite. Relancer les tests lents explicitement lorsqu'ils portent
la conclusion discutée ; la commande habituelle `pytest -m "not slow"` les exclut (voir le [guide des tests lents](ci-tests-lents.md)).
Vérifier enfin que les slides décrivent la version publiée dans le
[registre des livraisons](livraisons.md), et non toutes les propositions encore en PR.

## Questions types du jury et arguments de défense

### Q1 : Pourquoi avoir choisi un algorithme de Jacobi vectorisé plutôt que Gauss-Seidel ?
- **Réponse :** Dans un langage de haut niveau comme Python/NumPy, les boucles scalaires agent par agent de Gauss-Seidel imposent un surcoût d'interpréteur très lourd. Bien que Gauss-Seidel demande moins d'itérations théoriques, notre benchmark mesuré dans #13 montre que Jacobi vectorisé (qui traite simultanément toutes les paires en contact via des opérations NumPy matricielles) s'exécute **environ 2 fois plus vite** à précision égale.

### Q2 : Pourquoi déclencher l'accélération de Nesterov seulement après 80 balayages ?
- **Réponse :** Allumée dès le premier balayage, l'extrapolation de Nesterov pousse les disques **au-delà du contact**, et ce jeu reste définitif, puisque les corrections ne font qu'écarter les disques. La vitesse relue $v = \Delta x / \Delta t$ contient alors un rebond : un choc de trois disques alignés restituait 1 % de la vitesse d'arrivée ($1{,}27 \cdot 10^{-2}\text{ m}$ de jeu, $1{,}06 \cdot 10^{-2}\text{ m/s}$ résiduels). Le test à deux disques ne pouvait pas le voir : une paire isolée est corrigée exactement en un balayage, et l'artefact n'apparaît qu'à partir de trois corps (`TestChocMultiple`). En n'allumant l'extrapolation qu'après 80 balayages de Jacobi pur, avec une rampe repartant de zéro, les contacts simples sont déjà résolus et l'accélération ne sert qu'aux empilements profonds : la restitution est divisée par environ 1 100 pour descendre à $9{,}0 \cdot 10^{-7}$ ([PR #46](https://github.com/ViscoCrowd/ViscoCrowd-simulation/pull/46)), pour un surcoût limité à un facteur 2,2 sur le temps de projection.

### Q3 : Pourquoi le sol mouillé n'augmente-t-il pas la distance d'arrêt à vitesse normale ?
- **Réponse :** La dynamique du modèle (§ 2.4) combine relaxation ($\tau = 0{,}5\text{ s}$) et borne d'accélération ($a_{\max} = 3{,}3\text{ m/s}^2$ sur mouillé). L'accélération demandée vaut $(U - v)/\tau$, où $U$ est la vitesse visée ; elle n'est écrêtée que si sa norme dépasse $a_{\max}$. Pour un freinage jusqu'à l'arrêt ($U = 0$), elle vaut $v_0/\tau$ : l'adhérence ne sature donc que si $v_0 > a_{\max} \cdot \tau = 1{,}65\text{ m/s}$, soit un facteur de panique supérieur à 1,23. À la vitesse de Weidmann de $1{,}34\text{ m/s}$, l'agent freine sans glisser : en régime non saturé, la distance d'arrêt vaut $v_0 \tau \approx 0{,}67\text{ m}$ ($0{,}6566\text{ m}$ mesuré au pas de $0{,}01\text{ s}$), sur le mouillé comme sur le sec. L'adhérence sature tout de même, rarement, lors des relances et des virages serrés (0,03 % des pas sur le mouillé au facteur 1, PR #72). À $2{,}5\text{ m/s}$, un agent seul freine sur 9 % de distance en plus. Sur l'évacuation complète de la piscine dans la géométrie de référence, en revanche, les balayages de la PR #84 ne mesurent aucun effet net jusqu'au facteur 2,5 : les relances ont lieu près du bassin et cette porte n'est pas encombrée. Le seul effet net mesuré est un retard de $t_{50}$ de $0{,}38\text{ s}$ (10 graines sur 10) quand l'adhérence du mouillé tombe à $1\text{ m/s}^2$ ; une porte de $0{,}8\text{ m}$, elle, se bouche (#85).

### Q4 : Quelle différence fondamentale faites-vous entre le débit au portique et le temps d'évacuation ?
- **Réponse :** Le débit spécifique $J_s$ compte le flux *net* de franchissements à travers une ligne orientée, divisé par la largeur et le temps. Il ne donne pas les temps d'évacuation, pour deux raisons. D'abord, une ligne de mesure n'est pas forcément une sortie. Ensuite, un compteur de passages ne dit pas *quand* une personne est définitivement sortie : un agent qui sort, rentre et ressort compte trois passages bruts (`franchissements`), et même si le flux net le compte bien une fois, il ne situe pas sa sortie définitive dans le temps. Or $t_{50}$ et $t_{90}$ sont des instants. L'observable rétrospective de sorties définitives (`sorties_definitives`) vérifie que le dernier passage est sortant et que l'agent ne revient plus jamais à l'intérieur. C'est elle qui donne les quantiles robustes $t_{50}$ et $t_{90}$.

### Q5 : Pourquoi la relation vitesse–espacement de Tordeux ($T = 0{,}35\text{ s}$) impose-t-elle un ordre strict par le champ eikonal ?
- **Réponse :** La règle $V(s) = \min(v_0, s/T)$ appliquée naïvement crée des dépendances circulaires (A attend B, B attend C, C attend A) dès que plusieurs personnes se croisent, bouchant tout goulot. En imposant que le meneur suivi soit obligatoirement *plus proche de la sortie* au sens de la distance eikonale ($\phi_j < \phi_i$), la relation « suit » devient un ordre partiel strict sans aucun cycle. Le plus avancé d'un groupe avance toujours sans être ralenti par ceux qui le talonnent.

### Q6 : Que signifie l'écart de 1,69 mm observé sur le choc à trois disques (#10 / #48), et biaise-t-il la densité ?
- **Réponse :** Ce phénomène a justement fait l'objet d'une requalification dans la [PR #48](https://github.com/ViscoCrowd/ViscoCrowd-simulation/pull/48). Sur le triangle sans frottement, l'écart de $1{,}69\text{ mm}$ après impact croît avec le temps : il provient d'une **vitesse résiduelle liée à la tolérance d'arrêt** de la projection, et non d'un défaut statique intrinsèque à Jacobi. Sur un empilement comprimé de 60 agents, perturber un centre de $10^{-12}\text{ m}$ modifie l'arrangement final de plus de $10^{-6}\text{ m}$ (sensibilité aux réarrangements discrets), et le jeu relatif des paires proches ($\sim 4 \cdot 10^{-5}$) ne suffit pas à borner une densité de Voronoï. Nous avons donc testé directement l'effet de la tolérance ($10^{-6}\text{ m}$ contre $10^{-9}\text{ m}$) sur la densité de Voronoï mesurée par un test de permutation apparié exact (`tests/test_densite.py`, aucune différence détectée à 5 % sur huit graines), tout en gardant dans [#10](https://github.com/ViscoCrowd/ViscoCrowd-simulation/issues/10) la vérification d'amplitude sur la géométrie cible du goulot.
