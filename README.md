<div align="center">

# ViscoCrowd

**Évacuation de piscine en panique : extraction aquatique répartie, carrelage mouillé, goulot unique.**

Simulation particulaire — module R5.12 *Modélisation mathématique*
BUT 3 Informatique (alternance) · 2026-2027

[![CI](https://github.com/ViscoCrowd/ViscoCrowd-simulation/actions/workflows/ci.yml/badge.svg)](https://github.com/ViscoCrowd/ViscoCrowd-simulation/actions/workflows/ci.yml)
[![Rapport](https://github.com/ViscoCrowd/ViscoCrowd-simulation/actions/workflows/report.yml/badge.svg)](https://github.com/ViscoCrowd/ViscoCrowd-simulation/actions/workflows/report.yml)
[![Python 3.12](https://img.shields.io/badge/python-3.12-3776ab.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

</div>

---

## La question

> Comment la succession d'une **extraction aquatique répartie** (franchissement des rebords et
> échelles) et d'un **goulot d'étranglement unique en milieu sec**, couplée à l'**inertie d'une
> zone de carrelage mouillé**, altère-t-elle le **diagramme fondamental débit/densité** d'une
> foule en panique ?

Une piscine couverte s'évacue en urgence. La foule traverse trois milieux aux propriétés
mécaniques incompatibles, et c'est leur enchaînement qui nous intéresse :

| | Milieu | Ce qui s'y joue |
|---|---|---|
| 🌊 | **Bassin** | Forte traînée visqueuse. Sortie répartie entre le rebord (partout, mais lent) et les échelles (rares, mais rapides). Chaque point de franchissement est à capacité unitaire. |
| 💧 | **Carrelage mouillé** | Faible adhérence : l'accélération disponible est bornée. L'agent ne peut ni s'arrêter ni tourner vite — c'est le terme d'**inertie**. |
| 🚪 | **Zone sèche et goulot** | Adhérence nominale, puis rétrécissement vers une porte unique. C'est là qu'on mesure. |

**L'enjeu.** Deux mécanismes antagonistes sont plausibles, et les départager est tout le travail :
la traversée *désynchronise* les arrivées au goulot et fait **monter** le débit (effet tampon),
ou bien la faible adhérence empêche les agents de réguler leur approche, densifie les contacts
et le fait **chuter** (effet inertiel, apparenté au *faster-is-slower*).

---

## Approche

Modèle **particulaire** à **exclusion dure**, dans le prolongement direct du cours :

```
    pas libre  →  projection sur l'ensemble admissible  →  v = Δx / Δt
                                                            ╰── le choc est ici
```

La vitesse n'est jamais transportée d'un pas à l'autre : elle est **recalculée à partir du
déplacement effectivement réalisé**. Si la projection a annulé le déplacement normal, elle
annule du même coup la composante normale de la vitesse. C'est la traduction discrète de la loi
de choc mou — et c'est ce qui garantit, par construction, qu'aucun agent ne traverse une paroi,
**quel que soit le pas de temps**.

Le schéma d'intégration, les contraintes et les conditions aux limites sont écrits par le
groupe. Aucun moteur physique, moteur de jeu ou code de simulation de foule prêt à l'emploi.

📐 **[Spécification de conception complète](docs/superpowers/specs/2026-10-06-viscocrowd-design.md)**

---

## Démarrage

### Avec Docker — reproductibilité garantie

```bash
docker compose run --rm viscocrowd make valider
```

### En local

```bash
python -m venv .venv
source .venv/bin/activate        # Windows : .venv\Scripts\activate
pip install -e ".[dev]"

viscocrowd valider-moteur --figures
```

### Exécuter une configuration et relire une trajectoire

Les deux bancs d'essai disposent de configurations YAML en unités SI :

```bash
viscocrowd simuler experiments/bille_boite.yaml --sortie data/bille.npz
viscocrowd simuler experiments/tassement.yaml --sortie data/tassement.npz
# Même commande dans l'image, avec l'archive conservée dans ./data :
docker compose run --rm viscocrowd viscocrowd simuler experiments/tassement.yaml --sortie data/tassement.npz
```

Chaque configuration déclare `version: 1`, `scenario`, `graine` et `parametres`.
La graine est un entier positif ou nul pour le tassement, et `null` pour la bille
déterministe. Les paramètres omis reprennent les valeurs du banc d'essai ; **toutes les
valeurs effectives sont enregistrées dans l'archive**. Les clés inconnues ou dupliquées,
les valeurs non finies et les paramètres physiques invalides sont refusés. Une sortie
existante n'est jamais écrasée : choisir un autre nom pour une nouvelle expérience.

L'archive NPZ v1 contient `t` (P,), `x` et `v` (P, N, 2), `rayons` (N,), ainsi que
des métadonnées JSON : configuration effective, unités, versions Python/NumPy/ViscoCrowd
et diagnostics de validation. Une simulation non convergée n'est pas sauvegardée.
La lecture vérifie version, formes, valeurs finies et temps strictement croissants,
avec `allow_pickle=False` : aucun objet Python n'est chargé.

```python
from viscocrowd.io.trajectoires import lire_trajectoire
from viscocrowd.observables.energie import energie_mecanique

donnees = lire_trajectoire("data/bille.npz")
p = donnees.metadonnees["configuration"]["parametres"]
energie = energie_mecanique(donnees.x, donnees.v, masse=p["masse"], gravite=p["gravite"])
```

Les tests vérifient l'égalité exacte des tableaux à graine fixée et après relecture,
dans un même environnement. Cette garantie ne porte pas sur les octets du fichier ZIP
ni sur l'égalité entre versions de dépendances. Le format conserve une population fixe
et tous les pas en mémoire ; ce n'est pas une reprise de calcul ni un état d'évacuation.
Le dernier instant peut dépasser la durée demandée de moins d'un pas, conformément
à l'intégrateur existant. La commande `valider-moteur --figures` conserve ses bancs de
validation actuels ; l'exploitation automatique des archives par les futures campagnes
reste à raccorder. Ces deux configurations ne produisent pas de nouvelles figures du rapport.

**Dépendances** — Python ≥ 3.12, NumPy, SciPy, Matplotlib, PyYAML.
Versions exactes figées dans [`requirements.lock.txt`](requirements.lock.txt).

**Temps d'exécution mesuré le 21 octobre 2026** — suite rapide : **382 tests en 34 s**
sur le poste de Lenny, Python 3.14.4 (2 scénarios lents exclus). La validation du moteur
affiche son propre temps ; les durées varient selon la machine et les dépendances.

### Aperçu de la piscine

```bash
make interface
# Ou, avec l'environnement virtuel activé :
viscocrowd interface
```

Une fenêtre affiche un schéma en noir et blanc, inspiré du croquis de référence :
un bassin noir à contour blanc, une échelle à barreaux et une sortie unique à droite.
Le cadre extérieur reste continu derrière la sortie. Un petit repère indique les
directions x et y. Les différents sols ne sont pas encore détaillés.
La barre d'outils permet de zoomer, de déplacer la vue et d'enregistrer une image.

**Une unité du plan représente un mètre**, avec la même échelle horizontale et verticale.
Les dimensions de travail sont regroupées dans `DimensionsPlan` : bassin de **25 × 12,5 m**
dans une emprise de **48 × 20,5 m**, échelle de **0,50 m** de large et **1 m** de long,
sortie de **1,20 m**. Une barre de **5 m** et un disque de référence de **0,40 m de diamètre**,
dessinés à la même échelle que le bassin, permettent de juger les proportions.
Le disque est placé dans la légende : aucune population n'est ajoutée.
La distance du bord droit du bassin au mur de sortie est de **20 m**, indiquée sur le plan
et réglable avec `DimensionsPlan(plage_sortie=...)`. Cet espace réserve de la place au futur
parcours sur sol mouillé puis sec ; leur séparation et leurs effets restent à définir.
Ces dimensions sont **provisoires**, à valider pour le scénario ; cette maquette ne lance
aucune simulation et ne présente aucun résultat physique.
Le format du bassin reprend notamment celui des piscines municipales La Plaine et Mourlon,
décrit par la [Ville de Paris](https://mairie15.paris.fr/pages/equipements-sportifs-13195).

Le bouton **Afficher paramètres** déplie le panneau à droite ; **Masquer paramètres** rend
sa largeur au plan. Le panneau est masqué à l'ouverture pour privilégier la vue d'ensemble.
Le zoom et les valeurs sont conservés lors de la bascule, avec une échelle toujours uniforme.
Le panneau réserve les valeurs de population, de géométrie, des trois milieux,
des franchissements et du calcul. Le rayon de référence, le nombre d'échelles et la largeur
de sortie reprennent le dessin ; les autres champs non renseignés affichent `—`. Le chronomètre
en haut à droite affiche le **temps simulé**, au format minutes:secondes.centièmes ; il
reste à zéro par défaut et ne compte pas le temps d'ouverture de la fenêtre.

Les valeurs pourront être fournies directement en arguments. Exemple d'affichage uniquement
(ces nombres ne constituent pas une calibration du modèle) :

```python
from viscocrowd.ui.parametres import DimensionsPlan, ParametresAffichage, ParametresMilieu
from viscocrowd.ui.piscine import ouvrir_interface

ouvrir_interface(
    dimensions=DimensionsPlan(plage_sortie=20.0, largeur_sortie=1.2),
    afficher_parametres=True,
    parametres=ParametresAffichage(
        nombre_agents=100,
        dt=0.01,
        graine=20262027,
        eau=ParametresMilieu(vitesse=0.5),
    ),
    temps_simule=12.5,
)
```

`creer_figure()` accepte les mêmes arguments pour construire la vue sans lancer sa boucle
graphique. `DimensionsPlan` commande les dimensions du dessin et ses annotations : changer
la largeur de sortie ajuste aussi son symbole et le panneau. Les valeurs de rayon, nombre
d'échelles et largeur de sortie éventuellement fournies dans `ParametresAffichage` sont
remplacées par celles du dessin. Les autres valeurs restent des annotations.

L'affichage utilise Matplotlib, déjà présent dans le projet, et reste isolé dans
`src/viscocrowd/ui/`. Il nécessite un environnement graphique local : macOS utilise
le backend natif ; les autres postes doivent disposer d'un backend interactif
Matplotlib, par exemple TkAgg avec Tk installé. Le conteneur Docker configuré avec
`MPLBACKEND=Agg` reste destiné aux calculs et aux exports hors écran.

---

## État d'avancement

| Jalon | Contenu | État |
|---|---|---|
| 0 | Socle du dépôt, méthodologie, cahier des charges | Socle livré ; [trace de validation à compléter](docs/validation-sujet.md#trace-de-validation) |
| 1 | Moteur : schéma semi-implicite + projection sur le domaine | ✅ Validé |
| 2 | Exclusion entre agents (projection itérative) | ✅ Validé collectivement, avec limites suivies ci-dessous |
| 3 | Champ de guidage eikonal + milieux (eau / mouillé / sec) | En cours : adhérence et assemblage livrés ; géométrie, calibration et guidage à terminer |
| 4 | Scénario piscine complet, franchissements | ⏳ À développer |
| 5 | Campagnes, diagramme fondamental, validation chiffrée | ⏳ À développer |
| 6 | Rapport, figures finales, transparents | ⏳ À finaliser |

Le statut du sujet et les questions encore ouvertes sont centralisés dans la
[fiche de cadrage](docs/validation-sujet.md#trace-de-validation). Les choix collectifs du jalon 2
(Jacobi vectorisé et Nesterov après 80 balayages) figurent dans le
[journal des décisions](docs/journal-decisions.md) et l'[issue #13](https://github.com/ViscoCrowd/ViscoCrowd-simulation/issues/13).

Cette validation conserve la limite de contacts multiples suivie dans
l'[issue #10](https://github.com/ViscoCrowd/ViscoCrowd-simulation/issues/10), à corriger ou à
quantifier avant les campagnes. Le rejet des valeurs non finies
([#16](https://github.com/ViscoCrowd/ViscoCrowd-simulation/issues/16)) et la protection des états
([#17](https://github.com/ViscoCrowd/ViscoCrowd-simulation/issues/17)) sont corrigés ;
le lancement Docker ([#18](https://github.com/ViscoCrowd/ViscoCrowd-simulation/issues/18))
est vérifié par la CI. L'assemblage des milieux est livré dans la
[PR #30](https://github.com/ViscoCrowd/ViscoCrowd-simulation/pull/30) ; le raccordement à la
géométrie et au guidage réels reste ouvert dans [#26](https://github.com/ViscoCrowd/ViscoCrowd-simulation/issues/26).
Les configurations YAML et archives de trajectoires C7 sont livrées pour les bancs d'essai
dans la [PR #32](https://github.com/ViscoCrowd/ViscoCrowd-simulation/pull/32).

Le [planning détaillé et daté 2026–2027](docs/planning/README.md) est la référence pour le suivi
des tâches ; ses modifications sont relisibles dans les pull requests.

---

## Validation du moteur

> *Une simulation qui tourne n'est pas une simulation juste.*

Chaque critère produit un **nombre**, pas une impression visuelle. Reproductible par
`viscocrowd valider-moteur`.

| Critère | Mesure | Attendu |
|---|---|---|
| Respect de la contrainte | **2,2 × 10⁻¹⁶ m** | précision machine |
| … à Δt = 10⁻¹ s (dix fois trop grand) | **2,2 × 10⁻¹⁶ m** | indépendant de Δt |
| Remontée d'énergie (boîte fixe) | **0,0 J** | ≤ 0, strictement |
| Dissipation totale par les chocs | 14,2 J | substantielle |
| Écart à l'entraînement, ω = 5 rad/s | 1,7 × 10⁻² m/s | → 0 |
| Recouvrement résiduel entre agents (36 disques, Δt = 2·10⁻³ s) | **≤ 10⁻⁶ m** (1,4 × 10⁻⁵ du rayon de 0,07 m) | ≤ tolérance annoncée |
| … violation des parois, mêmes agents | **0,0 m** | précision machine |
| … projections non convergées | **0 sur 1500** | 0 |
| … balayages de projection par pas, au maximum | 182 (budget 300) | < budget |
| … énergie cinétique finale du tas | **7,0 × 10⁻⁶ J** | → 0 (tas au repos) |
| Restitution après un choc à contacts multiples | **9,0 × 10⁻⁷** de l'énergie d'arrivée | 0 (choc mou) |

### Un résultat non trivial

Le sujet d'introduction annonce qu'après dissipation, « la bille doit se stabiliser dans un coin
de la boîte et tourner solidairement avec elle ». **Nos mesures montrent que ce n'est vrai que
dans le régime centrifuge**, soit ω²R ≳ g :

| ω (rad/s) | ω²R/g | écart à l'entraînement |
|---:|---:|---:|
| 1,0 | 0,10 | 1,9 m/s ❌ |
| 3,0 | 0,92 | 3,6 × 10⁻² m/s ✅ |
| 5,0 | 2,55 | 1,7 × 10⁻² m/s ✅ |
| 10,0 | 10,19 | 6,7 × 10⁻² m/s ✅ |

Or **ω = 1 rad/s, la valeur suggérée par le sujet, n'est pas dans ce régime** : la gravité y
domine d'un facteur dix, et la bille glisse le long des parois en dégringolant de coin en coin.
Le critère de validation n'est pas faux — il a un domaine de validité, que les paramètres
suggérés ne respectent pas. Les deux régimes sont désormais testés séparément en intégration
continue.

---

## Organisation

```
src/viscocrowd/
├── core/          état, schéma semi-implicite, graines aléatoires
├── io/            configurations YAML, lecture et écriture des trajectoires NPZ
├── geometry/      domaines, parois, projection d'exclusion, grille de voisins
├── observables/   énergie, densité, débit  (ne dépend d'aucun module de simulation)
├── scenarios/     assemblages testables
├── viz/           figures
├── ui/            aperçu graphique de la piscine, indépendant du moteur
└── cli.py

tests/             unitaires · invariants physiques (tournent à chaque PR)
docs/              cahier des charges, spécification, journal des décisions
experiments/       configs YAML + manifeste figure ↔ config ↔ graine
report/            rapport LaTeX, compilé par la CI
```

**Pourquoi `observables/` ne dépend de rien** — les trajectoires sont persistées, et les
observables calculés hors ligne. Retracer une figure ou tester un nouvel observable ne demande
donc pas de relancer les simulations, ce qui est déterminant sur un balayage de paramètres.

---

## Reproductibilité

Exigences du module, et où elles sont tenues :

| Exigence | Où |
|---|---|
| Dépendances, commande, temps d'exécution | ce fichier, section **Démarrage** |
| Paramètres de chaque figure du rapport | [`experiments/manifeste.yaml`](experiments/manifeste.yaml) |
| Graine fixée pour les tirages aléatoires | `src/viscocrowd/core/rng.py` — tout l'aléa y passe |
| Relance à l'identique | `docker compose run --rm viscocrowd make figures` |

---

## Contribuer

Méthodologie, convention de branches et processus de revue : **[CONTRIBUTING.md](CONTRIBUTING.md)**.

```bash
make install     # environnement de développement
make test        # suite de tests
make lint        # ruff
make valider     # critères de validation du moteur, chiffrés
make figures     # régénère toutes les figures
make report      # compile le rapport LaTeX
```

---

## Équipe

| | GitHub |
|---|---|
| Karrouchi Hamza | [@CodeByHaamza](https://github.com/CodeByHaamza) |
| Lesueur Shaleena | [@shalee-pnt](https://github.com/shalee-pnt) |
| Mongrandi Lenny | [@lennymgrd](https://github.com/lennymgrd) |

Encadrement : O. Pantz — module R5.12, BUT 3 Informatique.

## Licence

[MIT](LICENSE)
