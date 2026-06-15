# cloudctl (Custom Cloud CLI)

**Python-powered CLI tool orchestrating Terraform deployments and cloud environment management.**

## Overview

`cloudctl` is a custom command-line interface built in Python that abstracts complex infrastructure operations into simple, repeatable commands. It acts as the control plane for the Secure Cloud Platform, managing everything from bootstrapping infrastructure to validation and connection testing.

## Technologies Used

* **Python 3.9+**
* **Typer:** Modern CLI framework leveraging Python type hints.
* **Subprocess Management:** Interfacing with Terraform binaries.
* **Paramiko / Subprocess SSH:** Secure connection testing and remote execution.

## Installation & Setup

1. **Prerequisites:** Ensure Python 3.9+ and Terraform are installed.
2. **Virtual Environment:**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```
3. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
4. **Configuration:**
   Review and update `config/settings.yaml` to specify the `key_path` (your local SSH private key), `user` (e.g., `ec2-user`), and `allowed_cidr` (your public IP in `/32` form) for remote host connections. `cloudctl infra apply` (and `cloudctl deploy`) passes the CIDR into Terraform so you do not need to provide `-var` manually.

   For CI/CD secrets and the GitHub Actions deploy path, see [GitHub Secrets & CI Deploy](../README.md#github-secrets--ci-deploy) in the project README.

## Command Reference

Run the main entrypoint to see available commands: `python3 main.py --help`

| Command | Description |
|---|---|
| `infra apply` | Provisions infrastructure via Terraform. |
| `app deploy` | Deploys the web service container using a rolling update and validates the deployment. |
| `deploy` | Convenience wrapper that runs `infra apply` and `app deploy`. |
| `destroy` | Safely stops/removes remote containers and destroys all Terraform-managed infrastructure. |
| `status` | Operational visibility: deployment summary, host metrics, Docker state, ports, logs. |
| `validate` | Pass/fail smoke test: SSH, container running, `/health`, `/version` metadata. |

## Validate vs Status

These commands answer different questions and are intentionally separated:

| Concern | `validate` | `status` |
|---|---|---|
| Purpose | Is the deployment healthy? | What is the system doing right now? |
| Exit code on app failure | Yes | No (informational) |
| HTTP checks | External (public IP) | Internal (SSH to localhost) |
| Expected image tag match | Yes (during deploy) | No |
| Deployment summary | No | Yes |
| Host metrics / logs / ports | No | Yes |

- Run **`cloudctl validate`** after deploy or when you need a quick pass/fail check.
- Run **`cloudctl status`** when investigating issues or reviewing operational detail.

The deployment summary in `status` displays Phase 12 fields: deployed image tag, container health, deployment timestamp, and running version (sourced from Docker inspect and the `/version` endpoint).

## Deployment Metadata

The application exposes `GET /version` with:

```json
{
  "version": "sha-a13f92",
  "commit": "a13f92",
  "deployed_at": "2026-05-18T14:00:00Z"
}
```

`version` reflects the deployed image tag. `commit` is the git SHA baked into the image at CI build time. `deployed_at` is set when `deploy_container.sh` starts the container.

## Rolling Updates

`deploy_container.sh` performs a same-host blue-green deploy:

1. Start a staging container on port 8080
2. Health-check the staging container
3. Stop and remove the old production container on port 80
4. Start the new production container on port 80

If the staging health check fails, the staging container is removed and the existing production container is left running.

## Extending the CLI

To add new functionality, create a new module in the `commands/` directory and register it in `main.py`. Use `commands/common.py` for shared helper functions across the CLI.
