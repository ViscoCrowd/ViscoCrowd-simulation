# Démonstrations de la soutenance

`make demo` (`.\run.ps1 demo` sous Windows) régénère dans `data/demo/` tous les films et images
de la soutenance, depuis les configurations de ce dossier. Le jour J, rien ne dépend d'un
fichier produit à la main sur un poste. Ce ne sont **pas** des configurations de référence :
ce sont des cas choisis pour montrer un mécanisme, et l'en-tête de chaque YAML dit lequel.

| Fichier produit | Commande | Configuration | Ce qu'on dit à l'oral |
|---|---|---|---|
| `duel.gif` | `duel` | `duel-plage-glissante.yaml` | La même foule, plage glissante en haut, témoin sec en bas : la porte saturée écoule moins (#137, graine 7 : 84,3 s contre 70,7 s) |
| `variantes.gif` | `comparer-variantes` | `duel-plage-glissante.yaml`, adhérence du mouillé à 3,3, 2 et 1 m/s² | L'effet inertiel n'apparaît que sur un sol très glissant (0,2 et 0,1 g) |
| `pose-longue.png` | `simuler` puis `pose-longue` | `duel-plage-glissante.yaml` | Toutes les trajectoires d'un coup : files aux échelles, couloir vers la porte |
| `pression.png` | `pression` | `pression-porte-saturee.yaml` | Sans régulation, porte de 0,8 m, panique 2 : la foule se comprime et des chaînes de force forment une arche devant la porte (#164). Sur la référence régulée, presque aucun contact |

À ajouter quand leurs PR seront fusionnées : la traînée d'eau (`trainee`, #165), la carte
des temps d'arrêt (`attente`, #178) et les intervalles entre sorties (`bouchons`, #177).

Durée mesurée de `make demo` : 3 min 27 s le 18 novembre 2026 (deux simulations du duel, trois
variantes, une simulation pour la pose longue), plus 2 min 13 s pour la carte de pression
(150 baigneurs, mesurée seule le 19 novembre).
