# Exécuter et reprendre une campagne

```bash
viscocrowd campagne experiments/couloir.yaml experiments/piscine.yaml \
  --graines 1 2 3 --sortie data/campagne
# Après interruption, reprendre exactement le même plan :
viscocrowd campagne experiments/couloir.yaml experiments/piscine.yaml \
  --graines 1 2 3 --sortie data/campagne --reprendre
```

Chaque configuration est exécutée pour chaque graine, dans cet ordre. Sans `--graines`,
chaque configuration conserve sa propre graine. La bille déterministe exige l'absence
de cette option. Les doublons et les configurations invalides sont refusés avant calcul.
Pour une vraie campagne scientifique, utiliser au moins dix graines comme en spec §4 ;
la liste de trois graines ci-dessus illustre seulement la commande.

Le dossier contient `campagne.json`, les configurations figées `0001.yaml`, etc., et une
archive NPZ par calcul. Il doit se trouver hors de `src/` et `experiments/`, sous `data/`
par exemple. Ces deux dossiers sont suivis par la provenance du code : les fichiers de la
campagne y passeraient pour une modification. Un tel dossier est refusé avant toute écriture. Le suivi est remplacé atomiquement après chaque cas. Une archive
n'est réutilisée que si le cas est terminé, son empreinte SHA-256 est intacte et sa lecture
réussit. Les autres cas sont recalculés ; les anciennes archives incomplètes/corrompues
sont conservées sous `0001.invalide-1.npz`, etc. Aucun fichier extérieur n'est touché.

La reprise compare les paramètres/graines, le commit et l'état du dépôt, l'empreinte du
contenu des sources Python, les versions de Python/NumPy/SciPy/Matplotlib/PyYAML et la
plateforme. Un changement refuse la reprise : créer alors un nouveau dossier, pour ne
pas mélanger des résultats. Le contenu des sources distingue aussi deux arbres modifiés
sur le même commit. Le contexte est revérifié avant et après chaque calcul ; le code
doit rester stable pendant la campagne. Il ne s'agit pas d'une surveillance continue.

`Ctrl+C` laisse les cas terminés disponibles, marque le cas interrompu et libère le verrou.
Une coupure brutale (`SIGKILL`, panne) peut laisser `.verrou` : lire son PID/hôte, vérifier
qu'aucun processus n'utilise le dossier, puis retirer ce seul verrou avant `--reprendre`.
Le fichier empêche deux lancements concurrents dans le même dossier ; aucune prise de
contrôle automatique d'un verrou n'est faite.

Une erreur de simulation figure dans le suivi avec son message, et les cas suivants
restent exécutés. Le code de sortie est 1 si la campagne est incomplète, 130 après Ctrl+C.
`termine` signifie que le calcul et l'archive ont réussi : une piscine peut ne pas être
entièrement évacuée à la durée maximale. Les événements archivés permettent de le mesurer.
Les statistiques de validation restent associées à chaque cas ; aucune moyenne ne masque
les échecs. Cette commande ne reprend pas un pas de simulation interrompu.

Les scénarios pris en charge sont ceux de `simuler` (bille, tassement, couloir, piscine).
Le banc E0 possède sa propre commande et ne produit pas encore d'archive NPZ : il n'est
pas inclus dans ce lanceur tant que ce contrat n'est pas raccordé.
