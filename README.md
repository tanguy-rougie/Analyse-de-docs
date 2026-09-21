# Analyse-de-docs

Une entreprise veut permettre à ses ingénieurs d'interroger en langage naturel une base de documentation technique (specs, manuels, rapports). Le dépôt vise un pipeline RAG complet, évalué et déployable.

## Démarrage rapide

1. **Environnement** : `conda env create -f environment.yml` puis `conda activate analyse-de-docs`
2. **Configuration** : `copy .env.example .env` — Ollama + `llama3.2` par défaut (`ollama pull llama3.2`)
3. **PDF** : placer les fichiers dans `Documents/` (non versionné)
4. **Indexation** : `python -m src.ingestion --input-dir ./Documents --collection technical_docs --reset` → crée `chroma_db/` (non versionné)
5. **Interface** : `python -m src.web` → [http://localhost:8000](http://localhost:8000) ; pour les jobs, lancer aussi `python -m src.worker` dans un second terminal. En Docker, interface Streamlit sur [http://localhost:8501](http://localhost:8501)

**Docker** : `docker compose up --build`, puis `docker compose exec ollama ollama pull llama3.2`

Après un clone, refaire les étapes 3–5 (les données locales ne sont pas sur GitHub).

## Pipeline d’ingestion (PDF → chunks → embeddings → ChromaDB)

### Prérequis

- Python 3.10+
- Environnement Conda : depuis la racine du dépôt, `conda env create -f environment.yml` puis `conda activate analyse-de-docs` (mise à jour : `conda env update -f environment.yml --prune`)

### Comportement

1. **Lecture PDF** : extraction du texte **par page** avec `pypdf`.
2. **Chunking** : découpage récursif (`RecursiveCharacterTextSplitter`) avec une limite en **tokens** mesurée par le **tokenizer Hugging Face du même modèle** que les embeddings (aligné avec `sentence-transformers`).
3. **Paramètres par défaut** : 512 tokens, chevauchement 50 (variables d’environnement `CHUNK_SIZE`, `CHUNK_OVERLAP`).
4. **Taille effective** : si `tokenizer.model_max_length` est une valeur réaliste (≤ 8192), la taille des chunks est `min(CHUNK_SIZE, model_max_length)` pour limiter la troncature côté modèle. Les placeholders HF très grands sont ignorés et on garde `CHUNK_SIZE`.
5. **Embeddings + stockage** : `SentenceTransformerEmbeddingFunction` (Chroma) avec le modèle `EMBEDDING_MODEL` (défaut **`BAAI/bge-small-en-v1.5`**, contexte adapté à des chunks de 512 tokens).
6. **Index vectoriel** : les collections sont créées avec **`hnsw:space: cosine`** (similarité cosinus). Si une collection a été créée **avant** ce réglage, elle peut encore utiliser une autre métrique : **ré-ingérez avec `--reset`** pour repartir sur une indexation cosinus cohérente.
7. **Persistance** : répertoire `CHROMA_PERSIST_DIR` (défaut `./chroma_db`).

### Variables d’environnement

| Variable | Défaut | Rôle |
|----------|--------|------|
| `CHROMA_PERSIST_DIR` | `./chroma_db` | Dossier de persistance Chroma |
| `EMBEDDING_MODEL` | `BAAI/bge-small-en-v1.5` | Modèle sentence-transformers |
| `CHUNK_SIZE` | `512` | Taille max d’un chunk (tokens) |
| `CHUNK_OVERLAP` | `50` | Chevauchement (tokens) |
| `INGEST_BATCH_SIZE` | `256` | Taille des lots pour `collection.add` |

### Commande (depuis la racine du dépôt)

Placez des fichiers `.pdf` dans un dossier (ex. `Documents/` ; seuls les PDF **directement** dans ce dossier sont pris en charge, pas les sous-dossiers).

```bash
python -m src.ingestion --input-dir ./Documents --collection technical_docs --reset
```

- `--reset` : supprime la collection existante puis la recrée avant d’ingérer (recommandé pour une réindexation complète).
- Sans `--reset`, une nouvelle ingestion des mêmes pages peut entrer en conflit avec des IDs déjà présents dans Chroma.

### Sortie

Le programme affiche un JSON résumé, par exemple :

```json
{
  "pages_loaded": 42,
  "chunks_written": 310,
  "collection": "technical_docs",
  "persist_dir": "C:\\...\\chroma_db"
}
```

### Structure du code

- `src/ingestion/pdf_loader.py` — PDF → documents par page
- `src/ingestion/chunker.py` — découpage token-aware
- `src/ingestion/chroma_store.py` — client Chroma persistant et ajout par lots
- `src/ingestion/pipeline.py` — orchestration
- `src/ingestion/__main__.py` — CLI

### Vérification rapide après ingestion

Dans un interpréteur Python (racine du dépôt sur `PYTHONPATH`, ou même cwd) :

```python
import chromadb
from chromadb.utils import embedding_functions
from src.ingestion.config import IngestionConfig

cfg = IngestionConfig.from_env()
client = chromadb.PersistentClient(path=cfg.chroma_persist_dir)
col = client.get_collection(
    "technical_docs",
    embedding_function=embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=cfg.embedding_model
    ),
)
print(col.count())
print(col.query(query_texts=["your test query"], n_results=2))
```

## Pipeline RAG (retrieval cosinus top-k → rerank optionnel → LLM)

Le retrieval utilise **top-k** sur Chroma en **similarité cosinus** (voir docstring de `src/retrieval/chroma_retriever.py` : en espace cosinus Chroma, `cosine_similarity ≈ 1 - distance`).

### Mode basique (défaut)

Sans rerank CrossEncoder, le contexte LLM est formé à partir des **`k`** meilleurs passages Chroma uniquement :

- `USE_RERANKING=false` (défaut)
- `RETRIEVE_K=5` et `RERANK_TOP_N=5` (défaut) : même `k` pour la recherche et pour le nombre de passages envoyés au LLM

Pour activer le rerank : `USE_RERANKING=true` et augmenter `RETRIEVE_K` (ex. `20`).

### Variables d’environnement (RAG)

| Variable | Défaut | Rôle |
|----------|--------|------|
| `RETRIEVE_K` | `5` | Top-k passages retournés par Chroma (similarité cosinus) |
| `RERANK_TOP_N` | `5` | Passages gardés pour le contexte LLM |
| `USE_RERANKING` | `false` | `true` pour CrossEncoder après Chroma |
| `CROSS_ENCODER_MODEL` | `cross-encoder/ms-marco-MiniLM-L-6-v2` | Modèle sentence-transformers pour le rerank |
| `LLM_PROVIDER` | `ollama` | `ollama` (défaut), `openai`, ou `mistral` |
| `OLLAMA_BASE_URL` | `http://127.0.0.1:11434` | Serveur Ollama local |
| `OLLAMA_MODEL` | `llama3.2` | Modèle Ollama (`ollama pull llama3.2` si absent) |
| `OLLAMA_HTTP_TIMEOUT` | `600` | Timeout HTTP (secondes) pour `/api/chat` — utile sur CPU lent |
| `OPENAI_MODEL` | `gpt-4o-mini` | Modèle OpenAI (`OPENAI_API_KEY` requis si `LLM_PROVIDER=openai`) |
| `MISTRAL_API_KEY` | — | Requis si `LLM_PROVIDER=mistral` |
| `MISTRAL_MODEL` | `mistral-small-latest` | Modèle Mistral |
| `MISTRAL_BASE_URL` | `https://api.mistral.ai/v1` | API compatible schéma OpenAI |

Les variables d’ingestion (`CHROMA_PERSIST_DIR`, `EMBEDDING_MODEL`, …) doivent correspondre à celles utilisées lors de l’indexation.

### CLI

```bash
python -m src.retrieval --collection technical_docs "Quel est le sujet du document ?"
```

Avec aperçus de chunks et scores :

```bash
python -m src.retrieval --collection technical_docs --verbose -q "Votre question"
```

Sous Windows, si les guillemets posent problème :

```bash
python -m src.retrieval --collection technical_docs -q "Votre question"
```

La sortie JSON contient : `answer`, `sources` (fichier, page, `distance`, `cosine_similarity`), `used_reranking`, et si `--verbose` : `chunk_details`.

### Tests manuels (5–10 questions)

1. Adapter [`eval/questions.txt`](eval/questions.txt) à vos documents.
2. Lancer `python scripts/run_manual_questions.py` (ajoute des lignes à `eval/manual_runs.jsonl`, ignoré par git par défaut).
3. Consigner observations et problèmes dans [`eval/MANUAL_TEST_LOG.md`](eval/MANUAL_TEST_LOG.md).

### Code

- `src/retrieval/chroma_retriever.py` — top-k, scores cosinus
- `src/retrieval/reranker.py` — CrossEncoder
- `src/retrieval/rag.py` — `answer_question(...)`
- `src/generation/prompts.py` — prompt système + contexte borné
- `src/generation/llm_client.py` — OpenAI / Mistral / Ollama

## Interface web (FastAPI)

Interface pour saisir une question en langage naturel et afficher la réponse RAG avec les sources.

### Prérequis

- Index Chroma déjà ingéré (voir section ingestion).
- **Ollama** installé et démarré, modèle **llama3.2** disponible :

```bash
ollama pull llama3.2
```

(Sous Windows, l’app Ollama suffit en général ; le serveur écoute sur `http://127.0.0.1:11434`.)

### Variables d’environnement (web)

| Variable | Défaut | Rôle |
|----------|--------|------|
| `RAG_COLLECTION` | `technical_docs` | Collection interrogée |
| `WEB_HOST` | `0.0.0.0` | Adresse d’écoute uvicorn |
| `WEB_PORT` | `8000` | Port HTTP |
| `DATABASE_URL` | `postgresql+psycopg://analyse:analyse@localhost:5432/analyse` | PostgreSQL pour les **jobs** (pas pour les vecteurs) |
| `WORKER_POLL_INTERVAL` | `2` | Secondes entre deux interrogations de la file quand elle est vide |
| `WORKER_SIMULATED_DURATION` | `3` | Durée du traitement simulé, pour `job_type=simulate` (secondes) |

### Jobs (étape 1)

L’API **enregistre** un travail dans PostgreSQL ; elle ne l’exécute pas (c’est le worker qui s’en charge). États : `PENDING` → `RUNNING` → `COMPLETED` / `FAILED`.

Un job porte les paramètres d’entrée dans `payload` (`job_type`, `input_dir`, `collection`, `reset`) et, une fois terminé, le résumé produit par le worker dans `result`.

Couches (à lire dans cet ordre) :

1. Contrôleur HTTP : [`src/web/controllers/jobs.py`](src/web/controllers/jobs.py)
2. Service : [`src/jobs/service.py`](src/jobs/service.py)
3. Repository : [`src/jobs/repository.py`](src/jobs/repository.py)
4. Modèle / table : [`src/jobs/models.py`](src/jobs/models.py)

```bash
curl -s http://localhost:8000/health
curl -s -X POST http://localhost:8000/jobs -H "Content-Type: application/json" -d "{\"job_type\":\"simulate\"}"
curl -s http://localhost:8000/jobs/<job_id>
```

PostgreSQL local sans tout lancer : `docker compose up -d postgres`, puis `python -m src.web`.

ChromaDB reste le vector store. PostgreSQL ne stocke ici que les jobs. `Documents/` est un dossier local de PDF, pas un équivalent de S3.

### Worker (étape 2)

Processus **séparé** de l’API : il interroge la table `jobs`, prend le plus ancien `PENDING`, le passe en `RUNNING`, exécute le travail, puis écrit `COMPLETED` ou `FAILED`. L’API n’exécute rien elle-même (pas de `BackgroundTasks`).

```bash
# terminal 1
python -m src.web
# terminal 2
python -m src.worker
```

Trois types de jobs, distingués par `job_type` dans [`src/worker/runner.py`](src/worker/runner.py) :

| `job_type` | Effet |
|------------|-------|
| `ingest` | Appelle le pipeline d’ingestion réel (voir étape 6) |
| `simulate` | Attend `WORKER_SIMULATED_DURATION` secondes, sans rien indexer |
| `fail` | Lève une erreur pour observer l’état `FAILED` |

```bash
curl -s -X POST http://localhost:8000/jobs -H "Content-Type: application/json" -d "{\"job_type\":\"simulate\"}"
curl -s http://localhost:8000/jobs/<job_id>   # RUNNING, puis COMPLETED
```

Code : [`src/worker/__main__.py`](src/worker/__main__.py) (boucle), [`src/worker/runner.py`](src/worker/runner.py) (traitement d’un job), [`src/worker/config.py`](src/worker/config.py).

`SELECT FOR UPDATE SKIP LOCKED` n’est **pas** utilisé : avec un seul worker, personne ne peut prendre le même job en même temps. Ce verrouillage ne deviendrait utile qu’en lançant plusieurs workers en parallèle.

### Lancement local

1. Copier [`.env.example`](.env.example) vers `.env` (déjà prévu pour **Ollama + llama3.2**).
2. Vérifier qu’Ollama tourne et que le modèle est installé (`ollama pull llama3.2`).
3. Démarrer le serveur :

```bash
python -m src.web
```

Le fichier `.env` est chargé automatiquement. Variables par défaut : `LLM_PROVIDER=ollama`, `OLLAMA_MODEL=llama3.2`, `OLLAMA_BASE_URL=http://127.0.0.1:11434`.

Ouvrir [http://localhost:8000](http://localhost:8000). L’API REST : `GET /health`, `POST /jobs`, `GET /jobs/{job_id}`, `POST /api/ask` (body `{ "question": "...", "verbose": false }`).

Pour OpenAI ou Mistral à la place, modifiez `LLM_PROVIDER` et les clés dans `.env`.

### Code

- `src/web/app.py` — application FastAPI (Q&A + branchement des contrôleurs)
- `src/web/controllers/` — routes `/health` et `/jobs`
- `src/jobs/` — persistance PostgreSQL des jobs
- `src/worker/` — exécution des jobs, hors API
- `src/web/static/index.html` — formulaire Q&A
- `src/web/__main__.py` — serveur uvicorn

## Docker

### Prérequis

- Docker et Docker Compose.
- Fichier `.env` optionnel à la racine (copier depuis `.env.example`). Compose surcharge `OLLAMA_BASE_URL` vers `http://ollama:11434` et `DATABASE_URL` vers le service `postgres`.

### Services (étape 3)

Un conteneur par rôle, sur le réseau interne de Compose :

| Service | Rôle | Port hôte |
|---------|------|-----------|
| `frontend` | Interface Streamlit, cliente HTTP de l’`api` | `8501` |
| `api` | FastAPI : `/health`, `/jobs`, `/api/ask` | `8000` |
| `worker` | Exécute les jobs, aucun port exposé | — |
| `postgres` | Table `jobs` | `5432` |
| `ollama` | LLM local pour le Q&A | `11434` |
| `registry` | Dépôt d’images local (outil d’apprentissage) | `5001` |

`api` et `worker` partagent **la même image** (`analyse-de-docs-app:local`, construite depuis le [`Dockerfile`](Dockerfile)) : seule la commande de démarrage diffère (`python -m src.web` contre `python -m src.worker`). Un seul code, deux processus — comme deux tâches lancées depuis une même image sur un orchestrateur.

`depends_on` + healthchecks donnent un ordre de démarrage : l’`api` et le `worker` attendent que Postgres réponde à `pg_isready`. L’`api` a son propre healthcheck qui appelle `/health`.

Docker Compose sert ici d’**orchestrateur local pédagogique**. Ce n’est pas un équivalent technique d’ECS/Fargate ; il reproduit seulement les concepts (services séparés, réseau interne, variables d’environnement, dépendances).

### Lancer la stack

```bash
docker compose up --build
```

Puis [http://localhost:8501](http://localhost:8501) (Streamlit) ou [http://localhost:8000](http://localhost:8000) (API et page HTML). Vérifier l’état des conteneurs :

```bash
docker compose ps
docker compose logs -f worker   # voir les jobs passer RUNNING puis COMPLETED
```

Première utilisation — télécharger le modèle dans le conteneur Ollama :

```bash
docker compose exec ollama ollama pull llama3.2
```

Volumes : `./chroma_db` (index Chroma, vector store actuel), `./Documents` (PDF en local), cache Hugging Face (`hf_cache`), volume `postgres_data` (table `jobs`).

### Ingestion dans le conteneur

L’image contenant tout le code, la CLI d’ingestion reste disponible telle quelle :

```bash
docker compose run --rm worker python -m src.ingestion --input-dir /app/Documents --collection technical_docs --reset
```

## Ingestion déclenchée par un job (étape 6)

Le worker appelle maintenant le **pipeline d’ingestion existant**, sans le modifier : `ingest()` de [`src/ingestion/pipeline.py`](src/ingestion/pipeline.py), donc pypdf, chunking token-aware, embeddings `BAAI/bge-small-en-v1.5` et ChromaDB comme avant. Seul le déclencheur change : une ligne dans PostgreSQL au lieu d’une commande tapée à la main.

```bash
curl -s -X POST http://localhost:8000/jobs -H "Content-Type: application/json" \
  -d '{"job_type":"ingest","input_dir":"./Documents","collection":"technical_docs","reset":true}'
curl -s http://localhost:8000/jobs/<job_id>
```

Le résumé renvoyé par `ingest()` est stocké dans la colonne `result` et lisible via l’API :

```json
"result": {
  "pages_loaded": 203,
  "chunks_written": 485,
  "collection": "technical_docs",
  "persist_dir": "/app/chroma_db"
}
```

En cas d’erreur, le job passe `FAILED` et `error_message` contient le message du pipeline (par exemple `Not a directory: /app/DossierInexistant`). Le worker continue de tourner : un job raté ne l’arrête pas.

Suivre l’avancement pendant l’indexation :

```bash
docker compose logs -f worker
```

La CLI `python -m src.ingestion` reste disponible et fait exactement la même chose. Les deux chemins appellent la même fonction.

**Changement de schéma** : la colonne `result` a été ajoutée à la table `jobs`. Sur une base créée avant cette étape, l’ajouter une fois :

```bash
docker compose exec postgres psql -U analyse -d analyse -c "ALTER TABLE jobs ADD COLUMN IF NOT EXISTS result JSONB;"
```

`create_all` ne crée que les tables manquantes, jamais les colonnes manquantes. C’est précisément le besoin auquel répond un outil de migration comme Alembic, non utilisé ici pour garder le projet simple.

## Interface Streamlit (étape 5)

Interface unique pour les deux usages : poser une question (synchrone) et créer puis suivre un job (asynchrone).

```bash
docker compose up -d
```

Puis [http://localhost:8501](http://localhost:8501).

- **Poser une question** → `POST /api/ask` : réponse et sources affichées directement. Nécessite Ollama et un index Chroma.
- **Jobs** → `POST /jobs` crée le travail, puis « Actualiser l’état » appelle `GET /jobs/{id}` : on voit `PENDING`, `RUNNING`, puis `COMPLETED` (ou `FAILED` avec le type `fail`). Le type `ingest` lance la vraie indexation ; le résumé apparaît dans `result`.

Le frontend ne parle **qu’à l’API** : pas d’accès à PostgreSQL, pas d’import du pipeline RAG. Son image ([`frontend/Dockerfile`](frontend/Dockerfile)) ne contient que `streamlit` et `httpx` — environ 0,8 Go contre 2,8 Go pour l’image applicative, qui embarque torch et chromadb.

Hors Docker, il faut indiquer où joindre l’API :

```bash
API_BASE_URL=http://localhost:8000 streamlit run frontend/app.py
```

La page HTML servie par FastAPI sur [http://localhost:8000](http://localhost:8000) reste disponible ; les deux interfaces coexistent.

## Registry Docker local (étape 4)

Un **registry** est un dépôt d’images : on y **pousse** une image construite localement, et n’importe quelle machine ayant accès au dépôt peut la **tirer**. Le service `registry` reproduit ce cycle en local, sur `localhost:5001` (le port 5000 est occupé par AirPlay sur macOS).

```bash
./scripts/registry_cycle.sh v1
```

Le script enchaîne les quatre étapes, en les affichant :

1. **build** — construire l’image depuis le [`Dockerfile`](Dockerfile) (`analyse-de-docs-app:local`)
2. **tag** — la renommer avec l’adresse du dépôt : `localhost:5001/analyse-de-docs-app:v1`
3. **push** — l’envoyer vers le registry
4. **pull** — la récupérer (la référence locale est supprimée juste avant, pour vérifier que le pull la ramène vraiment)

Le préfixe du tag n’est pas décoratif : c’est lui qui indique à Docker **vers quel dépôt** pousser et **depuis lequel** tirer.

Inspecter le contenu du registry par son API HTTP :

```bash
curl -s http://localhost:5001/v2/_catalog
curl -s http://localhost:5001/v2/analyse-de-docs-app/tags/list
```

Faire tourner la stack depuis l’image du registry plutôt que depuis un build local :

```bash
APP_IMAGE=localhost:5001/analyse-de-docs-app:v1 docker compose up -d api worker
docker compose ps    # la colonne IMAGE montre l'image tirée du registry
```

Sans `APP_IMAGE`, Compose revient au build local (`analyse-de-docs-app:local`) : c’est le mode de travail quotidien.

Le rôle est **conceptuellement** celui d’ECR : même cycle `build → tag → push → pull`, même logique de tags versionnés. Un registry managé y ajoute l’authentification, les droits d’accès, le scan de vulnérabilités et la réplication, absents ici.

Étapes suivantes prévues pour le cas d’étude : évaluation RAGAS, comparaison de configurations.
