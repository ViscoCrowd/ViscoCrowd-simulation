# Cahier des charges — ViscoCrowd

**Module** R5.12 — Modélisation mathématique · BUT 3 Informatique (alternance) · 2026-2027
**Groupe** Karrouchi Hamza, Lesueur Shaleena, Mongrandi Lenny

---

## 1. Objet

Étudier, par simulation particulaire, comment l'enchaînement d'une extraction aquatique répartie
et d'un goulot d'étranglement unique, séparés par une zone de carrelage mouillé à faible
adhérence, déforme le diagramme fondamental débit/densité d'une foule en panique.

La problématique complète et le modèle retenu sont décrits dans la
[spécification de conception](superpowers/specs/2026-10-06-viscocrowd-design.md).

## 2. Livrables

| Livrable | Format | Échéance |
|---|---|---|
| Description du sujet pour validation | ≈ 1/2 page | **avant toute implémentation du modèle** |
| Rapport final | PDF, 15-20 p. hors annexes | **mardi 5 janvier 2027, 23h59** |
| Code | dépôt complet et reproductible | mardi 5 janvier 2027, 23h59 |
| Transparents | format libre | **lundi 18 janvier 2027, 18h00** |
| Soutenance | 10 min + 10 min de questions | **mardi 19 janvier 2027** |

Dépôt **exclusivement sur Moodle**. Aucun envoi par courriel n'est pris en compte.
Retard non justifié : **2 points de pénalité par jour entamé**.

## 3. Exigences fonctionnelles

| # | Exigence | Vérifiable par |
|---|---|---|
| F1 | Simuler N agents en exclusion dure dans un domaine à géométrie libre | tests d'invariants |
| F2 | Représenter trois milieux aux propriétés mécaniques distinctes | scénario paramétré |
| F3 | Représenter des points de franchissement à capacité unitaire | observable de débit par site |
| F4 | Guider les agents vers la sortie par un champ de plus court temps | figure du champ |
| F5 | Mesurer densité et débit, et tracer le diagramme fondamental | figures du rapport |
| F6 | Permettre un balayage de paramètres sur plusieurs graines | configs `experiments/` |

## 4. Exigences non fonctionnelles

| # | Exigence | Origine |
|---|---|---|
| NF1 | Toute exécution est reproductible à graine fixée | consignes, § Reproductibilité |
| NF2 | Chaque figure du rapport est traçable jusqu'à sa configuration | consignes, § Reproductibilité |
| NF3 | Le modèle est écrit par le groupe, sans bibliothèque spécialisée | consignes, § Bibliothèques |
| NF4 | Chaque membre peut expliquer et modifier n'importe quelle partie | consignes, § IA et § Soutenance |
| NF5 | Le code est lisible et commenté sur le *pourquoi* | barème, critère de forme |
| NF6 | Toute régression physique est détectée automatiquement | choix du groupe |

**NF4 structure toute notre organisation.** C'est de lui que découlent la revue croisée
obligatoire et le refus de fusionner du code qu'un membre ne saurait pas réécrire.

## 5. Critères d'acceptation de la validation

Repris des consignes, chacun doit produire un **nombre** dans le rapport :

- [ ] **Invariants** — conservation du nombre d'agents ; absence d'interpénétration ; absence de
      sortie du domaine. *L'écart mesuré est donné, pas seulement affirmé.*
- [ ] **Sensibilité à la discrétisation** — comportement quand le pas de temps diminue et quand
      le nombre d'agents augmente. Les conclusions physiques doivent être stables.
- [ ] **Comparaison à un résultat connu** — diagramme fondamental de Weidmann et débit spécifique
      de goulot de la littérature.
- [ ] **Cohérence dimensionnelle** — unités de toutes les grandeurs, et ordres de grandeur
      vérifiés.

## 6. Contraintes sur les figures

- Numérotée, légendée, et **appelée dans le corps du texte**.
- Axes nommés, **portant leurs unités** ; courbes multiples distinguées par une légende.
- Paramètres de la simulation ayant produit la figure indiqués.
- **Aucune capture d'écran** d'une fenêtre de simulation en guise de graphique.

## 7. Structure du rapport

Résumé (1/2 page max) · Introduction · Modélisation · Discrétisation numérique · Implémentation ·
Validation · Interprétation et analyse · Conclusion · Références · Annexes.

Aucune section ne s'intitule « Développement ».

**Annexes obligatoires** — tableau de répartition des tâches (qui a fait quoi, dans quelle
proportion) et section sur les outils utilisés, notamment d'IA générative, et pour quels usages.

**Bonus** — 1 point sur l'ensemble du module si le rapport est rédigé en LaTeX. Il l'est.

## 8. Risques identifiés

| Risque | Impact | Parade |
|---|---|---|
| La projection itérative ne converge pas assez vite | bloquant, jalon 2 | mesurer le résidu dès le premier jour ; plafonner les itérations et publier le résidu atteint |
| Coût en temps de calcul sur les balayages | retard jalon 5 | grille de hachage spatial ; lancer les campagnes longues tôt |
| Les deux effets antagonistes se compensent | résultat peu lisible | E1 et E2 isolent chaque effet séparément |
| Désynchronisation du groupe (alternance) | qualité du rapport | PR courtes et fréquentes ; revue sous 48 h |
| Sujet non validé à temps | **évaluation compromise** | demi-page rédigée dès le jalon 0 |

## 9. Hors périmètre

Troisième dimension · chocs élastiques · modèle de forces sociales en parallèle · hétérogénéité
comportementale fine · interface graphique interactive.
