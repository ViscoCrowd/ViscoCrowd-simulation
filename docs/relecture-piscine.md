# Relire une évacuation de piscine

`viscocrowd rejouer data/piscine.npz` utilise les commandes du lecteur de couloir :
Lire/Pause, curseur temporel, `--vitesse`, exports `--image` et `--gif` hors écran.
`--instant` choisit le PNG ; le GIF parcourt toute l'archive, dernier instant compris.
Les exports existants ne sont pas écrasés. `--vitesse` ne modifie que la lecture.

La géométrie provient de `configuration.parametres.geometrie`, les états du tableau
`etats` et de sa légende. L'eau est bleue, les agents en franchissement orange et ceux
sur la plage blancs ; les agents sortis sont masqués. Le nombre d'évacués est compté
dans les états affichés, contrôlés contre les instants de sortie archivés.

La case d'un site occupé est déduite de la position de l'agent immobilisé sur ce site.
Cela couvre aussi les franchissements inachevés, absents de la liste des événements
terminés. Une occupation hors site ou multiple sur un site est refusée dès l'ouverture,
sur tous les instants : elle ne peut pas interrompre une lecture ou un GIF en cours.
Les marqueurs carrés identifient les échelles ; les petits points identifient le rebord.
Le fond sec/mouillé/eau emploie la même carte géométrique que le scénario, sans guidage.

Le lecteur refuse les états absents, une légende différente, les transitions en arrière,
une population incompatible ou des sorties contradictoires. Il ne revalide pas toute
la physique d'une archive : les invariants restent du ressort de la simulation/tests.

La navigation prend le dernier instant archivé inférieur ou égal au temps demandé.
Un état n'est pas interpolé : lors d'un archivage espacé, la vue n'invente pas un début
de franchissement entre deux images. Les événements de sortie conservent leurs instants
interpolés pour l'analyse, même quand l'affichage reste discret. Une archive espacée
(`simuler --archiver-tous K`) est signalée sous le schéma : « 1 image tous les K pas ».

## Vérification manuelle reproductible

```bash
viscocrowd simuler experiments/piscine.yaml --sortie data/piscine.npz
viscocrowd rejouer data/piscine.npz --image figures/piscine-10s.png --instant 10
viscocrowd rejouer data/piscine.npz --gif figures/piscine.gif --vitesse 20
```

Vérifier le bassin et la porte à l'échelle, le changement d'état au bord, la libération
des sites, puis la disparition des évacués. La fin de l'archive peut être une évacuation
incomplète : le compteur doit alors rester inférieur à N. Les paramètres du YAML sont
des propositions C6 ; une animation plausible ne constitue pas une validation physique.
