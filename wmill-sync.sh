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

missing=()
[[ -z "$WMILL_BASE_URL" ]] && missing+=("WMILL_BASE_URL oder WINDMILL_BASE_URL")
[[ -z "$WMILL_WORKSPACE" ]] && missing+=("WMILL_WORKSPACE")
[[ -z "$WMILL_TOKEN" ]] && missing+=("WMILL_TOKEN")

if ((${#missing[@]})); then
  echo "Fehlende .env-Variablen: ${missing[*]}" >&2
  exit 1
fi

echo "=== Paperless-chAIn: wmill sync push ==="
echo "base-url:  $WMILL_BASE_URL"
echo "workspace: $WMILL_WORKSPACE"
echo

exec wmill sync push \
  --base-url "$WMILL_BASE_URL" \
  --workspace "$WMILL_WORKSPACE" \
  --token "$WMILL_TOKEN" \
  --yes \
  "$@"
