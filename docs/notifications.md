# Notifications

Controlled via `NOTIFY_MODE` in `.env`:

| Mode | Description |
|------|-------------|
| `log` | Windmill logs only (default) |
| `matrix` | Directly to Matrix room (without Hermes) |
| `hermes` | HTTP POST to Hermes webhook → Matrix/Telegram/etc. |

After `.env` changes:

```bash
docker compose up -d windmill-worker
```

## When are notifications sent?

| Event | Script | Content |
|-------|--------|---------|
| Success with warnings | `notify` | Title, metadata, warning list |
| Flow error | `handle_flow_failure` | Step, error message, doc_id |

## Hermes webhook (`NOTIFY_MODE=hermes`)

Prerequisites:
- Hermes Gateway with webhook adapter (`WEBHOOK_ENABLED=true`, port default `8644`)
- Matrix (or other target) configured in Hermes

**1. Create route:**

```bash
hermes webhook subscribe paperless-chain \
  --deliver matrix \
  --deliver-only \
  --prompt "{message}" \
  --description "Paperless-chAIn document notifications"
```

**2. In `.env`:**

```bash
NOTIFY_MODE=hermes
HERMES_WEBHOOK_URL=http://192.168.178.158:8644/webhooks/paperless-chain
HERMES_WEBHOOK_SECRET=<secret-from-subscribe-command>
```

**3. Test:**

```bash
hermes webhook test paperless-chain --payload '{"message":"Test from Paperless-chAIn","doc_id":1,"event":"paperless_chain.document_processed"}'
```

## Alternative without Hermes

- `NOTIFY_MODE=matrix` — direct Matrix API (`MATRIX_HOMESERVER`, `MATRIX_ACCESS_TOKEN`, `MATRIX_ROOM_ID`)
- `NOTIFY_MODE=log` — no external service required
