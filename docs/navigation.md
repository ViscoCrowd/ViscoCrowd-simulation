# Navigation locale des baigneurs (#158)

**Statut** : module facultatif (`navigation:` dans le YAML de la piscine, `null` par défaut).
La référence n'est pas modifiée : l'activer est une décision de groupe (#158).

## Le problème

Le guidage eikonal donne à tous le même plus court chemin vers la porte. Sur la plage, ce
chemin longe le bord du bassin à un rayon près, puis va en ligne droite du coin du bassin à
la porte. Comme rien n'écartait un agent de cette ligne (vitesses identiques, aucune
anticipation, régulation qui fait suivre le précédent), les baigneurs marchaient **en file
indienne contre le bord, puis en deux lignes parfaites vers la porte**. Sur dix graines,
93 % des positions de plage le long du bassin étaient à moins de 1 cm du plus près
possible, et le flux faisait 6 cm d'épaisseur.

## Le modèle : Moussaïd, Helbing et Theraulaz (2011)

*How simple rules determine pedestrian behavior and crowd disasters*, PNAS 108(17),
p. 6884-6888, vérifié sur l'original (`moussaid2011` dans la bibliographie). Deux
heuristiques fondées sur la vision :

1. **Direction.** Dans son champ de vision, de −φ à +φ autour de sa ligne de visée, le
   piéton choisit la direction α qui minimise la distance à sa destination
   `d(α)² = d_max² + f(α)² − 2 d_max f(α) cos(α₀ − α)`, où α₀ est la direction de la
   destination et f(α) la distance à la première collision s'il marchait dans la direction
   α à sa vitesse souhaitée, compte tenu de la vitesse et de la taille des autres,
   plafonnée à l'horizon d_max.
2. **Vitesse.** `v_des = min(v0, d_h / τ)`, où d_h est la distance au premier obstacle
   dans la direction choisie, à l'instant t.

La vitesse relaxe ensuite vers `v_des e_des`, comme dans tout le modèle (τ et a_max du
sol). Valeurs de l'article, reprises par défaut : τ = 0,5 s, φ = 75°, d_max = 10 m
(fig. 2), vitesse souhaitée tirée selon une loi normale de coefficient de variation
0,2/1,3 = 0,15 (fig. 3).

## Ce qui est adapté, et pourquoi

| Article | Ici | Pourquoi |
|---|---|---|
| Destination : un point | Direction du champ eikonal | La porte est derrière le coin du bassin : le champ donne la direction du plus court chemin, que l'heuristique corrige localement |
| Forces de contact k g(r_i + r_j − d_ij) | Projection du moteur | L'exclusion dure du cours reste inchangée |
| Tous les piétons | Agents sur la plage seulement | Nager n'est pas marcher ; les nageurs gardent le champ de l'eau |
| v0 ~ N(1,3 ; 0,2) m/s | Vitesse du sol × facteur individuel ~ N(1 ; 0,15), tronqué à ±3σ | Les sols et le facteur de panique gardent leur sens ; la troncature garde le déplacement par pas sous r/5 |
| — | Régulation T de Tordeux remplacée sur la plage | La seconde heuristique en est la version 2D, avec τ = 0,5 s au lieu de T = 0,35 s |
| — | Marge de 1 mm face aux parois | La projection tolère 10⁻⁶ m de recouvrement ; sans marge, un agent posé contre le bassin voyait toutes ses directions bouchées |

Les obstacles vus sont les murs, le bassin, les montants de la porte (coins arrondis, comme
la projection depuis #125), les obstacles fixes et les autres agents de la plage. Une
première version à coins vifs figeait les baigneurs qui glissaient le long du coin d'un
montant, et la porte se bouchait.

## Mesure (17 novembre 2026)

Référence `experiments/piscine.yaml` (régulée, T = 0,35 s), graines 1 à 10, commit
`89da62c` sans modification locale, Windows. Script et bilan :
[`mesures/navigation-2026-11-17/`](mesures/navigation-2026-11-17/).

```bash
python docs/mesures/navigation-2026-11-17/mesurer.py experiments/piscine.yaml
```

| | Référence | Navigation | Navigation, Δt/2 | Navigation, sol sec |
|---|---|---|---|---|
| Positions de plage contre le bord du bassin | 92,9 ± 3,3 % | **9,1 ± 1,6 %** | 8,8 % | 9,1 % |
| Épaisseur du flux (écart interquartile latéral) | 0,06 m | **0,78 m** | 0,76 m | 0,76 m |
| t50 (s) | 31,43 ± 0,52 | 30,83 ± 0,57 | 30,43 ± 0,61 | 30,47 ± 0,55 |
| t90 (s) | 45,40 ± 0,76 | 43,44 ± 0,66 | 43,15 ± 0,78 | 43,10 ± 0,82 |
| t100 (s) | 51,28 ± 1,87 | 47,16 ± 0,96 | 47,47 ± 1,02 | 47,00 ± 1,04 |
| Débit à la porte (pers/(m·s)) | 2,28 ± 0,10 | 2,46 ± 0,06 | 2,44 ± 0,06 | 2,47 ± 0,09 |
| Calcul par évacuation | 16 s | 40 s | 77 s | 39 s |

Écarts appariés, graine par graine (valeur p par permutation exacte des signes) :

| | Δ t50 (s) | Δ t100 (s) | Δ débit |
|---|---|---|---|
| Navigation − référence | −0,60 ± 0,56 (p = 0,006, 9/10) | **−4,12 ± 1,07** (p = 0,002, 10/10) | +0,18 ± 0,07 (p = 0,002, 10/10) |
| Δt/2 − Δt (navigation) | −0,39 ± 0,79 (p = 0,14) | +0,31 ± 0,81 (p = 0,24) | −0,02 ± 0,06 (p = 0,24) |
| Mouillé − sec (navigation) | +0,36 ± 0,73 (p = 0,14) | +0,16 ± 1,32 (p = 0,78) | −0,01 ± 0,10 (p = 0,82) |

![Graine 1, à 20, 28 et 36 s : en haut la référence, en bas la navigation](mesures/navigation-2026-11-17/avant-apres.png)

*Graine 1, à 20, 28 et 36 s. En haut, la référence : deux files contre le bassin, puis deux lignes vers la porte. En bas, la navigation : des flux diffus, puis une foule devant la porte. Pointillés : limite de la bande mouillée.*

## Ce qu'on en retient

1. **La file indienne disparaît.** Les baigneurs s'écartent du bord du bassin (9 % contre
   93 %) et le flux s'élargit d'un facteur treize. Visuellement, les deux lignes parfaites
   deviennent des flux diffus, puis une foule qui se resserre devant la porte.
2. **L'évacuation est plus rapide**, de 4 s sur t100 (10 graines sur 10), et la porte
   écoule plus : 2,46 contre 2,28 pers/(m·s). Explication possible, non mesurée : en
   utilisant la largeur de la plage, les baigneurs arrivent à la porte de front plutôt
   qu'en deux files. Ce débit s'éloigne de la mesure de Seyfried (1,97) : le
   goulot E0 n'utilise pas encore la navigation, et T y reste étalonné pour l'ancienne
   règle (voir les limites).
3. **Le pas de temps ne change rien de décelable** : Δt/2 déplace t50, t100 et le débit de
   moins de leur écart-type entre graines.
4. **L'effet du sol mouillé n'est pas résolu** sur dix graines : Δt50 = +0,36 ± 0,73 s.
   La navigation rend chaque évacuation plus sensible au détail des trajectoires : l'écart
   mouillé − sec est dix fois plus dispersé qu'avec la référence (0,07 s). Le mesurer
   demandera davantage de graines.

## Limites

- **E0 n'utilise pas la navigation.** Si elle devient la référence de la piscine, le
  goulot E0 doit l'adopter aussi, pour que l'étalonnage contre Seyfried porte sur le même
  modèle. La seconde heuristique (τ = 0,5 s) y remplacerait T = 0,35 s : c'est une
  validation à refaire, pas un réglage.
- **Coût de calcul** : environ 2,5 fois plus long par évacuation, à cause des distances
  libres calculées dans 31 directions pour chaque baigneur de la plage.
- **Les nageurs** ne naviguent pas : dans l'eau, le guidage reste celui du champ.
- **La distance gardée au bord du bassin** n'est pas imposée. Elle vient de l'évitement des
  autres et de la dispersion des vitesses ; aucune source ne la fixe ici.
