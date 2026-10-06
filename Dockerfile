# Image de reference du projet.
#
# Objectif unique : permettre de relancer les simulations et de retrouver
# EXACTEMENT les memes figures, sur n'importe quelle machine. C'est l'exigence
# de reproductibilite des consignes du module.
#
#   docker compose run --rm viscocrowd make valider

FROM python:3.12-slim

# Backend matplotlib hors ecran, et sortie Python non tamponnee pour que les
# logs apparaissent en direct dans la console.
ENV MPLBACKEND=Agg     PYTHONUNBUFFERED=1     PIP_NO_CACHE_DIR=1

RUN apt-get update  && apt-get install -y --no-install-recommends make  && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Les dependances sont installees AVANT le code source : tant que les versions
# ne bougent pas, cette couche reste en cache et la reconstruction est immediate.
COPY requirements.lock.txt ./
RUN pip install -r requirements.lock.txt

COPY pyproject.toml README.md LICENSE Makefile ./
COPY src/ ./src/
RUN pip install --no-deps -e .

COPY tests/ ./tests/
COPY experiments/ ./experiments/

CMD ["viscocrowd", "valider-moteur", "--figures"]
