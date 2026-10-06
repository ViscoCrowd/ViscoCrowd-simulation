# Journal des décisions

Les décisions de modélisation un peu structurantes, les options écartées, et les pistes qui
n'ont pas abouti.

> Les consignes précisent que les pistes explorées sans succès **font partie du travail et que
> leur analyse est valorisée**. Une impasse documentée en octobre est une section de rapport en
> décembre ; la même impasse oubliée n'est rien.

Format : une entrée par décision, la plus récente en haut.

---

## 2026-10-06 — Le critère d'entraînement du sujet a un domaine de validité

**Contexte.** Le sujet d'introduction donne comme critère de validation n° 2 : « après quelques
secondes, tous les chocs ayant dissipé l'énergie disponible, la bille doit se stabiliser dans un
coin de la boîte et tourner solidairement avec elle ». Notre test écrit à partir de cet énoncé
échouait, avec un écart à la vitesse d'entraînement de 1,86 m·s⁻¹ au lieu des 0,05 attendus.

**Investigation.** Plutôt que de desserrer le seuil du test, nous avons mesuré l'écart en
fonction de la vitesse angulaire :

| ω (rad·s⁻¹) | ω²R/g | écart moyen (m·s⁻¹) | distance finale au centre (m) |
|---:|---:|---:|---:|
| 0 | 0,00 | 0,000 | 0,996 |
| 1 | 0,10 | 1,854 | 1,283 |
| 3 | 0,92 | 0,032 | 1,321 |
| 5 | 2,55 | 0,002 | 1,344 |
| 10 | 10,19 | 0,007 | 1,344 |
| 20 | 40,77 | 0,027 | 1,344 |

**Décision.** Le critère n'est pas faux : il vaut dans le régime où la force centrifuge domine la
gravité, soit ω²R ≳ g. Or les paramètres suggérés par le sujet (ω = 1 rad·s⁻¹, R = 1 m) donnent
ω²R/g = 0,10 — la gravité y domine d'un facteur dix, et la bille glisse le long des parois en
dégringolant de coin en coin au fil de la rotation, sans jamais se caler.

La transition est nette autour de ω²R/g ≈ 1. Dans le régime centrifuge, la distance finale au
centre vaut 1,3435 m, soit exactement √2 × (R − r) : la bille est bien au coin, au millimètre
près.

**Conséquence.** Deux tests distincts, un par régime, plutôt qu'un seuil affaibli. Le test en
régime gravitaire vérifie que la bille n'est *pas* entraînée, ce qui fixe une conclusion
physique au lieu d'une tolérance arbitraire.

**À retenir pour le rapport.** Bon exemple d'analyse critique d'un résultat de simulation : un
critère de validation a toujours un domaine de validité, et le délimiter fait partie de la
validation.

---

## 2026-10-06 — Projection sur convexe plutôt que forces sociales

**Options considérées.**

1. *Projection sur l'ensemble admissible* (Maury & Venel), dans le prolongement du cours.
2. *Modèle de forces sociales* (Helbing) : répulsion exponentielle et relaxation vers la vitesse
   désirée.
3. *Hybride* : forces pour le comportement, projection corrective en fin de pas.

**Décision : option 1.**

**Pourquoi.** Le modèle de forces sociales ne garantit pas la non-interpénétration : en panique,
les forces saturent et les agents se chevauchent. Il faudrait alors mesurer et justifier ce
recouvrement, alors que les consignes demandent précisément d'établir son absence. La projection
l'exclut **par construction**, ce qui transforme un critère d'évaluation en propriété acquise.

L'option 3 a été écartée par YAGNI : deux mécanismes concurrents rendent impossible d'attribuer
un effet observé à l'un plutôt qu'à l'autre, ce qui est exactement ce qu'une soutenance met à
l'épreuve.

---

## 2026-10-06 — Les trajectoires sont persistées, les observables calculés hors ligne

**Décision.** La boucle de simulation écrit les trajectoires sur disque ; les observables sont
calculés dans un second temps, à partir de ces fichiers.

**Pourquoi.** Un diagramme fondamental demande un balayage de paramètres sur plusieurs graines.
Si les observables étaient calculés au vol, ajouter une mesure ou corriger une définition de
densité imposerait de relancer toutes les simulations. Séparer les deux rend aussi
`observables/` testable sur des données synthétiques, sans faire tourner le moteur.

**Coût accepté.** De l'espace disque, et une étape de plus dans la chaîne de production des
figures.
