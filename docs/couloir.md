# Banc de foule guidée en couloir

Ce démonstrateur assemble les briques du projet : guidage, milieux, exclusion,
archives et relecture. Il permet de montrer un groupe qui traverse une bande mouillée
et de vérifier ses contraintes. Les valeurs sont illustratives ; le parcours piscine
et l'étude de l'effet de l'adhérence restent à construire.

## Reproduire la démonstration

Depuis la racine, avec l'environnement installé et activé selon le [README](../README.md) :

```bash
viscocrowd simuler experiments/couloir.yaml --sortie data/couloir.npz
viscocrowd rejouer data/couloir.npz
viscocrowd rejouer data/couloir.npz --gif figures/couloir.gif --image figures/couloir.png --instant 4.5
```

Les exports fonctionnent sans affichage, notamment dans Docker en préfixant la commande
par `docker compose run --rm viscocrowd`. Choisir de nouveaux noms si les fichiers existent.
La fenêtre interactive offre Lire/Pause et un curseur ; `--vitesse 2` accélère la lecture.
Le GIF rejoue toute l'archive ; `--instant` sélectionne seulement l'image PNG.

## Ce qui est mesuré

Configuration : [`experiments/couloir.yaml`](../experiments/couloir.yaml), graine 20262027,
24 agents de rayon 0,2 m, section en x = 12 m, largeur 3 m. La bande mouillée s'étend
de x = 4 à x = 8 m. Les agents et les parois latérales continuent après la section.

Mesures du 21 octobre 2026, Δt = 0,01 s, durée 14 s, 1 401 instants archivés :

| Grandeur | Mesure | Critère |
|---|---:|---|
| Recouvrement maximal | 9,99457 × 10⁻⁷ m | ≤ 10⁻⁶ m |
| Violation maximale des parois | 0 m | précision machine |
| Projections non convergées | 0 | 0 |
| Agents distincts ayant traversé | 24 / 24 | tous atteignent la section |
| Premier / dernier passage | 7,225 / 9,228 s | instants interpolés, pas des temps d'évacuation |

Pour recalculer ces valeurs depuis l'archive, sans relancer le moteur :

```bash
python - <<'PY'
import numpy as np
from viscocrowd.geometry.couloir import Couloir
from viscocrowd.io.trajectoires import lire_trajectoire
from viscocrowd.observables.debit import franchissements

a = lire_trajectoire("data/couloir.npz")
p = a.metadonnees["configuration"]["parametres"]
domaine = Couloir(p["longueur"], p["largeur"])
i, j = np.triu_indices(len(a.rayons), 1)
distances = np.linalg.norm(a.x[:, i] - a.x[:, j], axis=2)
recouvrement = np.maximum(a.rayons[i] + a.rayons[j] - distances, 0).max()
violation = max(domaine.violation(x, a.rayons, t) for t, x in zip(a.t, a.x, strict=True))
passages = franchissements(a.t, a.x, *domaine.section_sortie)
print("Recouvrement (m) :", recouvrement)
print("Violation des parois (m) :", violation)
print("Agents distincts :", len(np.unique(passages.agent[passages.sens > 0])))
print("Premier / dernier passage (s) :", passages.instant[[0, -1]])
print("Diagnostics du calcul :", a.metadonnees["validation"])
PY
```

Le contrôle exhaustif des paires convient à ce petit banc. La recherche de voisins du
moteur reste fondée sur sa grille spatiale.

## Validation et périmètre

`pytest tests/test_couloir_geometrie.py tests/test_couloir_scenario.py tests/test_relecture.py`
vérifie la géométrie, la carte, les contacts, le confinement, la sauvegarde et la lecture.
Pour un agent sans contact ni saturation, la référence est
`x(t) = x₀ + s [t − τ (1 − exp(−t/τ))]`. Les erreurs à t = 2 s sont respectivement
0,01893993, 0,00946027 et 0,00472770 m pour Δt = 0,02, 0,01 et 0,005 s : l'ordre un
est observé sur ce cas. Les paramètres exacts et les limites sont dans la
[section validation du rapport](../report/sections/05-validation.tex).

Le banc change plusieurs propriétés à la fois entre les sols : son ralentissement ne
permet pas d'isoler l'effet de l'adhérence. Il ne contient ni obstacle, ni porte étroite,
ni rebord ou échelle. Les passages ne sont pas des sorties absorbantes (#11).
G1 est livré ; G5 dispose d'un premier cas couplé validé. G2, la calibration C6,
le scénario piscine et les campagnes E0–E4 restent ouverts dans le
[planning](planning/README.md). Le rapport et la démonstration ne concluent pas encore
sur le diagramme fondamental de la piscine.
