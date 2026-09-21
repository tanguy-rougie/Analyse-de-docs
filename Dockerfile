FROM python:3.11-slim-bookworm

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    CHROMA_PERSIST_DIR=/app/chroma_db

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/

# Image commune à l'api et au worker : le port est déclaré par Compose côté api,
# le worker n'écoute rien. Commande par défaut = api.
CMD ["python", "-m", "src.web"]
