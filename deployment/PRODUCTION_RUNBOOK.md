# ProgRec Production Runbook

This runbook deploys the public web platform with:

- Frontend: Vercel project for `progrec-web`
- Frontend public path: `https://demo.wenxiangtao.com/progrec`
- Backend API: `https://progrec-api.wenxiangtao.com`
- Linux host: Docker Compose running FastAPI, worker, PostgreSQL, Redis, and Cloudflare Tunnel

## Current Readiness

The repository now provides:

- FastAPI system, runtime profile, agent session, and pipeline routes
- Runtime profile probing against OpenAI-compatible `/models`
- Session and message persistence in PostgreSQL
- Pipeline job persistence, result persistence, and retry replacement jobs
- Redis-backed queue enqueue/dequeue and worker consumption
- In-process pipeline execution with CLI fallback
- Docker Compose, Cloudflare Tunnel, optional Caddy, Postgres, Redis, API, and worker containers

## Linux Host Prerequisites

Install:

- Docker Engine
- Docker Compose plugin
- Git
- A shell user with access to `/opt/progrec`

Do not expose:

- PostgreSQL
- Redis
- FastAPI container port directly

Recommended for a home server:

- Do not open inbound `80/tcp` or `443/tcp` on the router
- Use Cloudflare Tunnel as the public entrypoint

## DNS

Create DNS records:

- `progrec-api.wenxiangtao.com` -> Cloudflare Tunnel public hostname
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
PROGREC_REPO_ROOT=/srv/app
ENCRYPTION_KEY=<32-or-more-random-characters>
CORS_ALLOWED_ORIGINS=https://demo.wenxiangtao.com
CLOUDFLARE_TUNNEL_TOKEN=<token-from-cloudflare-dashboard>
```

Cloudflare setup:

1. In the Cloudflare dashboard, create a Tunnel.
2. Create a public hostname:

   ```text
   Dockerized cloudflared: progrec-api.wenxiangtao.com -> http://progrec-api:8000
   Host-installed cloudflared: progrec-api.wenxiangtao.com -> http://127.0.0.1:8000
   ```

3. Copy the tunnel token into `deployment/.env`.
4. If you run `cloudflared` as a user-level systemd service on the Linux host, enable linger once so the service also starts after host reboot before interactive login:

   ```bash
   loginctl enable-linger mount
   ```

Start:

```bash
docker compose --env-file deployment/.env -f deployment/docker-compose.yml --profile cloudflare-tunnel up -d --build
```

Check:

```bash
docker compose --env-file deployment/.env -f deployment/docker-compose.yml ps
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/models/recommended
curl https://progrec-api.wenxiangtao.com/health
curl http://127.0.0.1:8000/pipeline/jobs/<job_id>
curl http://127.0.0.1:8000/pipeline/jobs/<job_id>/result
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
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/models/recommended
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
6. Post a message to `POST /agent/sessions/{id}/messages` and confirm SSE events arrive
7. Submit a pipeline job
8. Confirm `GET /pipeline/jobs/{id}` and `GET /pipeline/jobs/{id}/result` update

## Updates

Pull and redeploy backend:

```bash
cd /opt/progrec/ProgRec
git pull
docker compose --env-file deployment/.env -f deployment/docker-compose.yml --profile cloudflare-tunnel up -d --build
```

View logs:

```bash
docker compose --env-file deployment/.env -f deployment/docker-compose.yml logs -f progrec-api
docker compose --env-file deployment/.env -f deployment/docker-compose.yml logs -f progrec-worker
docker compose --env-file deployment/.env -f deployment/docker-compose.yml logs -f cloudflared
```

Stop:

```bash
docker compose --env-file deployment/.env -f deployment/docker-compose.yml down
```

## Optional Direct Exposure

If you later move this stack to a VPS or a network where inbound `80/443` is intentionally reachable, you can still use the previous Caddy-based edge:

```bash
docker compose --env-file deployment/.env -f deployment/docker-compose.yml --profile direct-exposure up -d --build
```

That mode expects:

- `progrec-api.wenxiangtao.com` resolves to the host public IP
- inbound `80/tcp` and `443/tcp` reach the Linux host
- Let's Encrypt can reach the host for ACME validation
