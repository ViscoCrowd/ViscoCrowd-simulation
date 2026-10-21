"""Lecture des configurations YAML versionnees, sans construction d'objets Python."""

from pathlib import Path

import yaml


class _Chargeur(yaml.SafeLoader):
    """Refuse les doublons : une graine ecrasee silencieusement fausse la campagne."""


def _mapping(chargeur, noeud):
    resultat = {}
    for cle, valeur in noeud.value:
        nom = chargeur.construct_object(cle)
        if not isinstance(nom, str) or nom in resultat:
            raise ValueError(f"cle YAML non textuelle ou dupliquee : {nom!r}")
        resultat[nom] = chargeur.construct_object(valeur)
    return resultat


_Chargeur.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _mapping)


def lire_configuration(chemin: str | Path) -> dict:
    """Lit l'enveloppe v1 ; le scenario valide ensuite ses parametres physiques."""
    with Path(chemin).open(encoding="utf-8") as fichier:
        try:
            config = yaml.load(fichier, Loader=_Chargeur)
        except yaml.YAMLError as erreur:
            raise ValueError(f"configuration YAML invalide : {erreur}") from erreur
    if not isinstance(config, dict) or set(config) != {
        "version",
        "scenario",
        "graine",
        "parametres",
    }:
        raise ValueError("configuration attendue : version, scenario, graine, parametres")
    if type(config["version"]) is not int or config["version"] != 1:
        raise ValueError("version de configuration non prise en charge (attendu : 1)")
    if config["scenario"] not in ("bille_boite", "tassement"):
        raise ValueError("scenario attendu : bille_boite ou tassement")
    if not isinstance(config["parametres"], dict):
        raise ValueError("parametres doit etre une table YAML")
    graine = config["graine"]
    if config["scenario"] == "bille_boite":
        if graine is not None:
            raise ValueError("graine doit etre null pour bille_boite, scenario deterministe")
    elif type(graine) is not int or graine < 0:
        raise ValueError("graine doit etre un entier positif ou nul pour tassement")
    return config
