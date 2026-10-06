## Ce que fait cette PR

<!-- Une a trois phrases. Le POURQUOI, pas le QUOI : le diff dit deja le quoi. -->

Closes #

## Nature

- [ ] `feat` — nouvelle brique de modele ou de code
- [ ] `fix` — correction d'un comportement faux
- [ ] `exp` — campagne de simulation
- [ ] `docs` — rapport, cahier des charges, journal
- [ ] `chore` — outillage, CI, dependances

## Validation

<!-- LA section qui compte. Des CHIFFRES, pas « ca a l'air de marcher ».
     Supprimez les lignes sans objet, mais ne les laissez pas vides. -->

| Grandeur mesuree | Valeur | Attendu |
|---|---|---|
| Violation de contrainte max | | precision machine |
| Recouvrement residuel max | | < tolerance annoncee |
| Remontee d'energie (domaine fixe) | | <= 0 |
| Temps d'execution | | |

Sensibilite verifiee : <!-- dt divise par 2 et 4 ? N augmente ? plusieurs graines ? -->

## Modelisation

<!-- A remplir si la PR touche au modele. Sinon : « sans objet ». -->

- Hypothese physique introduite ou modifiee :
- Decision consignee dans `docs/journal-decisions.md` : oui / non / sans objet

## Figures

<!-- Si des figures changent : lesquelles, et le manifeste est-il a jour ? -->

- [ ] `experiments/manifeste.yaml` mis a jour (figure, configuration, graine)

## Avant de demander la relecture

- [ ] `make lint` passe
- [ ] `make test` passe
- [ ] Les grandeurs physiques portent leurs unites
- [ ] Aucune dependance specialisee ajoutee (moteur physique, moteur de jeu, code de foule)
- [ ] Aucun appel direct a `numpy.random` (tout passe par `viscocrowd.core.rng`)
- [ ] **Je saurais reexpliquer et modifier ce code en soutenance**
