# Project structure

```
paperless-chain/
├── f/paperless_chain/
│   ├── process_document.flow/     # Main flow (webhook)
│   ├── embed_document.flow/       # Embedding only
│   ├── preprocess_webhook.py      # doc_url → doc_id
│   ├── fetch_document.py
│   ├── summarize_document.py
│   ├── derive_title.py
│   ├── resolve_document_type.py
│   ├── resolve_correspondent.py
│   ├── update_paperless.py
│   ├── chunk_document.py
│   ├── generate_embeddings.py
│   ├── store_qdrant.py
│   ├── apply_status_tags.py       # AI-Warning
│   ├── apply_embedded_tag.py      # AI-Embedded
│   ├── handle_flow_failure.py     # AI-Error
│   ├── notify.py
│   ├── queue_documents_by_tag.py  # Batch → process_document
│   ├── queue_embeddings_by_tag.py # Batch → embed_document
│   └── shared/
│       ├── ollama_client.py
│       ├── paperless_client.py
│       ├── windmill_client.py
│       ├── notify_client.py
│       ├── prompts.py
│       └── text_utils.py
├── search/                        # Search UI (FastAPI + HTMX)
├── docker-compose.yml
├── wmill.yaml / wmill-lock.yaml
├── wmill-sync.sh
├── update-stack.sh
├── queue-by-tag.sh
└── queue-embeddings.sh
```

## System tags

| Tag | Set by | Meaning |
|-----|--------|---------|
| `AI-Processed` | `update_paperless` | Full processing completed |
| `AI-Warning` | `apply_status_tags` | Warnings during processing |
| `AI-Error` | `handle_flow_failure` | Flow aborted |
| `AI-Embedded` | `apply_embedded_tag` | Embedding flow completed |

System tags are ignored by the LLM when selecting tags (`text_utils.SYSTEM_TAG_NAMES`).

## Qdrant chunk structure

Partial chunk:

```json
{
  "vector": [0.1, 0.2, "..."],
  "payload": {
    "doc_id": 123,
    "chunk_kind": "chunk",
    "label": "Invoice line items",
    "correspondent": "Telekom",
    "tags": ["invoice"],
    "text": "...",
    "document_type": "Invoice"
  }
}
```

Additionally, one chunk per document with `"chunk_kind": "summary"`.

Collection name: `QDRANT_COLLECTION` in `.env` (default: `paperless-chain-documents` in `.env.example`, `paperless_chain_documents` in `docker-compose.yml` — align the values).

## Docker stack

| Service | Role |
|---------|------|
| `qdrant` | Vector DB |
| `windmill-db` | PostgreSQL for Windmill |
| `windmill-server` | Windmill API + UI |
| `windmill-worker` | Flow execution (Ollama, Paperless, Qdrant) |
| `search` | Search UI |

Worker environment variables are passed through to Python scripts via `WHITELIST_ENVS`.
