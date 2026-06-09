## ADDED Requirements

### Requirement: Princess ships as a Docker image

The repository SHALL include a top-level `Dockerfile` that builds a runnable Princess server image using only the production `requirements.txt`. The image SHALL expose port `8000`, run as a non-root user, and start the server via `python -m princess` with `HOST=0.0.0.0`.

#### Scenario: Image builds from a clean checkout

- **WHEN** a developer runs `docker compose build` against a fresh clone
- **THEN** the build completes without error
- **AND** the resulting image runs `python -m princess` as its default command
- **AND** the running process listens on `0.0.0.0:8000`

#### Scenario: Image does not include development dependencies

- **WHEN** the built image is inspected (e.g., `docker run --rm princess pip list`)
- **THEN** `fastapi`, `uvicorn`, and `pydantic` are present
- **AND** `pytest`, `pylint`, and `black` are NOT present

#### Scenario: Image runs as a non-root user

- **WHEN** the container is started and `id` is run inside it
- **THEN** the effective UID is not `0`

### Requirement: Compose file targets the nginx-proxy-network

The repository SHALL include a top-level `docker-compose.yml` defining exactly one service named `princess` with `container_name: princess`, attached to the external Docker network `nginx-proxy-network`, with `restart: unless-stopped`.

#### Scenario: Service connects to the proxy network

- **WHEN** `docker compose up -d` is run
- **THEN** the `princess` container is on the `nginx-proxy-network`
- **AND** `docker network inspect nginx-proxy-network` lists `princess` as a connected container

#### Scenario: Service restarts on host reboot

- **WHEN** the container exits unexpectedly or the host reboots
- **THEN** Docker restarts the `princess` container automatically (per `restart: unless-stopped`)

### Requirement: Fronted by nginx-director with WebSocket support

Princess SHALL be reachable through nginx-director, registered as the app named `princess` with the upstream `princess:8000`. The nginx server block SHALL forward HTTP and WebSocket traffic (`Upgrade` / `Connection` headers preserved) so the in-game `/ws/{code}/{pid}` channel survives the proxy.

#### Scenario: HTTP lands on the lobby through the proxy

- **WHEN** a request reaches the proxy with the configured Host header
- **THEN** the response is the Princess lobby HTML (HTTP 200) served from the upstream

#### Scenario: WebSocket upgrade survives the proxy

- **WHEN** a player joins a room
- **THEN** the WebSocket connection to `/ws/{code}/{pid}` upgrades successfully through nginx
- **AND** real-time game state updates flow without the connection dropping

#### Scenario: nginx-director registration files are well-formed

- **WHEN** the nginx-director sync script runs
- **THEN** `princess` is reported with both `Container: ✅` and `DNS: ✅`

### Requirement: Push to main auto-deploys via a self-hosted runner

The repository SHALL include `.github/workflows/deploy.yml` that triggers on `push` to `main` and on `workflow_dispatch`. The deploy job SHALL run on a self-hosted runner identified by the `princess` label. The deploy step SHALL execute `docker compose up -d --build` and SHALL fail the workflow if a post-deploy HTTP smoke against the container's `127.0.0.1:8000/` does not return `200`.

#### Scenario: Merge to main triggers a deploy

- **WHEN** a commit lands on the `main` branch (via PR merge or direct push)
- **THEN** the `Deploy` workflow run is queued automatically
- **AND** it is picked up by a runner with the `princess` label

#### Scenario: Pull request does NOT trigger a deploy

- **WHEN** a pull request is opened, updated, or closed without merging
- **THEN** the `Deploy` workflow does not run

#### Scenario: Failed smoke fails the workflow

- **WHEN** the post-deploy HTTP smoke against the container returns any status other than `200` (or times out)
- **THEN** the workflow job exits non-zero
- **AND** the workflow log includes the last 100 lines of `docker compose logs princess`

#### Scenario: Manual redeploy works

- **WHEN** an operator runs `gh workflow run deploy.yml --ref main` (or clicks "Run workflow" in the UI)
- **THEN** the deploy job runs against the current `main` and follows the same build + smoke contract

### Requirement: Deploy concurrency is serialized

The deploy workflow SHALL declare a `concurrency` group such that simultaneous deploys queue rather than overlap or cancel each other.

#### Scenario: Rapid successive merges queue

- **WHEN** two commits land on `main` within seconds of each other
- **THEN** the first deploy run completes (success or failure) before the second deploy run starts
- **AND** neither run is cancelled by the other

### Requirement: Naming policy applies to deployment surfaces

Every deployment-related identifier exposed to operators or end users — Docker container name, compose service name, nginx upstream, GitHub workflow name, runner label, image tag — SHALL use the word "Princess" (or `princess` in lowercase contexts) only. The inspiring game's vulgar name MUST NOT appear in any of these surfaces.

#### Scenario: All deployment identifiers stay on-brand

- **WHEN** an operator runs `docker ps`, `gh workflow list`, or inspects the nginx server block
- **THEN** every visible identifier related to this deployment uses "Princess" / "princess"
- **AND** none uses the inspiring game's vulgar name in any case or form
