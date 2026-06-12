# Paperless-chAIn

AI extension for [Paperless-ngx](https://github.com/paperless-ngx/paperless-ngx): automatic metadata, semantic chunking, and vector search — orchestrated with [Windmill](https://www.windmill.dev/).

## What it does

- **New documents** (webhook): summary, title, tags, correspondent, document type → Paperless update → embeddings in Qdrant
- **Embeddings only** (`embed_document`): keep existing metadata, chunking + Qdrant only
- **Batch processing**: queue documents by tag (`queue-by-tag.sh`, `queue-embeddings.sh`)
- **Search UI**: semantic search across all chunks (FastAPI + HTMX)

## Quick Start

```bash
cp .env.example .env          # set PAPERLESS_*, OLLAMA_*, WMILL_*
docker compose up -d          # Qdrant, Windmill, Search UI
./wmill-sync.sh               # deploy scripts & flows
```

Paperless workflow: **Document Added → Webhook** to `process_document`.  
Details: [Setup](docs/setup.md) · [Paperless webhook](docs/setup.md#paperless-workflow)

| Service | URL |
|--------|-----|
| Windmill | `http://localhost:8000` |
| Search UI | `http://localhost:8888` |
| Qdrant | `http://localhost:6333` |

**Create Paperless tags:** `AI-Processed`, `AI-Warning`, `AI-Error`, `AI-Embedded`

## Documentation

| Topic | File |
|-------|------|
| Installation & configuration | [docs/setup.md](docs/setup.md) |
| Flows & steps | [docs/flows.md](docs/flows.md) |
| Batch queue by tag | [docs/batch-processing.md](docs/batch-processing.md) |
| Search UI | [docs/search.md](docs/search.md) |
| Notifications | [docs/notifications.md](docs/notifications.md) |
| Development & testing | [docs/development.md](docs/development.md) |
| Project structure & Qdrant | [docs/project-structure.md](docs/project-structure.md) |

## Helper scripts

| Script | Purpose |
|--------|---------|
| `./wmill-sync.sh` | Push Windmill scripts/flows |
| `./update-stack.sh` | git pull + sync + Docker rebuild |
| `./queue-by-tag.sh <tag> [limit]` | `process_document` for tagged docs |
| `./queue-embeddings.sh <tag> [limit]` | `embed_document` for tagged docs |
