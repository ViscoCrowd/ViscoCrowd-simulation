# Critères d'acceptation de la campagne finale

**Statut : proposition du 14 novembre 2026, à valider par le groupe avant la campagne finale
(#59, § 1).** Les fixer avant les calculs évite de choisir un seuil après coup pour qu'un
résultat passe. Un critère qui échoue est documenté tel quel ; on ne relève pas un seuil pour
le faire passer (CONTRIBUTING, § 5).

On sépare trois sources d'écart, qui ne se compensent pas :

- **l'erreur numérique** : pas de temps, tolérance de projection ;
- **la variabilité entre graines** : le placement initial change l'ordre d'arrivée aux sites ;
- **l'incertitude de la référence** : une mesure de Seyfried ou une synthèse de Weidmann a sa
  propre dispersion, et son propre domaine.

Et on sépare ce qui a servi à **ajuster** le modèle de ce qui sert à le **valider** : T a été
choisi sur E0 à N = 60. Ces données ne valident donc rien ; N = 40 et N = 20 le font, en partie.

## 1. Invariants, sur chaque simulation

Ils ne se discutent pas : une simulation qui en viole un est un bug, pas un résultat.

| Grandeur | Critère | Mesuré aujourd'hui |
|---|---|---|
| Recouvrement entre agents | ≤ tolérance de projection (10⁻⁶ m) | ≤ 10⁻⁶ m |
| Violation des murs et du bord du bassin | ≤ 10⁻¹² m | ~10⁻¹⁶ m |
| Conservation : dans l'eau + bord + plage + sortis = N | exacte, à chaque pas | exacte (#81, #91) |
| Projections non convergées | 0 | 0 |
| Évacuations incomplètes | **comptées à part, jamais moyennées** | 0 dans les configurations publiées depuis #125 ; hors régulation, 2 dans la piscine à a_max de l'eau = 1,6 (#127) et 1 au goulot E0 à b = 0,8 m (#141) |

## 2. Convergence numérique (M9)

Pour chaque grandeur publiée (t50, t90, t100, J_s, et chaque écart Δ mouillé − sec), l'écart
moyen apparié entre Δt et Δt/2 doit rester **sous son erreur standard** :

- pour une grandeur brute, l'erreur standard entre graines (écart-type / √10) ;
- **pour un écart Δ, l'erreur standard de Δ lui-même** (écart-type des Δ par graine / √10).
  C'est Δ que la problématique interroge, et l'appariement la rend bien plus petite : à la
  référence, 0,023 s pour Δ t50 contre 0,165 s pour t50. Sur #138, le critère passe à un
  rapport de 0,3 à 0,9 pour les Δ, contre moins de 0,1 pour les grandeurs brutes.

Sinon, la grandeur est publiée au pas le plus fin, et l'écart est signalé.
Δt/4 sert de contrôle sur la configuration de référence seulement, pour ne pas multiplier le
coût par quatre partout.

La tolérance de projection est couverte par #101 : entre 10⁻⁷ et 10⁻⁶ m, aucun effet décelable
sur la densité.

## 3. Détecter un effet du sol mouillé

Un écart Δ = mouillé − sec, apparié graine par graine sur 10 graines, est dit **détecté** si les
deux conditions tiennent :

1. **test de signe exact, bilatéral, au seuil de 5 %.** Les égalités sont fréquentes quand le
   mouillé n'est jamais limitant (7 graines sur 10 à τ = 0,8 s dans #136, et une « positive »
   à 2·10⁻¹³ s, du bruit d'arrondi). Une graine avec |Δ| < 10⁻⁹ s compte donc comme une
   égalité, et on l'écarte. Sur les n graines restantes, avec n ≥ 8, l'effet est détecté s'il
   y a au plus une graine de signe contraire pour n = 9 ou 10 (p = 3,9 % et 2,1 %), et aucune
   pour n = 8 (p = 0,8 % ; une seule contraire y donnerait 7 %). Avec n < 8, on ne conclut pas ;
2. sa moyenne dépasse l'effet du pas de temps sur ce même Δ (critère 2).

**Comparaison principale et balayages exploratoires.** À 5 % par écart, une campagne qui teste
une cinquantaine d'écarts (4 balayages × 3 ou 4 valeurs × t50, t90, t100, J_s) en « détecte »
quelques-uns par hasard. On désigne donc **une comparaison principale**, E1/E2 sur la
référence (Δ t50 et Δ t100), à laquelle s'applique ce critère. Les balayages sont présentés
comme **exploratoires** : un effet qu'on y trouve est décrit avec son décompte de graines,
sans être dit détecté. Pour en faire une conclusion du rapport, on le confirme sur dix
nouvelles graines (11 à 20), fixées avant la relance.

Il est dit **pertinent pour la problématique** s'il dépasse aussi 1 % de la grandeur, soit
environ 0,3 s sur t50 dans la référence. Aujourd'hui, sur la comparaison principale, Δt50
vaut −0,01 ± 0,07 s : ni détecté, ni pertinent. Dans les balayages exploratoires, il est de
même signe sur les 10 graines à 50 baigneurs, sans être pertinent (0,012 s) ; il ne devient
pertinent que si l'on impose une marche plus lente sur le mouillé (2,3 à 4,5 % de t50, #136)
ou sur une plage très glissante jusqu'à une porte saturée (#137).

## 4. Comparaison aux références

- **E0 contre Seyfried** : écart moyen absolu de J_s **≤ 10 %**, **sur 10 graines**, sur les
  effectifs qui n'ont pas servi à choisir T (N = 40 et N = 20). Sur dix graines (#141) :
  5,7 % et 7,3 %. Les 6,6 et 9,7 % cités jusqu'ici venaient de trois graines, et selon le
  triplet retenu, l'écart à N = 20 va de 5,7 à 9,7 % : trois graines ne suffisent pas à
  trancher contre un seuil de 10 %. Le seuil reste un nombre rond : les mesures de Seyfried
  sont des expériences uniques par couple (b, N), sans dispersion entre essais à laquelle se
  référer. Le seuil de 15 % du test lent reste une garde de non-régression, pas un critère de
  validité.
- **Diagramme fondamental contre Weidmann** : **aucun critère chiffré** tant que la mesure n'est
  pas faite dans son domaine (écoulement libre, sans contrainte extérieure). Devant un goulot ou
  une porte saturée, on décrit l'écart sans conclure (#126, #133). La dispersion des sources de
  Weidmann (0,26 m/s) n'est pas une tolérance de validation (journal, #51).
- **Évacuation contre le repère N / (J b)** : un ordre de grandeur, pas un critère (#105).

## 5. Robustesse d'une conclusion

Une conclusion du rapport est dite **robuste** si son sens ne change pas sur toute la plage
explorée de chaque paramètre incertain : τ (0,3 à 0,8 s), T (0,25 à 0,5 s), la vitesse et
l'adhérence sur le mouillé, a_max de l'eau, les durées de franchissement, la largeur de porte
et la population. Une conclusion qui ne tient que sur une partie de la plage est écrite avec
cette plage. Le [tableau des paramètres](parametres-piscine.md) donne, pour chacun, la plage
balayée et son effet.
