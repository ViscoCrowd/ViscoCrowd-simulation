# ViscoCrowd — raccourcis de developpement.
# Chaque cible doit rester reproductible a l'identique sur les trois postes.

PYTHON ?= python
VENV   := .venv
BIN    := $(VENV)/bin
ifeq ($(OS),Windows_NT)
	BIN := $(VENV)/Scripts
endif

.PHONY: help install test lint format valider figures report docker clean

help:  ## Affiche cette aide
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) 		| awk 'BEGIN {FS = ":.*?## "}; {printf "  [36m%-12s[0m %s
", $$1, $$2}'

install:  ## Cree l'environnement et installe le projet
	$(PYTHON) -m venv $(VENV)
	$(BIN)/python -m pip install --upgrade pip
	$(BIN)/python -m pip install -e ".[dev]"

test:  ## Lance la suite de tests (hors scenarios lents)
	$(BIN)/python -m pytest -m "not slow"

test-all:  ## Lance tous les tests, scenarios lents compris
	$(BIN)/python -m pytest

lint:  ## Verifie le style et le formatage
	$(BIN)/python -m ruff check .
	$(BIN)/python -m ruff format --check .

format:  ## Reformate le code
	$(BIN)/python -m ruff format .
	$(BIN)/python -m ruff check --fix .

valider:  ## Rejoue les criteres de validation du moteur, chiffres
	$(BIN)/python -m viscocrowd.cli valider-moteur

figures:  ## Regenere toutes les figures
	$(BIN)/python -m viscocrowd.cli valider-moteur --figures --sortie report/figures

report:  ## Compile le rapport LaTeX
	cd report && latexmk -pdf -interaction=nonstopmode main.tex

docker:  ## Construit l'image Docker
	docker compose build

clean:  ## Supprime les artefacts generes
	rm -rf .pytest_cache .ruff_cache htmlcov .coverage figures
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
