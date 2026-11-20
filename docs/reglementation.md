# La porte de la piscine face au règlement de sécurité

**Question.** Une piscine dont les dégagements respectent le règlement de sécurité des
établissements recevant du public (ERP) s'évacue-t-elle à temps selon notre modèle ? Et si le
dégagement secondaire est condamné, la porte principale réglementaire suffit-elle seule ?

## Ce que dit le règlement

Règlement de sécurité contre les risques d'incendie et de panique dans les ERP (arrêté du
25 juin 1980, dispositions générales) :

- **Article CO 38** (calcul des dégagements, version en vigueur depuis le 23 janvier 2010,
  [Légifrance](https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000021231086/2026-04-27)) :
  - de 51 à 100 personnes : soit deux dégagements d'une unité de passage chacun, soit un
    dégagement de deux unités complété par un dégagement accessoire ;
  - au-delà de 100 personnes : deux dégagements jusqu'à 500 personnes ; la largeur totale vaut
    une unité de passage par tranche de 100 personnes ou fraction, majorée d'une unité
    au-dessous de 501 personnes.
- **Article CO 36** (largeur des dégagements, d'après
  [SiteSécurité](https://sitesecurite.com/contenu/_erp/erp/co34a42_5POI.php?id=CO38), recoupé
  par la [fiche du ministère de la Culture](https://www.culture.gouv.fr/fr/Media/Thematiques/Securite-Surete/Fichiers/securite-incendie/fiche-n-11-effectifs-et-issus-de-secours-2022)) :
  l'unité de passage vaut 0,60 m, mais un dégagement d'une unité doit mesurer **0,90 m** et un
  dégagement de deux unités **1,40 m**. Au-delà de 200 personnes, les dégagements normaux ont au
  moins deux unités.

Le texte de CO 36 n'a pas été lu sur Légifrance (page refusée au téléchargement automatique) :
**à vérifier sur l'original** avant de le citer dans le rapport.

## Application à notre piscine

L'effectif retenu est le nombre de baigneurs : le personnel et le public des gradins sont
ignorés (une limite).

| Baigneurs | Unités de passage (CO 38) | Dégagements | Porte principale réglementaire |
|---|---|---|---|
| 100 | 2 | 2 de 1 UP, ou 1 de 2 UP + accessoire | 1,40 m (2 UP) |
| 150 | 2 + 1 = 3 | 2 | 1,40 m (2 UP) + 0,90 m (1 UP) |
| 200 | 2 + 1 = 3 | 2 | 1,40 m (2 UP) + 0,90 m (1 UP) |

Notre référence n'a qu'**une porte de 1,20 m**, qui ne correspond à aucune largeur
réglementaire (0,90 m pour une unité, 1,40 m pour deux). Le sujet assume un goulot unique :
dans le langage du règlement, c'est le cas où le **dégagement secondaire est condamné**.

## Mesure

Porte unique de 1,40 m (la porte principale réglementaire) puis de 0,90 m (une seule unité),
100, 150 et 200 baigneurs, référence mouillée et témoin sec appariés, graines 1 à 10, commit
`9631ade` sans modification locale ; 120 évacuations.

```bash
viscocrowd balayer-piscine experiments/piscine.yaml --parametre n_agents --valeurs 100 150 200 \
  --fixer largeur_porte=1.4 --graines 1 2 3 4 5 6 7 8 9 10 \
  --sortie docs/mesures/reglementation-porte-2026-11-18/porte-1.4.json
# idem avec largeur_porte=0.9 et porte-0.9.json
```

| Baigneurs | t100, porte 1,40 m (s) | t100, porte 0,90 m (s) | Débit, 1,40 m (pers/s) | Débit, 0,90 m (pers/s) | Δ t100 mouillé − sec |
|---|---|---|---|---|---|
| 100 | 51,28 ± 1,88 | 51,35 ± 1,74 | 2,74 | 2,74 | ≤ 0,07 s, sans signe dominant |
| 150 | 67,43 ± 2,82 | 68,47 ± 3,43 | 2,85 | 2,79 | ≤ 0,2 s |
| 200 | 84,72 ± 1,35 | 86,44 ± 2,03 | 2,85 | 2,78 | ≤ 0,3 s |

Aucune évacuation incomplète.

## Lecture

1. **Même condamnée à une seule porte, la piscine conforme s'évacue sans que la porte limite.**
   Le débit vaut 2,7 à 2,9 pers/s avec 1,40 m comme avec 0,90 m : c'est le rythme auquel les
   baigneurs sortent de l'eau, par les échelles et le rebord, qui fixe la durée. La porte
   d'une unité ne coûte que 1,7 s de plus à 200 baigneurs.
2. **La durée croît avec l'effectif** (51, 68 puis 85 s), comme à la référence (#128).
3. **Le sol mouillé ne change rien** dans ces configurations : l'effet inertiel demande une
   porte saturée (#137), que ces largeurs ne produisent pas à ces effectifs.

**Question ouverte.** À 0,90 m, la porte écoule 2,8 pers/s, soit J_s ≈ 3,1 pers/(m·s), bien
au-dessus du débit maximal de Weidmann (1,23 pers/(m·s)) et de la mesure de Seyfried au goulot.
À 0,80 m, la même piscine plafonne à 1,8 pers/s (#137). Le saut entre 0,80 et 0,90 m reste à
comprendre. Une piste, non vérifiée : à 0,80 m, deux disques de 0,40 m ne passent pas de
front entre les montants arrondis, à 0,90 m si. Avant de citer ces chiffres, il faudrait
mesurer le débit maximal de la porte de la piscine en fonction de sa largeur, porte saturée.

## Limites

- Effectif = baigneurs seuls ; un vrai calcul d'effectif ERP compte aussi le personnel et le
  public.
- Une seule porte dans le modèle : le scénario « deux dégagements » demande une géométrie à
  plusieurs portes (#193).
- Le règlement fixe des largeurs, pas des durées : il n'existe pas de temps d'évacuation
  réglementaire auquel comparer t100.
