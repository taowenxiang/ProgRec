# ProgRec Deployment

This directory contains the first production scaffolding for the public ProgRec web platform.

For the full Linux and Vercel deployment procedure, see `PRODUCTION_RUNBOOK.md`.

## Services

- `reverse-proxy`: Caddy for `https://progrec-api.wenxiangtao.com`
- `postgres`: application metadata and runtime profiles
- `redis`: async job queue and transient state
- `progrec-api`: FastAPI service layer over the `ProgRec` runtime
- `progrec-worker`: background pipeline worker

## Quick Start

1. Copy `.env.example` to `.env` and replace secrets.
2. Run `deployment/scripts/bootstrap_linux.sh` on the Linux host.
3. Start services with `docker compose -f deployment/docker-compose.yml up --build`.
