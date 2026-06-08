## 1. Pre-conditions

- [x] 1.1 Confirm `docker` and `docker compose` work for the deploying user. Confirm membership in the `docker` group.
- [x] 1.2 Confirm `nginx-proxy-network` exists: `docker network inspect nginx-proxy-network >/dev/null`.
- [x] 1.3 Confirm nginx-director's wildcard cert covers the chosen deployment subdomain (operator runbook holds the specific value).
- [x] 1.4 Confirm port 8000 is free on `nginx-proxy-network` — `docker ps --filter network=nginx-proxy-network --format '{{.Names}} {{.Ports}}' | grep ':8000'` should be empty.
- [x] 1.5 Confirm `gh auth status` shows `mhuot` and can hit `mhuot/princess`.

## 2. Containerize Princess

- [x] 2.1 Write `Dockerfile` — `FROM python:3.14-slim`, set `WORKDIR /app`, `COPY requirements.txt .`, `RUN pip install --no-cache-dir -r requirements.txt`, `COPY princess/ princess/`, `COPY static/ static/`, `EXPOSE 8000`, `ENV HOST=0.0.0.0 PORT=8000`, `CMD ["python", "-m", "princess"]`. Add a non-root `USER` (`useradd princess && USER princess`) for hardening.
- [x] 2.2 Write `.dockerignore` excluding `.git`, `.github`, `.venv`, `__pycache__`, `*.pyc`, `tests`, `openspec`, `smoke`, `scripts`, `*.md`, `CHANGELOG.md`, `CONTRIBUTING.md`, `NOTICE`, `LICENSE`, `pyproject.toml`, `requirements-dev.txt`, `Dockerfile`, `.dockerignore`, `docker-compose.yml`, `actions-runner`.
- [x] 2.3 Write `docker-compose.yml` — service `princess`, `build: .`, `container_name: princess`, `restart: unless-stopped`, `networks: [nginx-proxy-network]`, env `HOST=0.0.0.0`, `PORT=8000`. Top-level `networks: nginx-proxy-network: { external: true }`.
- [x] 2.4 Local build smoke: `docker compose build`. Verify the resulting image runs as a non-root UID and does NOT contain pytest/pylint/black.
- [x] 2.5 Commit: `deploy-via-nginx-director: Add Dockerfile and compose for Princess container`

## 3. Register with nginx-director (operator runbook)

These steps are out-of-repo. Performed once via the nginx-director MCP server's `create_app` tool or the web UI, atomically: writes the per-app JSON, generates the nginx server block from `templates/app.conf.template`, creates the Route53 A record, and reloads nginx. The chosen subdomain and any other specifics live in private operator notes, not in this change.

- [x] 3.1 Call `create_app(name='princess', subdomain=<operator choice>, container_name='princess', port=8000)` via the MCP server (or perform the equivalent in the web UI).
- [x] 3.2 Bring up the container: `docker compose up -d`.
- [x] 3.3 Verify the container is on `nginx-proxy-network`: `docker inspect princess --format '{{json .NetworkSettings.Networks}}' | jq 'keys'` includes `nginx-proxy-network`.
- [x] 3.4 Reload nginx now that the upstream resolves: `docker exec nginx-director nginx -s reload`.
- [x] 3.5 End-to-end check from a browser at the deployment URL: create a room, add a bot, play one move. (No commit — verification only.)

## 4. Register the self-hosted runner

- [x] 4.1 Mint a registration token: `gh api -X POST /repos/mhuot/princess/actions/runners/registration-token --jq .token`.
- [x] 4.2 On the host: `mkdir -p actions-runner && cd actions-runner` and download the latest `actions-runner-linux-arm64-*.tar.gz` from `github.com/actions/runner/releases/latest`; extract.
- [x] 4.3 Configure: `./config.sh --url https://github.com/mhuot/princess --token <TOKEN> --name princess-deploy --labels princess --work _work --unattended`. (`self-hosted`, `Linux`, `ARM64` are added automatically.)
- [x] 4.4 Install + start as a systemd service: `sudo ./svc.sh install ubuntu && sudo ./svc.sh start`. Confirm `systemctl status actions.runner.mhuot-princess.princess-deploy.service` reports `active (running)` and `Listening for Jobs`.
- [x] 4.5 Confirm the runner appears via `gh api /repos/mhuot/princess/actions/runners --jq '.runners[]|{name,status,labels}'` with status `online` and labels including `princess`.
- [x] 4.6 Add `actions-runner/` to `.gitignore`.
- [x] 4.7 Commit (only if `.gitignore` changed): `deploy-via-nginx-director: Ignore self-hosted runner workdir`

## 5. Deploy workflow

- [x] 5.1 Write `.github/workflows/deploy.yml`:
  - `name: Deploy`
  - `on: { push: { branches: [main] }, workflow_dispatch: {} }`
  - `concurrency: { group: deploy-princess, cancel-in-progress: false }`
  - `jobs.deploy.runs-on: [self-hosted, princess]`
  - Steps: `actions/checkout@v4`; `docker compose up -d --build`; `sleep 5`; smoke (`docker exec princess python -c "import urllib.request,sys; r=urllib.request.urlopen('http://127.0.0.1:8000/',timeout=10); sys.exit(0 if r.status==200 else 1)"`); on failure `docker compose logs --tail=100 princess`.
- [x] 5.2 Local syntax check: `python -c 'import yaml; yaml.safe_load(open(".github/workflows/deploy.yml"))'`.
- [x] 5.3 Commit: `deploy-via-nginx-director: Add deploy workflow on push to main`
- [ ] 5.4 Push the feature branch; open a PR; confirm `tests`, `lint`, `openspec` workflows run on GitHub-hosted runners (deploy must NOT trigger on PR).
- [ ] 5.5 Merge the PR. Watch the `Deploy` workflow fire on the self-hosted runner. Confirm green and that the container has a fresh `Created` timestamp.
- [ ] 5.6 Manually re-trigger via `gh workflow run deploy.yml --ref main`; confirm `workflow_dispatch` works.

## 6. CI shake-out

- [ ] 6.1 Confirm all four workflows are green on `main`: `tests`, `lint`, `openspec`, `deploy`.
- [ ] 6.2 If the `openspec` workflow flags anything about the new spec, fix and commit per task.

## 7. Wrap up

- [ ] 7.1 Run `openspec validate deploy-via-nginx-director --strict` — expect zero errors.
- [ ] 7.2 Browser smoke from a different network — confirms public reachability + WebSocket upgrade through the proxy.
- [ ] 7.3 Archive via `openspec archive deploy-via-nginx-director` once everything is checked off and CI is green.
