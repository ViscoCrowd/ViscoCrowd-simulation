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
| Évacuations incomplètes | **comptées à part, jamais moyennées** | 0 depuis #125 |

## 2. Convergence numérique (M9)

Pour chaque grandeur publiée (t50, t90, t100, J_s, et chaque écart Δ mouillé − sec), l'écart
moyen apparié entre Δt et Δt/2 doit rester **sous l'erreur standard entre graines**
(écart-type / √10). Sinon, la grandeur est publiée au pas le plus fin, et l'écart est signalé.
Δt/4 sert de contrôle sur la configuration de référence seulement, pour ne pas multiplier le
coût par quatre partout.

La tolérance de projection est couverte par #101 : entre 10⁻⁷ et 10⁻⁶ m, aucun effet décelable
sur la densité.

## 3. Détecter un effet du sol mouillé

Un écart Δ = mouillé − sec, apparié graine par graine sur 10 graines, est dit **détecté** si les
deux conditions tiennent :

1. il a le même signe sur au moins 9 graines sur 10 (sous l'hypothèse d'aucun effet, cela
   arrive avec une probabilité d'environ 2 %) ;
2. sa moyenne dépasse l'effet du pas de temps sur ce même Δ (critère 2).

Il est dit **pertinent pour la problématique** s'il dépasse aussi 1 % de la grandeur, soit
environ 0,3 s sur t50 dans la référence. Aujourd'hui, Δt50 vaut environ 0,01 s : détecté dans
certaines configurations (10/10 graines à 50 baigneurs), jamais pertinent.

## 4. Comparaison aux références

- **E0 contre Seyfried** : écart moyen absolu de J_s **≤ 10 %** sur les effectifs qui n'ont pas
  servi à choisir T (N = 40 et N = 20 ; aujourd'hui 6,6 % et 9,7 %). Le seuil de 15 % du test
  lent reste une garde de non-régression, pas un critère de validité.
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
