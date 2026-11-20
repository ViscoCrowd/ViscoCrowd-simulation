"""#198 : le goulot E0 a-t-il, comme la porte de la piscine, des paliers de debit sous 0,9 m ?

Question, ecrite avant le calcul. Dans la piscine, le debit de la porte saturee vaut
1,79 pers/s de 0,75 a 0,82 m, puis 1,92 pers/s a 0,85 et 0,88 m, et la porte ne sature plus
a 0,90 m (mesure de Shaleena dans #198). Piste : un passage par voies discretes, propre aux
disques durs (deux disques de 0,40 m de diametre tiennent de front vers 0,9 m). Le goulot
E0 (#141) n'a ete mesure qu'aux largeurs 0,8 ; 0,9 ; ... ; 1,2 m, trop espacees pour le voir.

Protocole : E0 de reference (`experiments/goulot.yaml`, N = 60, T = 0,35 s), graines 1 a
10, largeurs 0,75 ; 0,78 ; 0,80 ; 0,82 ; 0,85 ; 0,88 ; 0,90 ; 0,95 ; 1,00 m. Debit en
pers/s : Q = J_s * b (J_s du protocole de Seyfried, comme `etalonner-goulot`). Seuls les
ecoulements comptent, les autres regimes sont comptes a part.

Criteres, fixes avant le calcul, entre deux largeurs voisines k et k+1 (moyennes sur les
graines, ecart apparie graine par graine) :
  - palier : |Q(k+1) / Q(k) - 1| < 2 % ;
  - saut : Q(k+1) / Q(k) - 1 > 2 (b(k+1) / b(k) - 1), et l'ecart apparie depasse deux
    erreurs standard ;
  - E0 montre la meme quantification que la porte s'il a au moins un palier sous 0,90 m
    ET un saut entre 0,80 et 0,95 m. Sinon, les paliers sont propres a la porte de la
    piscine (montants arrondis, alimentation par la plage), et seule la piscine porte la
    limite du rapport.

Usage, depuis la racine du depot (arbre propre) :
    python docs/mesures/e0-paliers-2026-11-20/paliers.py experiments/goulot.yaml sortie.json
"""

import json
import sys
from itertools import pairwise
from multiprocessing import Pool
from pathlib import Path

import numpy as np

from viscocrowd.io.configuration import lire_configuration
from viscocrowd.scenarios.campagne import contexte
from viscocrowd.scenarios.goulot import etalonner

LARGEURS = (0.75, 0.78, 0.80, 0.82, 0.85, 0.88, 0.90, 0.95, 1.00)
GRAINES = tuple(range(1, 11))


def mesurer(largeur):
    config = lire_configuration(Path(sys.argv[1]))
    mesures = etalonner(config, [largeur], GRAINES)[largeur]
    return largeur, [{"graine": m.graine, "statut": m.statut, "debit": m.debit} for m in mesures]


def debits(mesures, largeur):
    """Debit Q (pers/s) par graine, NaN hors ecoulement."""
    return np.array(
        [m["debit"] * largeur if m["statut"] == "ecoulement" else np.nan for m in mesures]
    )


if __name__ == "__main__":
    sortie = Path(sys.argv[2])
    if sortie.exists():
        raise SystemExit(f"{sortie} existe deja")
    ctx = contexte()
    with Pool(len(LARGEURS)) as pool:
        resultats = dict(pool.map(mesurer, LARGEURS))

    print("Largeur | Q (pers/s) | J_s (pers/(m.s)) | ecoulements")
    q = {}
    for b in LARGEURS:
        q[b] = debits(resultats[b], b)
        n = int(np.sum(np.isfinite(q[b])))
        print(
            f"  {b:.2f} m | {np.nanmean(q[b]):.3f} ± {np.nanstd(q[b], ddof=1):.3f}"
            f" | {np.nanmean(q[b]) / b:.3f} | {n}/10"
        )
    print("Voisines | Q(k+1)/Q(k) - 1 | 2 (b(k+1)/b(k) - 1) | ecart apparie (pers/s) | verdict")
    verdicts = []
    for b0, b1 in pairwise(LARGEURS):
        rapport = np.nanmean(q[b1]) / np.nanmean(q[b0]) - 1
        seuil = 2 * (b1 / b0 - 1)
        ecart = q[b1] - q[b0]
        ecart = ecart[np.isfinite(ecart)]
        moyenne, es = float(np.mean(ecart)), float(np.std(ecart, ddof=1) / np.sqrt(ecart.size))
        if abs(rapport) < 0.02:
            verdict = "palier"
        elif rapport > seuil and moyenne > 2 * es:
            verdict = "saut"
        else:
            verdict = "-"
        verdicts.append({"de": b0, "a": b1, "rapport": rapport, "verdict": verdict})
        print(
            f"  {b0:.2f} -> {b1:.2f} | {rapport:+.3f} | {seuil:.3f}"
            f" | {moyenne:+.3f} ± {es:.3f} | {verdict}"
        )
    palier = any(v["verdict"] == "palier" and v["a"] < 0.90 for v in verdicts)
    saut = any(v["verdict"] == "saut" and v["de"] >= 0.80 and v["a"] <= 0.95 for v in verdicts)
    conclusion = "meme quantification que la porte" if palier and saut else "pas de quantification"
    print(f"Conclusion selon le critere : {conclusion} (palier {palier}, saut {saut})")

    bilan = {
        "version": 1,
        "contexte": ctx,
        "largeurs": LARGEURS,
        "graines": GRAINES,
        "mesures": {str(b): resultats[b] for b in LARGEURS},
        "voisines": verdicts,
        "conclusion": conclusion,
    }
    sortie.parent.mkdir(parents=True, exist_ok=True)
    sortie.write_text(json.dumps(bilan, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Bilan : {sortie}")
