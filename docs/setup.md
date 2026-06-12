# Setup

## Prerequisites

- Docker & Docker Compose
- **Node.js ≥ 20** and **npm** (Windmill CLI)
- Paperless-ngx (already running)
- Ollama with LLM (e.g. `qwen3`) and `bge-m3`
- Optional: Hermes Agent or Matrix for notifications

## Phases

| Phase | What |
|-------|------|
| Preparation | `.env`, Paperless API token, Ollama models, status tags in Paperless |
| Stack | `docker compose up -d` |
| Windmill | Workspace, API token, `./wmill-sync.sh` |
| Paperless | Workflow with webhook to `process_document` |
| Test | Run flow manually or via test webhook |

## 1. `.env` and external services

```bash
cp .env.example .env
```

Minimum required settings:

| Variable | Description |
|----------|-------------|
| `PAPERLESS_URL` | Reachable **from the Windmill worker** (e.g. `http://host.docker.internal:8010`) |
| `PAPERLESS_API_TOKEN` | Paperless → **Settings → API Tokens** |
| `OLLAMA_URL` | Reachable **from the Windmill worker** (e.g. `http://host.docker.internal:11434`) |
| `OLLAMA_LLM_MODEL` | e.g. `qwen3` |
| `OLLAMA_EMBED_MODEL` | e.g. `bge-m3` |

**System tags in Paperless** (exact names):

| Tag | When set |
|-----|----------|
| `AI-Processed` | Successful `process_document` run |
| `AI-Warning` | Processing with warnings |
| `AI-Error` | Flow error |
| `AI-Embedded` | Successful `embed_document` run |

**Ollama models:**

```bash
ollama pull qwen3
ollama pull bge-m3
```

## 2. Start the stack

```bash
docker compose up -d
```

| Service | Default URL |
|--------|-------------|
| Windmill UI | `http://localhost:8000` (`WINDMILL_PORT`) |
| Search UI | `http://localhost:8888` (`SEARCH_PORT`) |
| Qdrant | `http://localhost:6333` (`QDRANT_PORT`) |

Update the stack:

```bash
./update-stack.sh
```

After `.env` changes, reload the worker:

```bash
docker compose up -d windmill-worker
```

## 3. Set up Windmill

`docker compose up` only starts containers — scripts and flows must be pushed via the CLI.

### 3.1 First login

1. Open Windmill UI: `http://localhost:8000`
2. Create an admin user
3. Choose a workspace (e.g. `main` or `paperless-chain`) — the ID is part of the webhook URL

### 3.2 API token

1. **User menu → Account Settings**
2. **Tokens → Add token**
3. Save the token in `.env` as `WMILL_TOKEN`

### 3.3 CLI & deploy

```bash
npm install -g windmill-cli
```

In `.env`:

```bash
WMILL_BASE_URL=http://localhost:8000
WMILL_WORKSPACE=main
WMILL_TOKEN=wm_xxxxxxxx
```

Deploy:

```bash
./wmill-sync.sh
```

Dry run: `./wmill-sync.sh --dry-run`

**Verify:** **Flows** → `process_document` and `embed_document`; under **Scripts**, the individual steps.

### 3.4 Test flow (without Paperless)

```bash
wmill flow run f/paperless_chain/process_document \
  --base-url "$WMILL_BASE_URL" \
  --workspace "$WMILL_WORKSPACE" \
  --token "$WMILL_TOKEN" \
  -d '{"doc_id": 1}'
```

Logs:

```bash
docker compose logs -f windmill-worker
```

## Paperless workflow

**Settings → Workflows** → new workflow:

| Field | Value |
|-------|-------|
| Name | Paperless-chAIn Auto-Process |
| Trigger | **Document Added** |
| Action | **Webhook** |
| Method | POST |
| Content-Type | `application/json` |
| Body | `{"doc_url": "{{ doc_url }}"}` |

**Webhook URL:**

```
http://<windmill-host>:<WINDMILL_PORT>/api/w/<workspace>/jobs/run/f/f/paperless_chain/process_document?token=<API-TOKEN>
```

Example locally, workspace `main`:

```
http://localhost:8000/api/w/main/jobs/run/f/f/paperless_chain/process_document?token=wm_xxxxxxxx
```

**Network:** Paperless must be able to reach Windmill at this URL. `localhost` does not work when Paperless and Windmill run in different containers/hosts — use the host IP or `host.docker.internal` instead.

**Test webhook:**

```bash
curl -X POST \
  'http://localhost:8000/api/w/main/jobs/run/f/f/paperless_chain/process_document?token=YOUR_TOKEN' \
  -H 'Content-Type: application/json' \
  -d '{"doc_url": "http://paperless/documents/42/"}'
```

The `doc_url` does not need to be reachable — only the ID in the path matters.

## Checklist

- [ ] Node.js ≥ 20 + `windmill-cli` (`wmill --version`)
- [ ] `.env` with `WMILL_*`, `PAPERLESS_*`, `OLLAMA_*`
- [ ] Ollama models pulled
- [ ] Tags `AI-Processed`, `AI-Warning`, `AI-Error`, `AI-Embedded` in Paperless
- [ ] Windmill admin + workspace, `WMILL_TOKEN` set
- [ ] `./wmill-sync.sh` successful
- [ ] Flow test with `wmill flow run` or curl OK
- [ ] Paperless workflow **Document Added → Webhook** active
- [ ] Search UI reachable at `:8888`
- [ ] Optional: notifications — [notifications.md](notifications.md)
