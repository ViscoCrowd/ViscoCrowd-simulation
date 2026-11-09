# Rejouer une projection non convergée

`viscocrowd simuler` refuse toujours une trajectoire dont une projection n'a pas
convergé. Il conserve désormais, à côté de la sortie demandée, un fichier
`nom.diagnostic.npz`. Le chemin est annoncé dans l'erreur ; le code de retour reste 1.
Une réussite ne crée aucun diagnostic. Un diagnostic existant n'est jamais écrasé.

```bash
viscocrowd simuler experiments/tassement.yaml --sortie data/tas.npz
# Si une projection échoue :
viscocrowd diagnostiquer-projection data/tas.diagnostic.npz
viscocrowd diagnostiquer-projection data/tas.diagnostic.npz --iterations 600
```

Le premier appel réutilise le budget et la tolérance archivés. Le second permet
d'étudier l'effet du budget, sans modifier la tolérance ni relancer la simulation.
Le bilan JSON donne les deux résidus en mètres, l'écart maximal aux positions
archivées, les contacts hors tolérance et les provenances du code. Retour 0 si le
nouvel appel converge, 1 s'il échoue encore, 2 si le diagnostic est invalide.
Comparer un budget supérieur n'autorise pas la publication du calcul initial :
il faut corriger puis relancer et valider la simulation complète.

## Ce qui est conservé

- Positions libres et positions après le dernier balayage, rayons et instant.
- Tolérance, nombre de balayages, résidu atteint, paramètres effectifs et graine.
- Provenance du code et versions numériques ; unités explicites.

En mode strict, c'est l'appel qui interrompt le calcul. En mode permissif, le
solveur conserve uniquement l'appel au plus grand résidu ; la vérification finale
le remonte. Les copies supplémentaires n'ont lieu qu'en cas d'échec, et une seule
configuration fautive reste conservée par projection.

Le fichier est un NPZ distinct des trajectoires, avec métadonnées JSON et lecture
sans pickle. Il ne peut pas alimenter le lecteur d'animation ou les observables
comme un résultat physique valide. Si sa sauvegarde échoue, la non-convergence
reste l'erreur principale et le motif de sauvegarde est indiqué.

## Périmètre et interprétation

Les domaines reconstruits sont ceux du tassement, du couloir et de la piscine.
Le temps et les paramètres effectifs sont repris exactement ; aucune fonction
arbitraire n'est chargée depuis l'archive. La bille seule n'emploie pas ce solveur.
L'archive est autonome pour rejouer **cet appel**, pas pour reprendre toute la
trajectoire : elle ne contient ni guidage futur ni état complet des franchissements.

Les indices des contacts sont **locaux à l'appel**. En piscine, seuls les agents
actifs sont projetés : ces indices ne sont donc pas les identifiants globaux de la
population. Les tableaux enregistrent tous les agents de l'appel, nécessaires pour
reconstruire les chaînes de contacts.

Pour une reproduction exacte, utiliser le même commit et les mêmes dépendances.
Rejouer après une correction reste possible ; comparer alors explicitement les
provenances et les écarts affichés. Les tests couvrent un échec de tassement réel
avec budget réduit, la reproduction exacte, le refus d'écrasement et les archives
invalides. Aucune hypothèse physique ni règle Jacobi/Nesterov n'est modifiée.
