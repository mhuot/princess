## Why

Princess runs locally via `python -m princess` against `127.0.0.1:8000`. To make it sharable beyond "clone the repo", it needs a packaged runtime and a deploy path. The host already runs [nginx-director](https://github.com/mhuot/nginx-director) — a wildcard-SSL reverse proxy for hobby apps on a private box — which is the natural front door without standing up a parallel cert/proxy stack.

There is also a self-hosted GitHub Actions runner already operating on the same host (registered to a different repo). Adding a second runner scoped to `mhuot/princess` lets `push → main` flow into a `docker compose up -d --build` on the same machine the proxy is on, with no inbound SSH, no deploy keys, and no third-party CD service. The blast radius is one box.

This change wraps Princess in a container, plugs it into nginx-director, and wires push-to-main → redeploy via a self-hosted runner. None of the runtime behavior changes; the engine, AI, server, and frontend ship exactly as they are today. The specific hostname and subdomain are deployment-time choices captured in operator runbooks, not in this repository's docs or specs.

## What Changes

- **Containerize Princess** (in this repo):
  - Add `Dockerfile` — Python 3.14-slim base, install `requirements.txt` (production deps only — no pytest/pylint/black), copy `princess/` + `static/`, expose `8000`, run `python -m princess` with `HOST=0.0.0.0` as a non-root user.
  - Add `.dockerignore` — exclude `.venv`, `__pycache__`, `tests/`, `openspec/`, `.github/`, `*.md`, `.git/`, etc.
  - Add `docker-compose.yml` — single `princess` service, `container_name: princess`, attached to the external `nginx-proxy-network`, `restart: unless-stopped`, env `HOST=0.0.0.0` / `PORT=8000`.
- **Register Princess with nginx-director** (out-of-repo, operator action):
  - Use nginx-director's MCP server (`create_app`) or web UI to register the app — this writes the per-app JSON, generates the nginx server block from `templates/app.conf.template`, and creates the Route53 A record in one shot. The subdomain choice lives in operator notes, not this repo.
- **Auto-deploy via self-hosted runner** (in this repo):
  - Register a second self-hosted runner on the host, scoped to `mhuot/princess`, installed as a separate systemd service. Label: `princess`.
  - Add `.github/workflows/deploy.yml` — triggers on `push` to `main` and `workflow_dispatch`. Runs on `[self-hosted, princess]`. Steps: checkout, `docker compose up -d --build`, post-deploy smoke (`docker exec princess python ...` GET against `127.0.0.1:8000` inside the container, expect 200), `docker compose logs --tail=100` on failure. `concurrency` group serializes deploys.

## Capabilities

### New Capabilities

- `deployment`: how Princess is packaged and released. Codifies the container contract (port, env vars, network), the nginx-director registration shape (apps/*.json + nginx/conf.d/*.conf), and the CD contract (push to `main` → self-hosted-runner deploy → post-deploy smoke). Does NOT codify the hostname or domain — those are operator-time choices.

### Modified Capabilities

(none — runtime behavior is unchanged; `room-server` still serves on port 8000 with the same routes.)

## Impact

- **Affected code:** none of the runtime Python. New top-level files only: `Dockerfile`, `.dockerignore`, `docker-compose.yml`, `.github/workflows/deploy.yml`.
- **Affected APIs:** none. Same HTTP + WebSocket surface.
- **Affected dependencies:** none new — production image installs the existing `requirements.txt`.
- **Affected systems:**
  - **Deployment host**: a new `princess` Docker container on `nginx-proxy-network`; a new `actions.runner.mhuot-princess.*.service` systemd unit; a new runner workdir under the repo (gitignored).
  - **nginx-director instance**: one new app registration entry + nginx server block + one `nginx -s reload` (performed by the MCP `create_app` call, atomic with DNS).
  - **DNS provider**: one new A record (created by `create_app`).
  - **GitHub (`mhuot/princess`)**: one new runner registration; one new workflow in the Actions tab.
- **Docs touched:** none in this change. README/CHANGELOG/CONTRIBUTING stay silent on the deployment URL for now. Doc updates can land in a follow-up change once the operator decides what (if anything) to publicize.
- **Reversible:** `docker compose down` stops the container; nginx-director's `delete_app` removes the registration + DNS + reloads nginx; `sudo systemctl stop && systemctl disable` + `./config.sh remove` removes the runner.
- **Naming policy:** every internal surface — container name, compose service, nginx upstream, workflow name, runner label — uses "Princess" / "princess" only. Never the inspiring game's vulgar name.
- **Out of scope:**
  - Documenting the live URL anywhere in the repo (deferred).
  - Multi-instance scaling, blue/green deploys, downtime-free rollouts (container restart is ~2s; acceptable for a hobby game).
  - Persistent state (rooms remain in-memory; deploy = all rooms drop).
  - Monitoring/alerting beyond `docker compose logs`.
  - Rate limiting, WAF, abuse protections.
  - Secrets management (no secrets needed — no DB, no third-party APIs).
