# Paramètres du scénario piscine

**État au 14 novembre 2026.** Chaque valeur de [`experiments/piscine.yaml`](../experiments/piscine.yaml),
avec son unité, son statut, sa source ou sa justification, et ce qu'on sait de son influence.
C'est le tableau que demandait #59 (§ 3) pour #26. Les plages et les effets renvoient aux
mesures publiées ; « non balayé » veut dire qu'aucune mesure n'existe encore.

**Statuts.**
- *Source* : valeur reprise d'une publication vérifiée.
- *Étalonné* : valeur ajustée sur une mesure (et donc pas validée par cette même mesure).
- *Hypothèse* : valeur choisie sans source, à défendre comme telle.
- *Scénario* : choix de la piscine étudiée, pas une propriété physique.
- *Numérique* : réglage du schéma ; il ne doit pas changer les résultats.

## Milieux et comportement

| Paramètre | Valeur | Unité | Statut | Source ou justification | Plage explorée et effet |
|---|---|---|---|---|---|
| Vitesse dans l'eau, `EAU.vitesse` | 0,69 | m/s | Source | Shirvani et al. (2020), petit bain de 0,7 m, eau calme (#71) | Non balayé |
| Vitesse sur le sec, `SEC.vitesse` | 1,34 | m/s | Source | Weidmann (1993), p. 43 | Non balayé (référence de marche) |
| Vitesse sur le mouillé, `MOUILLE.vitesse` | 1,34 | m/s | Hypothèse | Égale au sec, par protocole : isoler l'adhérence (#26) | 0,7 à 1,0 m/s : Δ t50 de +0,7 à +1,5 s, 2,3 à 4,5 % (#136) |
| Relaxation τ, les trois sols | 0,5 | s | Source | Helbing et al. (2000) ; commune aux trois sols (journal, 6 novembre) | 0,3 à 0,8 s : Δ t50 de 0,08 s à τ = 0,3 s, nul à 0,8 s (#136) |
| Adhérence du sec, `SEC.acceleration_max` | 5,9 | m/s² | Source | 0,60 g, seuil « non glissant » de Kendzior (2023) | Non balayé |
| Adhérence du mouillé, `MOUILLE.acceleration_max` | 3,3 | m/s² | Source | 0,34 g, seuil « glissant » de Kendzior (2023), un seuil de perception et non une mesure sous une foule | 1 à 5,9 m/s² : 0,38 s sur t50 à 1 m/s², porte de 1,2 m (2 novembre) ; **jusqu'à la porte saturée de 0,8 m, −4 % de débit à 2 m/s² et −19 % à 1 m/s²** (#137) |
| Adhérence dans l'eau, `EAU.acceleration_max` | 1,67 | m/s² | Hypothèse | 0,34 g × poids apparent de moitié (journal, 6 novembre) | Outil prêt (`adherence_eau`, #119), non balayé |
| Facteur de panique | 1,5 | — | Hypothèse | Au-delà du seuil *faster-is-slower* de Helbing et al. (2000) : 2,0 m/s sur la plage | 1 à 2, avec régulation : t100 de 62 à 47 s, sans *faster-is-slower* ; Δ t50 du mouillé de 0 à 0,1 s (#136) |
| Temps d'espacement T | 0,35 | s | Étalonné | Tordeux et al. (2016), T ajusté sur E0 à N = 60 (#58), appliqué aussi dans l'eau (#116) | 0,25 à 0,5 s : débit à la porte de 2,56 à 1,94 pers/(m·s) (#116) |

## Géométrie et population

| Paramètre | Valeur | Unité | Statut | Source ou justification | Plage explorée et effet |
|---|---|---|---|---|---|
| Bassin | 25 × 12,5 | m | Scénario | Bassin de 25 m courant | Non balayé |
| Plages : gauche, haut et bas, côté porte | 3 ; 4 ; 20 | m | Scénario | Choix du plan (C6) | Non balayé |
| Largeur de la porte | 1,2 | m | Scénario | Trois diamètres | 0,8 à 1,6 m : la porte ne limite l'évacuation que sous 1 m (#128) |
| Profondeur de la porte | 1,0 | m | Scénario | Épaisseur du couloir de sortie | Non balayé |
| Largeur mouillée | 3,0 | m | Scénario | Bande autour du bassin | 0 à 20 m : sans effet à l'adhérence de référence, même jusqu'à la porte saturée (2 novembre, #137) |
| Pas des sites de rebord | 0,6 | m | Hypothèse | Un site tous les 1,5 diamètre | Non balayé |
| Échelles | 2, aux 9/10 des grands côtés | — | Scénario | Côté porte | Non balayé |
| Population N | 100 | pers | Scénario | ≈ 0,32 pers/m² dans le bassin | 50 à 200 : t100 augmente de 16,5 à 17,2 s par 50 baigneurs (#128) |
| Rayon r | 0,2 | m | Hypothèse | Demi-largeur d'épaules ; rayons identiques | Non balayé |
| Espacement et bruit initiaux | 1,0 ; 0,1 | m | Scénario | Placement dans le bassin ; la graine fait varier le reste | Couvert par les 10 graines |

## Franchissements

| Paramètre | Valeur | Unité | Statut | Source ou justification | Plage explorée et effet |
|---|---|---|---|---|---|
| Durée du rebord | 4,0 | s | Hypothèse | Se hisser sur le bord, sans source | Outil prêt (`duree_rebord`, #119), non balayé |
| Durée de l'échelle | 2,0 | s | Hypothèse | Monter une échelle, sans source | Outil prêt (`duree_echelle`, #119), non balayé |
| Portée de saisie | 0,25 | m | Hypothèse | Moins qu'un rayon, sous la moitié du pas des sites (docstring du scénario) | Non balayé ; règle de déblocage proposée dans #131 (#127) |

## Numérique

| Paramètre | Valeur | Unité | Statut | Justification | Vérification |
|---|---|---|---|---|---|
| Pas de temps Δt | 0,01 | s | Numérique | Déplacement par pas ≈ r/10 à 2 m/s (spec § 5.1) | Δt/2 et Δt/4 : t50, t90, t100 et J_s bougent au moins 10 fois moins que l'erreur standard entre graines (#138) |
| Tolérance de projection | 10⁻⁶ | m | Numérique | 5·10⁻⁶ r | Entre 10⁻⁷ et 10⁻⁶ m, aucun effet décelable sur la densité au goulot (#101) |
| Pas de la grille de guidage | 0,1 | m | Numérique | r/2 | Convergence du Fast Marching mesurée sur le couloir (#43) ; non balayé sur la piscine |
| Durée maximale | 180 | s | Numérique | Borne : le calcul s'arrête quand tous sont sortis | Sans effet tant qu'aucune évacuation n'est incomplète |

## Chutes

`chutes: null` : le module est **désactivé** dans la référence. Ses taux n'ont pas de source
(`docs/modele-chutes.md`, § 8), et la bousculade dépendait du pas de temps (#132, corrigé dans
#135). La décision de l'activer est suivie dans #130.

## Ce que le tableau montre

- **Les paramètres sans source qui comptent le plus ont un effet mesuré** : l'adhérence du
  mouillé près d'une porte saturée (#137), la vitesse sur le mouillé (#136) et T (#116).
  Ce sont eux qui conditionnent les conclusions, et ils doivent être discutés dans le rapport.
- **Trois hypothèses n'ont encore aucune mesure d'influence** : les deux durées de
  franchissement et l'adhérence dans l'eau. Les balayages sont outillés (#119).
