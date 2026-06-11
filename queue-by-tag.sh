#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

WMILL_BASE_URL="${WMILL_BASE_URL:-${WINDMILL_BASE_URL:-}}"
WMILL_WORKSPACE="${WMILL_WORKSPACE:-}"
WMILL_TOKEN="${WMILL_TOKEN:-}"

TAG_NAME="${1:-}"
LIMIT="${2:-10}"

if [[ -z "$TAG_NAME" ]]; then
  echo "Usage: $0 <tag_name> [limit]" >&2
  echo "Example: $0 AI-Queue 10" >&2
  exit 1
fi

missing=()
[[ -z "$WMILL_BASE_URL" ]] && missing+=("WMILL_BASE_URL oder WINDMILL_BASE_URL")
[[ -z "$WMILL_WORKSPACE" ]] && missing+=("WMILL_WORKSPACE")
[[ -z "$WMILL_TOKEN" ]] && missing+=("WMILL_TOKEN")

if ((${#missing[@]})); then
  echo "Fehlende .env-Variablen: ${missing[*]}" >&2
  exit 1
fi

PAYLOAD="$(python3 -c 'import json, sys; print(json.dumps({"tag_name": sys.argv[1], "limit": int(sys.argv[2])}))' "$TAG_NAME" "$LIMIT")"

echo "=== Paperless-chAIn: queue by tag ==="
echo "tag:   $TAG_NAME"
echo "limit: $LIMIT"
echo

exec wmill script run f/paperless_chain/queue_documents_by_tag \
  --base-url "$WMILL_BASE_URL" \
  --workspace "$WMILL_WORKSPACE" \
  --token "$WMILL_TOKEN" \
  -d "$PAYLOAD"
