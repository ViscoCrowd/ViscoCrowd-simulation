"""Invariants du modele de foule sur la piscine de reference (E1 sec et E2 mouille).

Pour chaque evacuation (graines 1 a 10, deux sols) : plus fort recouvrement entre deux
agents actifs a tous les instants, plus forte violation des murs et du bord du bassin,
projections non convergees, agents sortis et franchissements par agent.

Les etats sont controles CONTRE LES POSITIONS, et non par leur somme : chaque agent a
toujours exactement un des quatre etats, donc eau + bord + plage + sortis = N par
construction, et ce controle ne pourrait jamais echouer (revue de Shaleena sur #145,
meme piege que #91). On verifie donc, a chaque instant archive :
  - EAU => centre dans le bassin ; PLAGE => hors du bassin et avant la ligne de porte ;
    FRANCHISSEMENT => exactement sur la position d'un site du bord ; SORTI => au point
    exterieur ;
  - aucun retour en arriere : eau -> bord -> plage -> sorti, jamais l'inverse ;
  - le nombre de SORTI egale le nombre d'instants de sortie enregistres <= t, une
    grandeur tenue a part par le scenario.
Un agent perdu, duplique ou mal place ferait echouer au moins l'un de ces controles.

Usage : python docs/mesures/invariants-piscine-2026-11-16/mesurer.py experiments/piscine.yaml
"""

import sys
from multiprocessing import Pool
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree

from viscocrowd.io.configuration import lire_configuration
from viscocrowd.scenarios.balayage_piscine import temoin
from viscocrowd.scenarios.campagne import contexte
from viscocrowd.scenarios.piscine import (
    EAU,
    FRANCHISSEMENT,
    PLAGE,
    SORTI,
    ParametresPiscine,
    simuler_piscine,
)

BASE = lire_configuration(Path(sys.argv[1]))["parametres"]


def mesurer(cas):
    sol, g = cas
    par = BASE if sol == "mouille" else temoin(BASE)
    r = simuler_piscine(ParametresPiscine(**par, graine=g))
    n, diametre = r.parametres.n_agents, 2 * r.parametres.rayon
    recouvrement = 0.0
    for x, e in zip(r.x, r.etats, strict=True):
        actifs = np.flatnonzero((e == EAU) | (e == PLAGE))
        if actifs.size > 1:
            paires = cKDTree(x[actifs]).query_pairs(diametre, output_type="ndarray")
            if paires.size:
                d = np.hypot(*(x[actifs][paires[:, 0]] - x[actifs][paires[:, 1]]).T)
                recouvrement = max(recouvrement, float(diametre - d.min()))
    piscine = r.parametres.piscine
    L = piscine.longueur_emprise
    (_, y_bas), (_, y_haut) = piscine.porte
    dehors = np.array([L + piscine.profondeur_porte, 0.5 * (y_bas + y_haut)])
    bords = np.array([site.position for site in piscine.sites()])
    positions_ok = True
    for x, e in zip(r.x, r.etats, strict=True):
        dedans = piscine.dans_bassin(x)
        eau, plage, sorti, bord = (e == EAU), (e == PLAGE), (e == SORTI), (e == FRANCHISSEMENT)
        ecart_bord = (
            np.min(np.hypot(*(x[bord][:, None, :] - bords[None, :, :]).transpose(2, 0, 1)), axis=1)
            if bord.any()
            else np.zeros(0)
        )
        positions_ok &= bool(
            np.all(dedans[eau])
            and np.all(~dedans[plage])
            and np.all(x[plage, 0] < L)
            and np.all(ecart_bord < 1e-12)
            and np.allclose(x[sorti], dehors, rtol=0, atol=1e-12)
        )
    sans_retour = bool(np.all(np.diff(r.etats, axis=0) >= 0))
    sortis_attendus = np.array([np.sum(r.sorties <= t + 1e-9) for t in r.t])
    sortis_coherents = bool(np.array_equal(np.sum(r.etats == SORTI, axis=1), sortis_attendus))
    agents = r.franchissements[:, 0].astype(int)
    return (
        sol,
        g,
        recouvrement,
        r.violation_paroi_max(),
        r.projection.non_convergences,
        int(np.isfinite(r.sorties).sum()),
        bool(np.array_equal(np.sort(agents), np.arange(n))),
        positions_ok,
        sans_retour,
        sortis_coherents,
        r.t.size,
    )


if __name__ == "__main__":
    print("# contexte :", contexte()["code"], contexte()["sources_sha256"][:16])
    print(
        "# sol graine recouvrement_max_m violation_murs_m non_convergees sortis "
        "un_franchissement_par_agent etats_conformes_aux_positions sans_retour "
        "sortis_conformes_aux_instants instants"
    )
    with Pool(8) as pool:
        for ligne in pool.imap(mesurer, [(s, g) for s in ("sec", "mouille") for g in range(1, 11)]):
            sol, g, rec, viol, nc, sortis, un, pos, mono, cohe, k = ligne
            print(
                f"{sol:7s} {g:2d} {rec:.3e} {viol:.3e} {nc} {sortis} {un} {pos} {mono} {cohe} {k}",
                flush=True,
            )
