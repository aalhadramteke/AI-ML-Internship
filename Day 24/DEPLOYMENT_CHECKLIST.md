# Deployment Checklist

Project: Async API Practice + Multi-Agent Research Assistant
Tick every item before deploying. The command after each item shows how to verify it.

## 1. Testing
- [x] Unit tests pass: `pytest tests/unit`
- [x] API tests pass: `pytest tests/api`
- [x] Coverage reviewed (target 70% or more): `pytest --cov=app --cov=research --cov-report=term-missing`
- [x] Manual smoke test on the target machine:
  - [x] `GET /health` returns `{"status": "ok"}`
  - [x] `GET /api/v2/report/1` returns 200
  - [x] `POST /api/v2/research` with a real question returns a report with citations
- [x] Benchmark re-run on the target machine and compared to `report.md`: `python benchmark.py`
- [x] Test with Ollama stopped: research returns 503 and the app stays up

## 2. Logging
- [x] `LOG_LEVEL=INFO` (not DEBUG) in production
- [x] `logs/app.log` is created and written: `Get-Content logs\app.log -Tail 20`
- [x] Log folder is writable and rotates (5 MB x 5 backups)
- [x] Every request has a `[request-id]` line and every response has `X-Request-ID`
- [x] Errors show a stack trace in the log and a generic message to the client
- [x] No API keys, tokens, or full user documents appear in the logs: `Select-String -Path logs\app.log -Pattern "API_KEY|token"`
- [x] Log folder is on a volume or disk with free space and retention policy

## 3. Environment variables
- [x] `.env.example` lists every variable the code reads
- [x] `.env` exists on the server with production values and is NOT in git: `git check-ignore .env`
- [x] `APP_ENV=production`
- [x] `API_KEY` set to a long random value (32+ characters)
- [x] `ALLOWED_ORIGINS` lists only real front-end origins (or empty if none)
- [x] `RA_BACKEND`, `RA_OLLAMA_MODEL`, `RA_OLLAMA_HOST` point to the production LLM
- [x] App starts cleanly with the production `.env` (invalid values stop start-up with a clear error)
- [x] Secrets are stored in a secret manager or the host's protected environment, not in the repo

## 4. Docker configuration
- [x] Image builds: `docker compose build`
- [x] Container starts and becomes healthy: `docker compose up -d` then `docker compose ps`
- [x] Runs as non-root: `docker compose exec api whoami` shows `appuser`
- [x] `.env`, tests, `.git`, `venv` are excluded by `.dockerignore`
- [x] Python base image version is pinned (`python:3.11-slim`) and reviewed for updates
- [x] Container can reach the LLM: research call works from inside Docker (`host.docker.internal`)
- [x] Volumes mounted for `logs/`, `output/`, `docs/` and the model cache
- [x] `restart: unless-stopped` is set
- [x] Embedding model is cached (volume) or `HF_HUB_OFFLINE=1` is set after the first download
- [x] Image size and start-up time checked: `docker images`

## 5. Documentation
- [x] README setup steps work on a clean machine
- [x] Environment variables documented in README
- [x] API docs open at `/docs` and `/openapi.json` is current: `python scripts/export_openapi.py`
- [x] Error codes (401, 422, 429, 500, 503) documented
- [x] Benchmark report (`report.md`) and this checklist are in the repo
- [x] Rollback steps written down (see section 8)

## 6. Security
- [x] `/api/v2/research` rejects requests without the key: expect 401
- [x] CORS only allows listed origins
- [x] Request bodies are validated (2-50 chars, 1-100 quantity, 5-500 char query)
- [x] 500 responses never contain stack traces or internal paths
- [x] HTTPS terminates at a reverse proxy or load balancer (the app itself speaks HTTP)
- [x] Rate limiting configured at the proxy or gateway (the app only caps concurrent research runs)
- [x] Dependencies scanned: `pip-audit -r requirements.txt`
- [x] Dependency versions reviewed and pinned for release
- [x] Docs folder contains only files that may be shown to API users
- [x] OS and Docker host patched; only port 8000 (or 443 at the proxy) exposed

## 6b. Monitoring
- [x] `/health` checked every 30-60 seconds by an uptime monitor or the Docker healthcheck
- [x] Alert on health-check failures and container restarts
- [x] Alert on spikes of 5xx responses (grep `status=5` in `logs/app.log` or use the proxy metrics)
- [x] Response time tracked from `X-Process-Time-ms` or proxy logs
- [x] Research duration tracked (`duration_s` in the response, `[LLM call ok ... s]` lines in logs)
- [x] LLM availability monitored (Ollama process and `503` counts)
- [x] Disk usage alert for `logs/` and `output/`
- [x] Someone is named as owner for alerts

## 7. Deployment steps
- [x] Code merged and tagged (for example `v2.1.0`)
- [x] `.env` placed on the server
- [x] `docker compose up -d --build`
- [x] Health check green: `curl http://localhost:8000/health`
- [x] Smoke tests from section 1 repeated against the deployed instance
- [x] Logs checked for errors for the first 15 minutes

## 8. Rollback
- [x] Previous image or tag is kept: `docker images`
- [x] Rollback command ready: `git checkout <previous-tag>; docker compose up -d --build`
- [x] `.env` backup kept
- [x] After rollback, `/health` and a research call verified

