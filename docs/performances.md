# Mesurer avant une campagne longue

Le banc fait varier l'effectif, en conservant la géométrie, la graine et tous les
autres paramètres du YAML. Un effectif impossible est refusé, jamais compensé en
changeant l'espacement ou la taille du domaine. Les mesures ne constituent pas
une validation scientifique : celle-ci reste suivie dans l'issue #59.

```bash
viscocrowd mesurer-performances experiments/piscine.yaml \
  --effectifs 20 100 --archiver-tous 1 10 --repetitions 2 \
  --sortie data/performances-piscine.json
```

Le JSON conserve chaque répétition, les paramètres effectifs, la provenance du
code, les versions et les variables de nombre de threads. La sortie ne peut pas
écraser un fichier existant. Un cas en échec est enregistré comme tel, sans mesure
présentée comme valide, et rend le code final non nul. Le fichier est actualisé
après chaque cas ; il n'offre pas de reprise de campagne et une interruption
pendant son écriture peut le laisser incomplet.

## Lire les chiffres

Chaque cas s'exécute dans un **processus neuf**, pour que le pic mémoire d'un gros
effectif ne soit pas reporté sur le suivant.

| Champ | Mesure et limites |
|---|---|
| `temps_simulation_validation_archive_s` | Temps mural du calcul, de ses validations et de la compression NPZ ; imports du processus et lancement exclus. |
| `pic_rss_processus_octets` | Pic de mémoire résidente du processus, bibliothèques comprises ; disponible sur macOS/Linux, `null` ailleurs. Ce n'est pas une allocation Python ni une différence de deux pics. |
| `tableaux_conserves_octets` | Somme des tailles de t, x, v, rayons et états dans le résultat ; n'inclut pas les objets Python, temporaires du solveur ou métadonnées. |
| `archive_npz_octets` | Taille compressée sur disque. |
| `instants_archives`, `t_final_s` | Échantillonnage enregistré et durée physique réellement simulée. |

Comparer plusieurs répétitions sur la même machine, à charge comparable. Le temps
de fin d'évacuation peut changer avec l'effectif : ces lignes mesurent le coût du
scénario complet, pas une loi pure en N à durée constante. Fixer une durée courte
commune dans un YAML versionné pour isoler ce deuxième effet. Aucun seuil de temps
arbitraire n'est imposé en CI.

## Espacer l'archivage piscine sans changer dt

```bash
viscocrowd simuler experiments/piscine.yaml --sortie data/piscine-legere.npz \
  --archiver-tous 10
```

Le calcul garde `dt = 0,01 s` dans cet exemple, mais n'enregistre qu'un instant
tous les dix pas, ainsi que le premier et le dernier. L'espacement est fait
**pendant** la simulation : les tableaux intermédiaires ne sont pas accumulés puis
supprimés. Le dernier intervalle peut être plus court. La mémoire des états en
cours, du guidage, des événements et du solveur reste nécessaire.

Tous les pas continuent à vérifier les déplacements, la cohérence des états, la
projection et les murs. Le maximum de violation des parois est cumulé sur les pas
physiques, même ceux absents de l'archive. Tous les franchissements et les temps
de sortie restent conservés séparément : les temps d'évacuation ne sont pas
arrondis à la fréquence des images. Le défaut `--archiver-tous 1` garde tous les
instants. Aucune équation, tolérance ou hypothèse physique n'est modifiée.

Les métadonnées `archivage` distinguent le dt physique et le nombre de pas entre
images. Une relecture ne peut pas reconstituer des positions manquantes : ne pas
utiliser une archive espacée pour des pics de densité instantanée ou des vitesses
différenciées sans étude de sensibilité à la fréquence. Les états échantillonnés
peuvent sauter une transition intermédiaire visible dans les événements.

L'archivage espacé est actuellement réservé à la piscine. Le banc mesure aussi
couloir/tassement avec `--archiver-tous 1`. Ces scénarios gardent leur contrat
d'archive complète ; la bille seule n'est pas un banc en nombre d'agents.


## Mesure de référence du 23 octobre 2026

Mesure locale sur macOS arm64, Python 3.14.4, NumPy 2.5.3, SciPy 1.18.1,
Matplotlib 3.11.2, avec les dépendances figées. Code testé propre :
`7b8c1b4f34e77966919b62ab736bd7e696378bae`. Deux répétitions séquentielles
par cas, aucune autre suite de tests lancée en parallèle. Les valeurs ci-dessous
sont leurs moyennes ; [les huit mesures brutes](mesures/performances-piscine-2026-10-23.json)
conservent aussi les paramètres, la validation et l'environnement.

| N | Un instant tous les K pas | Temps calcul + validation + NPZ (s) | Pic RSS (Mio) | Tableaux conservés (Mio) | NPZ (Mio) | Instants |
|---:|---:|---:|---:|---:|---:|---:|
| 20 | 1 | 2.434 | 58.87 | 3.260 | 1.261 | 4231 |
| 20 | 10 | 2.422 | 54.97 | 0.327 | 0.129 | 424 |
| 100 | 1 | 8.122 | 114.24 | 17.454 | 6.835 | 4566 |
| 100 | 10 | 7.978 | 57.62 | 1.751 | 0.703 | 458 |

À 100 agents, K=10 divise ici la taille des tableaux par environ dix et le pic RSS
passe d'environ 114 à 58 Mio. Les bibliothèques et le guidage expliquent qu'à
20 agents le gain RSS reste limité. Avec seulement deux répétitions et des temps
proches, ces mesures ne démontrent pas une accélération du solveur.

Les huit calculs ont convergé. Les temps physiques finaux sont identiques entre
K=1 et K=10 : 42,30 s à 20 agents et 45,65 s à 100 agents. La preuve d'égalité des
positions conservées, des événements et des invariants est également automatisée
sur une évacuation complète de 20 agents (K=37). Un test injecte une violation sur
un pas non archivé et vérifie que la publication est refusée.
