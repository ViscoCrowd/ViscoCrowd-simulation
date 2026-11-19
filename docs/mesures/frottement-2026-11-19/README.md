# Frottement consommé par la marche : prototype (19 novembre 2026)

Prototype sans modification du code, discuté dans l'issue « le mouillé n'agit presque pas ».
Commit `6626819` (branche de #163), graines 1 à 10, mouillé contre témoin sec apparié.

- `frottement.py` : sur la plage, l'accélération disponible devient (μ − RCOF) g, avec
  RCOF = 0,20 (Beschorner et al. 2016) ou 0,25 (essai pour la marche rapide). Référence et
  navigation τ = 0,20 s (#158). Compte aussi les glissades attendues avec la logistique de
  Beschorner et al. (2016), sans faire tomber personne.
- `frottement-dt2.py` : le même au pas de temps divisé par deux (critère 2 du § 3 des
  critères d'acceptation).

| Mouillé − sec, Δt50 | Δt = 0,01 s, RCOF 0,20 | Δt/2, RCOF 0,20 | Δt = 0,01 s, RCOF 0,25 | Δt/2, RCOF 0,25 |
|---|---|---|---|---|
| Référence | +0,47 s (9/10) | +0,47 s (9/10) | +1,22 s (10/10) | +1,23 s (10/10) |
| Navigation τ = 0,20 s | +0,75 s (9/10) | +0,50 s (9/10) | +1,06 s (9/10) | +0,74 s (8/10) |

Les glissades attendues (160 à 430 par évacuation de 100 baigneurs) ne sont pas plausibles :
la loi est appliquée à l'accélération voulue du modèle, qui fait des à-coups. Ce volet n'est
pas exploitable en l'état.
