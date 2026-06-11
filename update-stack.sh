#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

echo "=== pAIperless: Stack aktualisieren ==="
echo "Verzeichnis: $ROOT"
echo

echo "→ git pull"
git pull --ff-only
echo

echo "→ docker compose down"
docker compose down
echo

echo "→ docker compose up -d --build"
docker compose up -d --build
echo

echo "=== Fertig ==="
docker compose ps
