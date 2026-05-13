# ProgRec Production Runbook

This runbook deploys the public web platform with:

- Frontend: Vercel project for `progrec-web`
- Frontend public path: `https://demo.wenxiangtao.com/progrec`
- Backend API: `https://progrec-api.wenxiangtao.com`
- Linux host: Docker Compose running Caddy, FastAPI, worker, PostgreSQL, and Redis

## Current Readiness

The repository currently provides the deployable foundation:

- FastAPI service skeleton
- Runtime profile test endpoint
- Agent session endpoint
- Pipeline job endpoint
- Docker Compose, Caddy, Postgres, Redis, API, and worker containers
- Vercel BFF routes in `progrec-web`

Before claiming the product is fully usable, the next backend implementation milestone must wire:

- `POST /agent/sessions/{id}/messages` to `ProgRec` V2
- `GET /pipeline/jobs/{id}` and `GET /pipeline/jobs/{id}/result`
- Redis queue consumption in `progrec-worker`
- Persistent PostgreSQL storage for sessions, messages, jobs, and results
- Real pipeline execution through `progrec_agent/run_agent.py` or `ProgRecOrchestrator`

## Linux Host Prerequisites

Install:

- Docker Engine
- Docker Compose plugin
- Git
- A shell user with access to `/opt/progrec`

Open inbound ports:

- `80/tcp`
- `443/tcp`

Do not expose:

- PostgreSQL
- Redis
- FastAPI container port directly

## DNS

Create DNS records:

- `progrec-api.wenxiangtao.com` -> Linux host public IP
- `demo.wenxiangtao.com` -> existing demo router

The demo router should forward `/progrec/*` to the Vercel deployment.

## Backend Deployment

On the Linux host:

```bash
sudo mkdir -p /opt/progrec
sudo chown -R "$USER":"$USER" /opt/progrec
cd /opt/progrec
git clone <PROGREC_REPO_URL> ProgRec
cd ProgRec
./deployment/scripts/bootstrap_linux.sh
cp deployment/.env.example deployment/.env
```

Edit `deployment/.env`:

```bash
POSTGRES_PASSWORD=<strong-password>
DATABASE_URL=postgresql://progrec:<strong-password>@postgres:5432/progrec
ENCRYPTION_KEY=<32-or-more-random-characters>
CORS_ALLOWED_ORIGINS=https://demo.wenxiangtao.com
```

Start:

```bash
docker compose --env-file deployment/.env -f deployment/docker-compose.yml up -d --build
```

Check:

```bash
docker compose --env-file deployment/.env -f deployment/docker-compose.yml ps
curl https://progrec-api.wenxiangtao.com/health
curl https://progrec-api.wenxiangtao.com/models/recommended
```

Expected health response:

```json
{"status":"ok","service":"progrec-api","version":"1.0.0"}
```

## Frontend Deployment

Create a GitHub repository for `progrec-web`, push `/Users/mount/Desktop/Programming/progrec-web`, and import it into Vercel.

Set Vercel environment variables:

```bash
NEXT_PUBLIC_APP_BASE_PATH=/progrec
NEXT_PUBLIC_APP_URL=https://demo.wenxiangtao.com/progrec
PROGREC_API_BASE_URL=https://progrec-api.wenxiangtao.com
```

Build command:

```bash
pnpm build
```

The Vercel deployment itself may have a Vercel URL. Your public user-facing route remains:

```text
https://demo.wenxiangtao.com/progrec
```

## Demo Router

Configure the router for:

```text
/progrec/* -> Vercel progrec-web deployment
```

It must preserve:

- HTTP methods
- headers
- request bodies
- streaming/SSE responses
- static asset requests under the `/progrec` base path

## Verification Checklist

Backend:

```bash
curl https://progrec-api.wenxiangtao.com/health
curl https://progrec-api.wenxiangtao.com/models/recommended
curl -X POST https://progrec-api.wenxiangtao.com/runtime-profiles/test \
  -H 'content-type: application/json' \
  -d '{"base_url":"https://api.openai.com/v1","model":"gpt-4.1-mini","api_key":"sk-test"}'
```

Frontend:

```bash
curl -I https://demo.wenxiangtao.com/progrec
curl -I https://demo.wenxiangtao.com/progrec/setup
curl -I https://demo.wenxiangtao.com/progrec/chat
```

End-to-end:

1. Open `https://demo.wenxiangtao.com/progrec/setup`
2. Enter API key, base URL, and model
3. Test connection
4. Open chat
5. Create an agent session
6. Submit a pipeline job
7. Confirm job status and result pages update

## Updates

Pull and redeploy backend:

```bash
cd /opt/progrec/ProgRec
git pull
docker compose --env-file deployment/.env -f deployment/docker-compose.yml up -d --build
```

View logs:

```bash
docker compose --env-file deployment/.env -f deployment/docker-compose.yml logs -f progrec-api
docker compose --env-file deployment/.env -f deployment/docker-compose.yml logs -f progrec-worker
docker compose --env-file deployment/.env -f deployment/docker-compose.yml logs -f reverse-proxy
```

Stop:

```bash
docker compose --env-file deployment/.env -f deployment/docker-compose.yml down
```
