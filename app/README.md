# cloud-status-api

**FastAPI service containerized and deployed to EC2 by `cloudctl` (local) or GitHub Actions (CI).**

## Role in the Platform

This is the application layer of the [Secure Cloud Platform](../README.md). The service runs in Docker on an EC2 host provisioned by Terraform and orchestrated by [`cloudctl`](../cloudctl/README.md).

- **Built and tested in CI** — pytest runs on every push to `main` ([`.github/workflows/ci.yaml`](../.github/workflows/ci.yaml))
- **Published to GHCR** — `ghcr.io/<owner>/cloud-status-api` (`latest` and `sha-<short>` tags)
- **Deployed with rolling updates** — [`deploy_container.sh`](../cloudctl/scripts/deploy_container.sh) validates a staging container on port 8080 before swapping production on port 80

## API Endpoints

The container listens on port **8000**; the host maps **80** (production) and **8080** (staging during rolling deploy).

| Route | Purpose |
|-------|---------|
| `GET /` | Service identity |
| `GET /health` | Liveness check (used by deploy scripts and CI smoke tests) |
| `GET /version` | Deployment metadata (image tag, commit, timestamp) |
| `GET /metrics` | Uptime and hostname |

### Example: `GET /version`

```json
{
  "version": "sha-a13f92",
  "commit": "a13f92",
  "deployed_at": "2026-05-18T14:00:00Z"
}
```

| Field | Source |
|-------|--------|
| `version` | Image tag (`APP_IMAGE_VERSION`), set at container start |
| `commit` | Git SHA baked into the image at build time (`APP_BUILD_SHA`) |
| `deployed_at` | UTC timestamp set when the container starts (`APP_DEPLOYED_AT`) |

## Environment Variables

| Variable | Set by | Purpose |
|----------|--------|---------|
| `APP_BUILD_SHA` | Docker build (`APP_BUILD_SHA` build-arg in CI) | Git commit embedded in the image |
| `APP_IMAGE_VERSION` | `deploy_container.sh` | Deployed image tag (e.g. `sha-a13f92`, `latest`) |
| `APP_DEPLOYED_AT` | `deploy_container.sh` | ISO 8601 UTC timestamp of container start |

## Local Development

Requires **Python 3.12** (matches CI).

```bash
cd app
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
PYTHONPATH=. pytest
```

Run the API locally:

```bash
uvicorn app.main:app --reload --port 8000
```

Build the container locally:

```bash
docker build --build-arg APP_BUILD_SHA=$(git rev-parse HEAD) -t cloud-status-api .
docker run -p 8000:8000 cloud-status-api
```

## Related Docs

- **Deploy and rolling updates** — [`cloudctl/README.md`](../cloudctl/README.md#rolling-updates)
- **Infrastructure (EC2, Docker host, SSM)** — [`terraform/README.md`](../terraform/README.md)
- **CI/CD release and secrets setup** — [Manual Container Release](../README.md#manual-container-release-optional) and [GitHub Secrets & CI Deploy](../README.md#github-secrets--ci-deploy)
