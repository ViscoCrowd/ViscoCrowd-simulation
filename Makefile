# ViscoCrowd — raccourcis de developpement.
# Chaque cible doit rester reproductible a l'identique sur les trois postes.

PYTHON ?= python
VENV   ?= .venv
ifeq ($(OS),Windows_NT)
BIN    ?= $(VENV)/Scripts
else
BIN    ?= $(VENV)/bin
endif

# Interpreteur utilise par les cibles d'execution. Surchargeable par
# l'environnement : l'image Docker installe le projet GLOBALEMENT, sans .venv, et
# y fixe VISCO_PY=python. Sans cette indirection, `docker compose run --rm
# viscocrowd make valider` cherchait .venv/bin/python, absent de l'image, et la
# commande de reproductibilite documentee ne pouvait pas fonctionner.
#
# Le nom est prefixe a dessein : `PY` est une variable assez courante pour etre
# deja definie dans un shell, et elle detournerait alors toutes les cibles sans
# qu'on s'en apercoive.
VISCO_PY ?= $(BIN)/python

# Simulation lancee par `make simu`, et archive relue par `make rejouer`. L'heure dans
# le nom evite de refuser le second lancement : une archive n'est jamais ecrasee.
# Heure et derniere archive sont calculees par Python, deja requis : sous PowerShell,
# seul Git\cmd est dans le PATH par defaut, `ls` n'existe pas et `date` est la
# commande Windows qui demande une nouvelle date. Les diagnostics de projection
# (*.diagnostic.npz, #69) ne sont pas des trajectoires : ils sont ecartes.
CONFIG  ?= experiments/piscine.yaml
SORTIE  ?= data/$(basename $(notdir $(CONFIG)))-$(shell $(VISCO_PY) -c "import datetime as d; print(d.datetime.now().isoformat(timespec='seconds').replace(':', '').replace('-', '').replace('T', '-'))").npz
# Facteur de vitesse de la relecture : a 1, l'evacuation de la piscine (environ 54 s
# simulees) dure autant a l'ecran. Transmis aussi par `make lancer VITESSE=5`, car
# une variable de la ligne de commande passe aux sous-make.
VITESSE ?= 1
# Surcharges de la piscine pour simu et lancer (noms de balayer-piscine) :
# make simu FIXER="n_agents=150 largeur_porte=0.8"
FIXER ?=
ARCHIVE ?= $(shell $(VISCO_PY) -c "import pathlib; a = sorted((p for p in pathlib.Path('data').glob('*.npz') if not p.name.endswith('.diagnostic.npz')), key=lambda p: p.stat().st_mtime); print(a[-1].as_posix() if a else '')")

.PHONY: help install test test-all test-invariants test-lents lint format valider simu rejouer lancer menu demo comparer campagne-finale maquette figures report docker clean

help:  ## Affiche cette aide
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-16s %s\n", $$1, $$2}'

install:  ## Cree l'environnement et installe le projet
	$(PYTHON) -m venv $(VENV)
	$(BIN)/python -m pip install --upgrade pip
	$(BIN)/python -m pip install -e ".[dev]"

test:  ## Lance la suite de tests (hors scenarios lents)
	$(VISCO_PY) -m pytest -m "not slow"

test-all:  ## Lance tous les tests, scenarios lents compris
	$(VISCO_PY) -m pytest

test-invariants:  ## Lance uniquement les invariants physiques
	$(VISCO_PY) -m pytest -m invariant

test-lents:  ## Lance uniquement les scenarios lents
	$(VISCO_PY) -m pytest -m slow

lint:  ## Verifie le style et le formatage
	$(VISCO_PY) -m ruff check .
	$(VISCO_PY) -m ruff format --check .

format:  ## Reformate le code
	$(VISCO_PY) -m ruff format .
	$(VISCO_PY) -m ruff check --fix .

valider:  ## Rejoue les criteres de validation du moteur, chiffres
	$(VISCO_PY) -m viscocrowd.cli valider-moteur

simu:  ## Lance une simulation (CONFIG=... SORTIE=... FIXER="n_agents=150", piscine par defaut)
	$(VISCO_PY) -m viscocrowd.cli simuler $(CONFIG) --sortie $(SORTIE)$(if $(strip $(FIXER)), --fixer $(FIXER))

rejouer:  ## Relit une archive a l'ecran (ARCHIVE=..., la plus recente par defaut ; VITESSE=1)
	$(if $(strip $(ARCHIVE)),,$(error Aucune archive dans data/ : lancer d'abord make simu))
	$(VISCO_PY) -m viscocrowd.cli rejouer $(ARCHIVE) --vitesse $(VITESSE)

# Le nom de l'archive est fige une seule fois dans une variable du shell, puis passe
# aux deux sous-make : SORTIE contient l'heure, et la developper deux fois pourrait
# donner deux noms differents a une seconde pres. On ne compte pas non plus sur
# « la plus recente de data/ », qui relirait une ancienne archive si un autre calcul
# finissait entre-temps. Si la simulation echoue, la relecture n'est pas lancee.
lancer:  ## Simule puis ouvre la relecture (CONFIG=..., piscine ou couloir)
	@sortie="$(SORTIE)" && $(MAKE) --no-print-directory simu SORTIE="$$sortie" && $(MAKE) --no-print-directory rejouer ARCHIVE="$$sortie"

menu:  ## Parametre la piscine par questions, simule puis relit (CONFIG=...)
	$(VISCO_PY) -m viscocrowd.cli menu $(CONFIG)

demo:  ## Regenere les films de la soutenance dans data/demo/ (experiments/demo)
	$(VISCO_PY) -c "import shutil; shutil.rmtree('data/demo', ignore_errors=True)"
	$(VISCO_PY) -m viscocrowd.cli duel experiments/demo/duel-plage-glissante.yaml --gif data/demo/duel.gif
	$(VISCO_PY) -m viscocrowd.cli comparer-variantes experiments/demo/duel-plage-glissante.yaml --gif data/demo/variantes.gif \
		--variante adherence_mouille=3.3 --variante adherence_mouille=2 \
		--variante adherence_mouille=1
	$(VISCO_PY) -m viscocrowd.cli simuler experiments/demo/duel-plage-glissante.yaml --sortie data/demo/plage-glissante.npz
	$(VISCO_PY) -m viscocrowd.cli pose-longue data/demo/plage-glissante.npz \
		--image data/demo/pose-longue.png
	$(VISCO_PY) -m viscocrowd.cli pression experiments/demo/pression-porte-saturee.yaml \n		--image data/demo/pression.png --instant 35

comparer:  ## Compare la piscine seche et mouillee sur dix graines (E1/E2)
	$(VISCO_PY) -m viscocrowd.cli comparer-piscine experiments/piscine.yaml --graines 1 2 3 4 5 6 7 8 9 10

campagne-finale:  ## Rejoue la campagne finale, avec reprise (experiments/campagne-finale.yaml)
	$(VISCO_PY) -m viscocrowd.cli rejouer-campagne experiments/campagne-finale.yaml --sortie data/finale

# Ancien nom : `interface`. Renommee pour qu'on ne la prenne pas pour la simulation,
# que `make lancer` simule puis relit ; la commande Python garde son nom.
maquette:  ## Ouvre la maquette de la piscine, sans simulation
	$(VISCO_PY) -m viscocrowd.cli interface

figures:  ## Regenere toutes les figures
	$(VISCO_PY) -m viscocrowd.cli valider-moteur --figures --sortie report/figures

report:  ## Compile le rapport LaTeX
	cd report && latexmk -pdf -interaction=nonstopmode main.tex

docker:  ## Construit l'image Docker
	docker compose build

clean:  ## Supprime les artefacts generes
	rm -rf .pytest_cache .ruff_cache htmlcov .coverage figures
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
