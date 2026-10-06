# Demande de validation de sujet

**Module** R5.12 — Modélisation mathématique · BUT 3 Informatique · 2026-2027
**Groupe** ViscoCrowd — Karrouchi Hamza, Lesueur Shaleena, Mongrandi Lenny

> ⚠️ **À relire par les trois membres, puis à transmettre à l'enseignant avant de commencer
> l'implémentation du modèle de foule.** Les consignes précisent qu'un travail mené sur un
> sujet non validé ne pourra pas être évalué dans de bonnes conditions.

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

## Questions à l'enseignant

1. L'usage de SciPy pour le diagramme de Voronoï (calcul de la densité locale selon la méthode
   de Steffen et Seyfried) entre-t-il dans les bibliothèques généralistes autorisées ? Nous
   écrivons nous-mêmes le modèle, le schéma d'intégration et la projection ; il s'agit
   uniquement d'une routine de géométrie algorithmique.
2. Le périmètre vous paraît-il correctement dimensionné pour trois personnes sur treize
   semaines, ou faut-il resserrer la question ?
