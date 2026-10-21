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

.PHONY: help install test lint format valider interface figures report docker clean

help:  ## Affiche cette aide
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-12s %s\n", $$1, $$2}'

install:  ## Cree l'environnement et installe le projet
	$(PYTHON) -m venv $(VENV)
	$(BIN)/python -m pip install --upgrade pip
	$(BIN)/python -m pip install -e ".[dev]"

test:  ## Lance la suite de tests (hors scenarios lents)
	$(VISCO_PY) -m pytest -m "not slow"

test-all:  ## Lance tous les tests, scenarios lents compris
	$(VISCO_PY) -m pytest

lint:  ## Verifie le style et le formatage
	$(VISCO_PY) -m ruff check .
	$(VISCO_PY) -m ruff format --check .

format:  ## Reformate le code
	$(VISCO_PY) -m ruff format .
	$(VISCO_PY) -m ruff check --fix .

valider:  ## Rejoue les criteres de validation du moteur, chiffres
	$(VISCO_PY) -m viscocrowd.cli valider-moteur

interface:  ## Ouvre l'apercu de la piscine (affichage local)
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
