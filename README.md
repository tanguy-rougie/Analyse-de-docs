# Analyse-de-docs

Une entreprise veut permettre à ses ingénieurs d'interroger en langage naturel une base de documentation technique (specs, manuels, rapports). Le dépôt vise un pipeline RAG complet, évalué et déployable.

## Démarrage rapide

1. **Environnement** : `conda env create -f environment.yml` puis `conda activate analyse-de-docs`
2. **Configuration** : `copy .env.example .env` — Ollama + `llama3.2` par défaut (`ollama pull llama3.2`)
3. **PDF** : placer les fichiers dans `Documents/` (non versionné)
4. **Indexation** : `python -m src.ingestion --input-dir ./Documents --collection technical_docs --reset` → crée `chroma_db/` (non versionné)
5. **Interface** : `python -m src.web` → [http://localhost:8000](http://localhost:8000)

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

### Jobs (étape 1)

L’API **enregistre** un travail dans PostgreSQL ; elle ne l’exécute pas encore (le worker arrive à l’étape suivante). États : `PENDING` → plus tard `RUNNING` → `COMPLETED` / `FAILED`.

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

`SELECT FOR UPDATE SKIP LOCKED` n’est **pas** utilisé : un seul worker suffira. Ce verrouillage sert uniquement si plusieurs workers risquent de prendre **le même** job en même temps.

ChromaDB reste le vector store. PostgreSQL ne stocke ici que les jobs. `Documents/` est un dossier local de PDF, pas un équivalent de S3.

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
- `src/web/static/index.html` — formulaire Q&A
- `src/web/__main__.py` — serveur uvicorn

## Docker

### Prérequis

- Docker et Docker Compose.
- Fichier `.env` à la racine (copier depuis `.env.example` ; pour Docker, `OLLAMA_BASE_URL` est surchargé par Compose vers `http://ollama:11434`).

### Lancer l’interface web (app + PostgreSQL + Ollama)

```bash
docker compose up --build
```

Puis [http://localhost:8000](http://localhost:8000). Le service **ollama** démarre avec l’app ; LLM par défaut : **llama3.2**.

Première utilisation — télécharger le modèle dans le conteneur Ollama :

```bash
docker compose exec ollama ollama pull llama3.2
```

Volumes : `./chroma_db` (index Chroma, vector store actuel), `./Documents` (PDF en local), cache Hugging Face (`hf_cache`), volume `postgres_data` (table `jobs`).

### Ingestion dans le conteneur

```bash
docker compose run --rm app python -m src.ingestion --input-dir /app/Documents --collection technical_docs --reset
```

Étapes suivantes prévues pour le cas d’étude : évaluation RAGAS, comparaison de configurations.
