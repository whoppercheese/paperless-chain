# Search UI

Semantic search across document chunks stored in Qdrant.

**URL:** `http://localhost:8888` (port via `SEARCH_PORT` in `.env`)

## How it works

1. The search query is converted to an embedding vector via Ollama/bge-m3
2. Qdrant returns the most similar chunks
3. Results are grouped by document
4. Links go directly to the Paperless document

## Filters

- Correspondent
- Tag
- Chunk type: summary or partial chunks

Filter values are read from the Qdrant collection (scroll over payload fields).

## Prerequisites

- At least one document processed via `process_document` or `embed_document`
- Search container running (`docker compose up -d`)
- `OLLAMA_URL` and `PAPERLESS_URL` in `.env` for embedding and document links

## Tech stack

- FastAPI + HTMX
- Source code: `search/`
- Docker image built via `docker-compose.yml`
