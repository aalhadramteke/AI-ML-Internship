# Deployment Checklist

Project: Async API Practice + Multi-Agent Research Assistant
Tick every item before deploying. The command after each item shows how to verify it.

## 1. Testing
- [ ] Unit tests pass: `pytest tests/unit`
- [ ] API tests pass: `pytest tests/api`
- [ ] Coverage reviewed (target 70% or more): `pytest --cov=app --cov=research --cov-report=term-missing`
- [ ] Manual smoke test on the target machine:
  - [ ] `GET /health` returns `{"status": "ok"}`
  - [ ] `GET /api/v2/report/1` returns 200
  - [ ] `POST /api/v2/research` with a real question returns a report with citations
- [ ] Benchmark re-run on the target machine and compared to `report.md`: `python benchmark.py`
- [ ] Test with Ollama stopped: research returns 503 and the app stays up

## 2. Logging
- [ ] `LOG_LEVEL=INFO` (not DEBUG) in production
- [ ] `logs/app.log` is created and written: `Get-Content logs\app.log -Tail 20`
- [ ] Log folder is writable and rotates (5 MB x 5 backups)
- [ ] Every request has a `[request-id]` line and every response has `X-Request-ID`
- [ ] Errors show a stack trace in the log and a generic message to the client
- [ ] No API keys, tokens, or full user documents appear in the logs: `Select-String -Path logs\app.log -Pattern "API_KEY|token"`
- [ ] Log folder is on a volume or disk with free space and retention policy

## 3. Environment variables
- [ ] `.env.example` lists every variable the code reads
- [ ] `.env` exists on the server with production values and is NOT in git: `git check-ignore .env`
- [ ] `APP_ENV=production`
- [ ] `API_KEY` set to a long random value (32+ characters)
- [ ] `ALLOWED_ORIGINS` lists only real front-end origins (or empty if none)
- [ ] `RA_BACKEND`, `RA_OLLAMA_MODEL`, `RA_OLLAMA_HOST` point to the production LLM
- [ ] App starts cleanly with the production `.env` (invalid values stop start-up with a clear error)
- [ ] Secrets are stored in a secret manager or the host's protected environment, not in the repo

## 4. Docker configuration
- [ ] Image builds: `docker compose build`
- [ ] Container starts and becomes healthy: `docker compose up -d` then `docker compose ps`
- [ ] Runs as non-root: `docker compose exec api whoami` shows `appuser`
- [ ] `.env`, tests, `.git`, `venv` are excluded by `.dockerignore`
- [ ] Python base image version is pinned (`python:3.11-slim`) and reviewed for updates
- [ ] Container can reach the LLM: research call works from inside Docker (`host.docker.internal`)
- [ ] Volumes mounted for `logs/`, `output/`, `docs/` and the model cache
- [ ] `restart: unless-stopped` is set
- [ ] Embedding model is cached (volume) or `HF_HUB_OFFLINE=1` is set after the first download
- [ ] Image size and start-up time checked: `docker images`

## 5. Documentation
- [ ] README setup steps work on a clean machine
- [ ] Environment variables documented in README
- [ ] API docs open at `/docs` and `/openapi.json` is current: `python scripts/export_openapi.py`
- [ ] Error codes (401, 422, 429, 500, 503) documented
- [ ] Benchmark report (`report.md`) and this checklist are in the repo
- [ ] Rollback steps written down (see section 8)

## 6. Security
- [ ] `/api/v2/research` rejects requests without the key: expect 401
- [ ] CORS only allows listed origins
- [ ] Request bodies are validated (2-50 chars, 1-100 quantity, 5-500 char query)
- [ ] 500 responses never contain stack traces or internal paths
- [ ] HTTPS terminates at a reverse proxy or load balancer (the app itself speaks HTTP)
- [ ] Rate limiting configured at the proxy or gateway (the app only caps concurrent research runs)
- [ ] Dependencies scanned: `pip-audit -r requirements.txt`
- [ ] Dependency versions reviewed and pinned for release
- [ ] Docs folder contains only files that may be shown to API users
- [ ] OS and Docker host patched; only port 8000 (or 443 at the proxy) exposed

## 6b. Monitoring
- [ ] `/health` checked every 30-60 seconds by an uptime monitor or the Docker healthcheck
- [ ] Alert on health-check failures and container restarts
- [ ] Alert on spikes of 5xx responses (grep `status=5` in `logs/app.log` or use the proxy metrics)
- [ ] Response time tracked from `X-Process-Time-ms` or proxy logs
- [ ] Research duration tracked (`duration_s` in the response, `[LLM call ok ... s]` lines in logs)
- [ ] LLM availability monitored (Ollama process and `503` counts)
- [ ] Disk usage alert for `logs/` and `output/`
- [ ] Someone is named as owner for alerts

## 7. Deployment steps
- [ ] Code merged and tagged (for example `v2.1.0`)
- [ ] `.env` placed on the server
- [ ] `docker compose up -d --build`
- [ ] Health check green: `curl http://localhost:8000/health`
- [ ] Smoke tests from section 1 repeated against the deployed instance
- [ ] Logs checked for errors for the first 15 minutes

## 8. Rollback
- [ ] Previous image or tag is kept: `docker images`
- [ ] Rollback command ready: `git checkout <previous-tag>; docker compose up -d --build`
- [ ] `.env` backup kept
- [ ] After rollback, `/health` and a research call verified

