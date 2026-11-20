# Mesurer les durées de franchissement à la piscine

**Pourquoi.** La durée pour se hisser sur le rebord (4 s) et pour monter l'échelle (2 s) sont
deux hypothèses sans source (`docs/parametres-piscine.md`). Elles fixent la capacité de
l'extraction répartie, le premier maillon de la problématique, et le champ de guidage de l'eau
en dépend (φ_eau = T_k + φ_plage). Une mesure du groupe, même modeste, vaut mieux qu'aucune
source, et elle se défend bien en soutenance.

**Ce protocole est écrit avant la séance** : on ne choisit pas après coup ce qu'on mesure.

## Ce qu'on mesure

- **Départ du chrono** : la main touche le bord du bassin, ou le premier barreau de l'échelle.
- **Arrêt** : les deux pieds sont posés sur la plage, la personne debout.
- **Deux natures** : `rebord` (se hisser sans échelle, là où l'eau a la profondeur du petit
  bain de la référence, 0,7 m si possible) et `echelle`.
- **Deux allures** : `normale` (comme en fin de séance) et `pressee` (« le plus vite possible,
  sans courir de risque »). L'allure pressée est le repère pour une évacuation.

## Plan

- 3 personnes × 5 essais × 2 natures × 2 allures = **60 mesures**, environ une heure.
- Ordre des essais **alterné** (rebord, échelle, rebord…) pour ne pas mesurer la fatigue.
- Un chronométreur, un secrétaire qui saisit au fur et à mesure dans `chronos.csv`.
- Noter la profondeur réelle au point de sortie, et la hauteur du bord au-dessus de l'eau.

## Sécurité

Accord du maître-nageur avant de commencer. Aucune course sur la plage, aucun essai
« pressé » si le sol est encombré. Un essai interrompu est noté `NA`, sans le recommencer
à la hâte.

## Saisie

`chronos.csv`, une ligne par essai :

```text
personne,nature,allure,essai,duree_s,profondeur_m,remarque
A,rebord,pressee,1,3.4,0.8,
```

`personne` est un code (A, B, C), jamais un nom. `duree_s` en secondes, au dixième.

## Analyse

```bash
python docs/mesures/franchissement-protocole/analyser.py docs/mesures/franchissement-AAAA-MM-JJ/chronos.csv
```

Le script donne, par nature et par allure, le nombre d'essais, la médiane et l'écart
interquartile, en tableau Markdown à recopier dans `docs/parametres-piscine.md` (statut
« mesuré par le groupe, n = … »).

## Ce qu'on en fera

- Si les médianes pressées tombent dans les plages déjà explorables (`duree_rebord`,
  `duree_echelle`, #119), on cite la mesure comme justification des valeurs, sans toucher la
  référence.
- Sinon, on ouvre une issue de décision : changer `piscine.yaml` oblige à refaire E1/E2 et les
  balayages.
- Limites à écrire : trois personnes jeunes et valides, une seule piscine, pas de panique
  réelle.
