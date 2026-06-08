## Context

Princess is a single-process FastAPI app: in-memory rooms, no DB, no background workers. The deployment problem is narrow — make one container reachable, redeploy when `main` moves.

The host already runs nginx-director (a wildcard-SSL proxy for hobby apps) and an unrelated self-hosted GitHub Actions runner for another repo. Both patterns are proven; this change adds a second tenant to each.

The hostname/subdomain Princess will be served at is intentionally not captured in this repo. It is an operator-time decision recorded in private runbooks. The repo only knows about the container contract (port 8000, network `nginx-proxy-network`) and the deploy contract (push-to-main → self-hosted runner).

## Decisions

### Use nginx-director as the reverse-proxy layer

**Decision:** Register Princess as just another app in nginx-director, exactly like the other apps it fronts.

**Why:** Wildcard cert is already mounted; HTTP→HTTPS redirect, security headers, error pages, and WebSocket-friendly proxy settings are all in the existing `templates/app.conf.template`. Adding one more app is one MCP `create_app` call (which atomically writes the per-app JSON, generates the nginx server block, creates the DNS A record, and reloads nginx). Building a parallel cert/proxy stack inside the Princess repo would duplicate solved problems.

**Alternative considered:** Standalone Caddy or Traefik in the Princess compose file. Rejected because we'd need a second SSL cert and DNS pattern, and the host already binds 80/443 to nginx-director.

### Self-hosted runner over SSH-from-GitHub-hosted

**Decision:** Register a new self-hosted runner under the repo at `actions-runner/`, scoped to `mhuot/princess`, run via systemd as user `ubuntu`. Deploy workflow targets `runs-on: [self-hosted, princess]`.

**Why:**
- No inbound SSH from GitHub IP ranges; the runner reaches out to GitHub.
- No SSH key as a repo secret to rotate.
- The runner runs as `ubuntu`, who already owns the Princess working tree and has Docker socket access (member of `docker` group, same as the sibling runner).
- Deploy step is a one-liner: `docker compose up -d --build` against a path the runner already has checked out.

**Alternative considered:** Reuse the existing runner registered to the other repo. Rejected — runner agents are bound to exactly one scope at registration time. The other repo is under an org Princess does not belong to, so we can't share via an org-level upgrade. Running two runner agents side-by-side on one host is the documented pattern; cost is ~50–120MB RAM each.

**Alternative considered:** SSH from a GitHub-hosted runner. Rejected — more moving parts (key rotation, IP allowlist, sshd config) for no upside since we already own the host.

### Runner label scheme

**Decision:** Labels = `self-hosted` (default), `linux`, `ARM64` (default for aarch64), and `princess` (the scoping label).

**Why:** `princess` is the meaningful selector — `runs-on: [self-hosted, princess]` makes the deploy workflow refuse to run on any other runner the host might offer. The architecture/OS labels are informational.

### Deploy trigger: push to main, no in-workflow test gate

**Decision:** Deploy workflow triggers on `push: branches: [main]` and `workflow_dispatch`. It does NOT depend on `tests.yml` / `lint.yml` via `workflow_run`.

**Why:** Branch protection on `main` (per the existing `repository-meta` capability) requires tests + lint + openspec checks to pass before a PR can merge. Anything that lands on `main` has already cleared the gate. Adding a `workflow_run` chain doubles deploy latency and complicates retriggering. The accepted risk: a direct push to `main` (bypassing PRs) would deploy without re-running the checks; the user mitigates with branch protection settings.

**Alternative considered:** `workflow_run: workflows: [Tests, Lint]`. Rejected for the reasons above. Easy to add later.

### Post-deploy smoke uses docker exec, not host curl

**Decision:** After `docker compose up -d --build`, the workflow waits 5s, then runs `docker exec princess python -c "..."` to GET `http://127.0.0.1:8000/` from inside the container itself. Non-200 fails the workflow and dumps `docker compose logs --tail=100`.

**Why:** The compose service joins `nginx-proxy-network` but exposes no host port mapping — port 8000 is reachable from the proxy and from inside the container, NOT from the runner host's localhost. A host-level `curl localhost:8000` would always fail with connection refused. Running the smoke from inside the container is self-contained, requires no image additions (the image already has `python`), and validates that uvicorn is actually bound and responsive.

**Alternative considered:** Add a host port mapping (`127.0.0.1:8000:8000`). Rejected — risks colliding with anything else on the host and serves no purpose beyond the smoke.

**Alternative considered:** Add a dedicated `/health` endpoint to the app. Out of scope; `/` returns 200 and is a sufficient liveness signal. Can be added later via a `room-server` spec amendment if we want a richer contract.

### Container name == app name == upstream name

**Decision:** Container name is `princess`. nginx upstream is `princess`. App registration name is `princess`.

**Why:** nginx resolves upstream hostnames against the Docker network's DNS, which uses the container name. Keeping these strings identical removes the "which `princess` is this" cognitive cost.

### No persistent volumes

**Decision:** The container declares no volumes. Rooms live in `princess.rooms` (in-memory dict). A redeploy drops all rooms.

**Why:** Consistent with how the app already works (local `python -m princess` also drops rooms on restart). Adding persistence is a separate, larger conversation about DB choice, schema migrations, and room lifecycle — out of scope.

**Risk accepted:** Players mid-game during a deploy lose their connection and rooms vanish. Acceptable for a hobby game on push-to-main; deploys are infrequent and can be announced. If this becomes painful, the future fix is graceful shutdown + sticky rooms, not "add a database for state."

### Production image excludes dev dependencies

**Decision:** Dockerfile installs `requirements.txt` only — not `requirements-dev.txt`. No `pytest`, `pylint`, `black` in the runtime image.

**Why:** Image stays minimal (~150MB), faster to build and push. CI workflows install dev deps in their own ephemeral environment.

### No README/CHANGELOG entry for the URL

**Decision:** This change ships the infra but does NOT add the public URL (or any deployment hostname) to README, CHANGELOG, or CONTRIBUTING.

**Why:** The operator explicitly wants the live URL un-publicized for now. The deployment exists; advertising its location in the repo is a separate decision. When/if the operator decides to publish, a follow-up change can update the docs.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Self-hosted runner is a privileged process — a malicious PR could pwn the host. | Workflow only runs on `push` to `main`, not on `pull_request`. PRs from forks can't trigger it. Branch protection requires PR review before merge. |
| `docker compose up -d --build` builds in-place — a build failure leaves the old container running but the workflow red. | Desirable (no broken rollout). Operator inspects the workflow log and fixes forward. |
| Second runner consumes ~50–120MB RAM continuously. | Acceptable on the deployment host. |
| Push-to-main = deploy with no human gate. | Matches operator preference. Easy to add a manual `workflow_dispatch`-only mode later. |
| The repo names `mhuot/princess` openly (in the runner registration command, badge URLs, etc.) — discoverable to anyone with the GitHub URL. | The GitHub repo is already public; this change adds no new disclosure beyond what already exists there. The deployment URL is the only piece kept private. |

## Migration Plan

Green-field deploy — no existing princess deployment to migrate. Order of operations is captured in `tasks.md`. The reversibility plan (in `proposal.md` → Impact → Reversible) covers full teardown.

## Open Questions

None. The operator confirmed: deploy mechanism (second self-hosted runner) and trigger (push to main). The deployment hostname is deliberately not captured here.
