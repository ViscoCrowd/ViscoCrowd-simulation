# Jalon 2 — exclusion entre agents

Publication de rattrapage du 21 octobre 2026, suivie dans [#39](https://github.com/ViscoCrowd/ViscoCrowd-simulation/issues/39).
Le tag annoté `jalon-2` désigne le commit de publication sur `main`. Il ne clôt pas le jalon 3.

## Périmètre et provenance

La version reprend l'instantané de `dev` `babd8b0`, après les figures #23 et avant les
milieux #25. S'y ajoutent les correctifs déjà relus de #28 : `bd481dd` (documentation
de la projection), `7c8a80d` (paramètres non finis) et `742494d` (outillage). La méthode
de livraison et son audit proviennent de #40. Aucun nouveau calcul physique n'est introduit.

- Projection d'exclusion Jacobi vectorisée, accélération de Nesterov après 80 balayages,
  grille de voisins, diagnostic de convergence et mode strict.
- Schéma semi-implicite, confinement, vitesse relue après projection et `State` protégé.
- Scénario de tassement, validations quantitatives et six figures reproductibles.
- Observable de passage/débit et maquette piscine déjà livrées, avec leurs limites.
- Contrôles des entrées, Docker et CI de reproductibilité.

Les revues croisées des PR #6, #21, #22, #23 et #28 sont conservées. Les corrections
reprennent leurs fichiers sans modification de calcul ; le noyau, l'exclusion et le débit
ont été comparés à `dev`. Le guidage, les milieux dynamiques, les archives YAML/NPZ et
la relecture du couloir restent dans `dev`, où leur jalon est encore en cours.

## Validation du candidat

Mesurée le 21 octobre, Python 3.14.4 sur le poste de Lenny ; la CI utilise Python 3.12.

| Contrôle | Résultat |
|---|---|
| Ruff et formatage | conformes |
| Tests rapides | 282 passent en 17,64 s ; 2 tests lents exclus |
| Validation du moteur | code retour 0, 12,5 s |
| Validation et production des figures | code retour 0, 6 PNG, 48,9 s |
| Bille : violation maximale des parois | 3,331 × 10⁻¹⁶ m aux trois pas vérifiés |
| Boîte fixe : remontée d'énergie maximale | 0 J |
| Tassement de 36 disques, Δt = 0,002 s | recouvrement ≤ 10⁻⁶ m, violation des parois 0 m |
| Convergence de la projection, même tassement | 0 échec sur 1 500 pas ; 182 balayages au maximum pour un budget de 300 |

Les quatre contrôles CI de la PR de publication doivent être verts avant fusion :
style, tests/invariants, figures et validation dans le conteneur. Les durées ci-dessus
dépendent de la machine et des dépendances.

## Reproduire cette version

Depuis un clone, choisir le tag, puis installer selon le README :

```bash
git switch --detach jalon-2
make install
make lint test valider
make figures
docker compose run --rm viscocrowd make valider
```

Le manifeste `experiments/manifeste.yaml` conserve les paramètres et les graines des
figures. Les sources du tag restent la référence ; les images jointes à la release
illustrent sa validation.

## Limites

La méthode obtient une configuration admissible à la tolérance demandée, sans garantie
générale de projection euclidienne optimale. Le biais de position à contacts multiples
reste suivi dans #10. Le passage d'une ligne n'est pas une évacuation définitive (#11),
et les constantes de Weidmann restent à vérifier sur leur source primaire (#12).
La maquette ne simule pas le parcours piscine. La trace enseignant de J0 reste à compléter
(#19) et les critères pédagogiques individuels de #13 restent ouverts.

Les publications historiques ne sont pas antidatées. Le planning de cet instantané décrit
son état documentaire antérieur ; le planning courant et les livraisons suivantes sont
consultables sur la branche `dev`.
