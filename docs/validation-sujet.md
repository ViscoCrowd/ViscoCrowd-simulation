# Demande de validation de sujet

**Module** R5.12 — Modélisation mathématique · BUT 3 Informatique · 2026-2027
**Groupe** ViscoCrowd — Karrouchi Hamza, Lesueur Shaleena, Mongrandi Lenny

> **Statut : acceptation du sujet rapportée par le groupe ; trace de l'échange à compléter.**

## Trace de validation

L'[issue #13](https://github.com/ViscoCrowd/ViscoCrowd-simulation/issues/13) consigne la
confirmation communiquée par le groupe le **13 octobre 2026**. C'est la trace du compte rendu
du groupe, pas celle de l'échange avec l'enseignant. Elle ne permet pas de dater cet échange
ni de vérifier qu'il a précédé l'implémentation.

| Élément à consigner | Information disponible |
|---|---|
| Enseignant ayant donné l'accord | À préciser ; O. Pantz est l'encadrant indiqué dans le dépôt |
| Date ou semaine de l'échange | Non renseignée ; le 13 octobre date seulement la confirmation du groupe |
| Canal (séance, courriel, Moodle…) | Non renseigné |
| Membre(s) ayant reçu l'accord | Non renseigné(s) |
| Contenu de la réponse, réserves éventuelles | Acceptation générale rapportée ; formulation et réserves non renseignées |

Un compte rendu d'accord oral suffit s'il précise ces éléments ; aucun justificatif écrit
de l'enseignant n'est présumé nécessaire. Compléter cette trace et les réponses ci-dessous
fait l'objet de l'[issue #19](https://github.com/ViscoCrowd/ViscoCrowd-simulation/issues/19),
coordonnée par Lenny, et de la [tâche C1 du planning](planning/README.md#cadrage-et-prerequis).
La cible est le **19 octobre 2026**. Une réponse manquante bloque ce qui en dépend, la mesure
de densité (SciPy/Voronoï) et toute inclusion des chutes, mais pas le jalon 3, qui n'en dépend
pas. Cette fiche centralise l'information ; les autres documents
y renvoient.

---

## Phénomène étudié

L'évacuation d'urgence d'une piscine couverte. La foule y traverse successivement trois milieux
dont les propriétés mécaniques diffèrent nettement :

1. **le bassin**, milieu aquatique à forte traînée visqueuse, que l'on quitte par une
   **extraction répartie** — le rebord, franchissable sur toute sa longueur mais lentement, et
   les échelles, peu nombreuses mais rapides. Chaque point de franchissement est à capacité
   unitaire ;
2. **la plage en carrelage mouillé**, à faible adhérence : l'accélération disponible est bornée,
   et l'agent ne peut donc ni s'arrêter ni changer de direction rapidement ;
3. **la zone sèche**, à adhérence nominale, qui se rétrécit vers un **goulot d'étranglement
   unique**.

Cette configuration nous intéresse parce qu'elle enchaîne deux régimes d'écoulement opposés —
une sortie *distribuée* puis une sortie *ponctuelle* — séparés par une zone où les agents
perdent le contrôle de leur trajectoire.

## Question posée

> Comment la succession d'une extraction aquatique répartie et d'un goulot d'étranglement unique
> en milieu sec, couplée à l'inertie d'une zone de carrelage mouillé, altère-t-elle le diagramme
> fondamental débit/densité d'une foule en panique ?

Deux mécanismes antagonistes sont plausibles, et les départager constitue le cœur du travail.
Soit l'extraction répartie et la traversée de la zone mouillée **désynchronisent** les arrivées
au goulot, ce qui abaisse la densité de pointe et augmente le débit. Soit la faible adhérence
**empêche les agents de réguler leur approche** : ils dépassent leur cible, se percutent, et la
densité effective au goulot augmente, dégradant le débit — un phénomène apparenté au
*faster-is-slower*.

Nous cherchons le signe et l'amplitude de cet effet sur la branche congestionnée du diagramme
fondamental, en fonction de la longueur et de l'adhérence de la zone mouillée.

## Type de modèle envisagé

Un modèle **particulaire à exclusion dure**, dans le prolongement direct du cours : à chaque pas
de temps, on calcule la position libre par un schéma d'Euler semi-implicite, puis on **projette
la configuration sur l'ensemble admissible** (non-recouvrement entre agents, confinement dans le
domaine). La vitesse est ensuite relue à partir du déplacement effectivement réalisé, ce qui
porte la loi de choc mou.

L'ensemble admissible n'étant pas convexe, nous suivrons l'approche de Maury et Venel :
linéarisation des contraintes autour de la configuration courante, puis projection **itérative**
sur l'intersection de demi-espaces obtenue.

Les trois milieux sont représentés par deux paramètres locaux — un temps de relaxation et une
accélération maximale — et la direction de déplacement souhaitée est donnée par un champ de
plus court temps de parcours, obtenu en résolvant l'équation eikonale. Le partage du flux entre
le rebord et les échelles devient ainsi une sortie du modèle plutôt qu'un paramètre imposé.

## Validation prévue

Outre les invariants (non-interpénétration, confinement, conservation du nombre d'agents) et les
études de sensibilité au pas de temps, au nombre d'agents et à la graine aléatoire, nous
confronterons nos sorties au **diagramme fondamental de Weidmann** et au débit spécifique de
goulot de la littérature.

Une simulation d'étalonnage sur un goulot sec seul, sans bassin ni zone mouillée, servira de
point de référence : si elle ne retrouve pas les valeurs connues, les résultats du scénario
complet ne vaudront rien.

---

## Questions de cadrage initialement posées à l'enseignant

L'acceptation générale du sujet ne vaut pas validation explicite de chaque bibliothèque,
paramètre ou extension du modèle. Les réponses manquantes sont suivies dans
l'[issue #19](https://github.com/ViscoCrowd/ViscoCrowd-simulation/issues/19) et la
[tâche C1](planning/README.md#cadrage-et-prerequis), avec une échéance au **19 octobre 2026**.

1. L'usage de SciPy pour le diagramme de Voronoï (calcul de la densité locale selon la méthode
   de Steffen et Seyfried) entre-t-il dans les bibliothèques généralistes autorisées ? Nous
   écrivons nous-mêmes le modèle, le schéma d'intégration et la projection ; il s'agit
   uniquement d'une routine de géométrie algorithmique.
2. Le périmètre vous paraît-il correctement dimensionné pour trois personnes sur treize
   semaines, ou faut-il resserrer la question ?

| Question | Réponse consignée | Conséquence tant que la réponse manque |
|---|---|---|
| SciPy pour Voronoï | Aucune réponse explicite disponible | SciPy est déjà une dépendance ; cela ne prouve pas l'accord pédagogique. Confirmer cet usage avant de développer la densité Voronoï ; en cas de refus, revoir la méthode et son calendrier avant les campagnes. |
| Dimensionnement du sujet | Acceptation générale rapportée, détail de la réponse absent | Présenter le périmètre principal sans le module de chutes et confirmer qu'il est tenable. |
| Extension aux chutes et au relevage | Addendum encore « à valider par le groupe » | Extension non programmée ; accord du groupe et avis de l'enseignant requis avant toute intégration au planning. |
