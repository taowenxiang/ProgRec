# ProgRec Deployment

This directory contains the first production scaffolding for the public ProgRec web platform.

For the full Linux and Vercel deployment procedure, see `PRODUCTION_RUNBOOK.md`.

## Services

- `cloudflared`: preferred public entrypoint for a home server via Cloudflare Tunnel
- `reverse-proxy`: optional Caddy edge for direct public `80/443` exposure
- `postgres`: application metadata and runtime profiles
- `redis`: async job queue and transient state
- `progrec-api`: FastAPI service layer over the `ProgRec` runtime
- `progrec-worker`: background pipeline worker

## Quick Start

1. Copy `.env.example` to `.env` and replace secrets.
2. Run `deployment/scripts/bootstrap_linux.sh` on the Linux host.
3. On a home server, start the stack with Cloudflare Tunnel:

   ```bash
   docker compose --env-file deployment/.env -f deployment/docker-compose.yml --profile cloudflare-tunnel up -d --build
   ```

4. Only if you intentionally want to expose `80/443` from the host, use:

   ```bash
   docker compose --env-file deployment/.env -f deployment/docker-compose.yml --profile direct-exposure up -d --build
   ```
