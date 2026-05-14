#!/usr/bin/env bash
set -euo pipefail

ENV_FILE="/opt/progrec/ProgRec/deployment/.env"
CLOUDFLARED_BIN="/opt/progrec/tools/cloudflared/usr/bin/cloudflared"
TOKEN_FILE="/opt/progrec/secrets/cloudflared.token"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing env file: $ENV_FILE" >&2
  exit 1
fi

if [[ ! -x "$CLOUDFLARED_BIN" ]]; then
  echo "Missing cloudflared binary: $CLOUDFLARED_BIN" >&2
  exit 1
fi

TOKEN="$(grep '^CLOUDFLARE_TUNNEL_TOKEN=' "$ENV_FILE" | cut -d= -f2-)"

if [[ -z "$TOKEN" ]]; then
  echo "CLOUDFLARE_TUNNEL_TOKEN is empty" >&2
  exit 1
fi

mkdir -p "$(dirname "$TOKEN_FILE")"
umask 077
printf '%s' "$TOKEN" > "$TOKEN_FILE"

exec "$CLOUDFLARED_BIN" tunnel --no-autoupdate run --token-file "$TOKEN_FILE"
