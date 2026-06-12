# Development

## Deploy scripts

```bash
./wmill-sync.sh
./wmill-sync.sh --dry-run    # preview
```

## Test individual scripts

```bash
wmill script run f/paperless_chain/fetch_document \
  --base-url "$WMILL_BASE_URL" \
  --workspace "$WMILL_WORKSPACE" \
  --token "$WMILL_TOKEN" \
  -d '{"doc_id": 1}'
```

## Test flows

```bash
# Full processing
wmill flow run f/paperless_chain/process_document \
  --base-url "$WMILL_BASE_URL" \
  --workspace "$WMILL_WORKSPACE" \
  --token "$WMILL_TOKEN" \
  -d '{"doc_id": 1}'

# Embedding only
wmill flow run f/paperless_chain/embed_document \
  --base-url "$WMILL_BASE_URL" \
  --workspace "$WMILL_WORKSPACE" \
  --token "$WMILL_TOKEN" \
  -d '{"doc_id": 1}'
```

## Logs

```bash
docker compose logs -f windmill-worker
```

LLM requests and Paperless PATCHs appear as:

- `=== Paperless-chAIn LLM Request ===`
- `=== Paperless-chAIn Paperless PATCH ===`

## Update the stack

```bash
./update-stack.sh
```

Runs: `git pull` → `wmill sync push` → `docker compose down` → `docker compose up -d --build`

## Windmill CLI profile (optional)

Register once, then `wmill sync push --yes` is enough:

```bash
wmill workspace add paperless_chain main http://localhost:8000
wmill sync push --yes
```

Update CLI: `wmill upgrade`
