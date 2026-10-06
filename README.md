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

**Dépendances** — Python ≥ 3.12, NumPy, SciPy, Matplotlib, PyYAML.
Versions exactes figées dans [`requirements.lock.txt`](requirements.lock.txt).

**Temps d'exécution typique** — validation complète du moteur avec figures : **≈ 8 s** sur un
portable récent. La suite de tests : **≈ 5 s**.

---

## État d'avancement

| Jalon | Contenu | État |
|---|---|---|
| 0 | Socle du dépôt, méthodologie, cahier des charges | ✅ |
| 1 | Moteur : schéma semi-implicite + projection sur le domaine | ✅ validé |
| 2 | Exclusion entre agents (projection itérative) | ⏳ |
| 3 | Champ de guidage eikonal + milieux (eau / mouillé / sec) | ⏳ |
| 4 | Scénario piscine complet, franchissements | ⏳ |
| 5 | Campagnes, diagramme fondamental, validation chiffrée | ⏳ |
| 6 | Rapport, figures finales, transparents | ⏳ |

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
├── geometry/      domaines, parois, projections
├── observables/   énergie, densité, débit  (ne dépend d'aucun module de simulation)
├── scenarios/     assemblages testables
├── viz/           figures
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
