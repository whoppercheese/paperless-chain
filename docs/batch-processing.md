# Batch processing by tag

For existing documents or controlled reprocessing: find documents with a queue tag and start Windmill jobs.

## Concept

1. Assign a **queue tag** to a document in Paperless (e.g. `AI-Queue` or `AI-Embed-Queue`)
2. Run a shell script or Windmill script
3. The script finds all docs with that tag (oldest first) and starts up to `limit` flow jobs
4. Docs with **skip tags** are skipped

## `queue-by-tag.sh` → `process_document`

Full processing (metadata + embedding):

```bash
./queue-by-tag.sh AI-Queue 10
```

Calls `queue_documents_by_tag`. Default skip: documents with `AI-Processed` are skipped.

**Typical workflow:**

1. Create tag `AI-Queue` in Paperless
2. Assign `AI-Queue` to existing documents
3. Run `./queue-by-tag.sh AI-Queue 10` repeatedly until all are processed
4. Successful docs receive `AI-Processed` (from the flow) and are skipped on the next run

## `queue-embeddings.sh` → `embed_document`

Embedding only, no metadata changes:

```bash
./queue-embeddings.sh AI-Embed-Queue 10
```

Calls `queue_embeddings_by_tag`. Default skip: documents with `AI-Embedded`.

**Typical workflow:**

1. Create tag `AI-Embed-Queue`
2. Tag docs that should only be (re-)embedded
3. `./queue-embeddings.sh AI-Embed-Queue 10`
4. Successful docs receive `AI-Embedded`

## Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `tag_name` | — | Queue tag in Paperless (required) |
| `limit` | `10` | Max number of jobs per invocation |
| `skip_tag_names` | see below | Docs with these tags are skipped |

| Script | Default `skip_tag_names` |
|--------|--------------------------|
| `queue_documents_by_tag` | `AI-Processed` |
| `queue_embeddings_by_tag` | `AI-Embedded` |

## Directly in Windmill

```bash
wmill script run f/paperless_chain/queue_documents_by_tag \
  --base-url "$WMILL_BASE_URL" \
  --workspace "$WMILL_WORKSPACE" \
  --token "$WMILL_TOKEN" \
  -d '{"tag_name": "AI-Queue", "limit": 10}'

wmill script run f/paperless_chain/queue_embeddings_by_tag \
  --base-url "$WMILL_BASE_URL" \
  --workspace "$WMILL_WORKSPACE" \
  --token "$WMILL_TOKEN" \
  -d '{"tag_name": "AI-Embed-Queue", "limit": 10, "skip_tag_names": ["AI-Embedded"]}'
```

## Prerequisites

- `WMILL_BASE_URL`, `WMILL_WORKSPACE`, `WMILL_TOKEN` in `.env` (shell scripts load `.env` automatically)
- Queue tag and skip tags exist in Paperless
- Windmill worker has Paperless and Windmill access (for `run_flow_async`)

Output lists `doc_id`, `job_id`, and skipped documents with reason.
