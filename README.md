# Secure Cloud Platform

[![Python](https://img.shields.io/badge/Python-3.9%2B-blue.svg)](https://www.python.org/)
[![Terraform](https://img.shields.io/badge/Terraform-IaC-623CE4.svg)](https://www.terraform.io/)
[![AWS](https://img.shields.io/badge/AWS-Cloud-FF9900.svg)](https://aws.amazon.com/)

**An end-to-end cloud environment automation project showcasing Infrastructure as Code (IaC) principles and custom CLI tooling.**

![cloudctl deployment demo](assets/demo.gif)

## Overview

The **Secure Cloud Platform** is a two-part project designed to demonstrate production-ready cloud engineering skills. It combines a robust **Terraform** infrastructure setup on AWS with `cloudctl`, a custom **Python CLI application** built to abstract and orchestrate infrastructure deployments.

I built this abstraction to solve the problem of developer friction when deploying AWS environments. Instead of expecting them to understand Terraform state files and raw HCL, they can leverage `cloudctl` to run validations, deploy and securely destroy  infrastructure, query status, and handle secure connectivity. This configuration mirrors how internal developer platforms (IDPs) are built in modern enterprise environments.

## Project Structure

This project is separated into two primary micro-components. **Please see their respective READMEs for detailed documentation and local setup instructions:**

* **[`/terraform/README.md`](terraform/README.md):** The IaC backbone. Defines the AWS VPC, subnets, EC2 instances, security groups, and automated Bash bootstrapping scripts.
* **[`/cloudctl/README.md`](cloudctl/README.md):** The Python CLI control plane. Manages the Terraform lifecycle, handles configuration (`settings.yaml`), and provides commands like `deploy`, `status`, and `destroy`.

## Key Technical Achievements 

* **DevOps & CI/CD Readiness:** Built an automated Python pipeline to orchestrate Terraform. `cloudctl` is highly extensible and easily integratable into CI/CD systems like GitHub Actions or Jenkins.
* **Security & Least Privilege:** Configured strict network segmentation and utilized IAM Instance Profiles rather than hardcoded API keys. Implemented IMDSv2 (Server-Side Request Forgery protection) on compute nodes.
* **Idempotency & State Management:** `cloudctl deploy` relies on Terraform's idempotency, ensuring safe, repeatable runs that only change necessary resources. Infrastructure state is secured using an S3 backend.

## Quick Start

1. Ensure you have **AWS credentials** configured locally, along with **Python 3.9+** and **Terraform** installed.
2. Clone the repository and navigate to the project root.
3. Install the CLI dependencies:
   ```bash
   cd cloudctl
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
4. Update `cloudctl/config/settings.yaml` with your SSH key path, user, and `allowed_cidr` (your public IP in `/32` form).
5. Deploy the infrastructure using the custom tool:
   ```bash
   python3 main.py deploy
   ```

## Manual Container Release (Optional)

This project uses a manual container release flow to keep things simple. Tests still run on every push to `main`, but container images are only published when you choose.

1. In GitHub Actions, open the `CI Pipeline` workflow and select **Run workflow**.
2. The release publishes two tags to GHCR:
   - `latest`
   - `sha-<short>` (short commit SHA for traceability)
3. The workflow also deploys to EC2 via AWS SSM when the `production` environment is configured (see below).
4. Local deploys still pull `latest` by default (see the `image.tag` setting in [cloudctl/config/settings.yaml](cloudctl/config/settings.yaml)).
5. The `/version` endpoint exposes deployment metadata:

   ```json
   {
     "version": "sha-a13f92",
     "commit": "a13f92",
     "deployed_at": "2026-05-18T14:00:00Z"
   }
   ```

   - `version` — image tag from the deployed container
   - `commit` — git commit SHA baked into the image at build time
   - `deployed_at` — UTC timestamp set when the container is started

6. Rolling updates validate a staging container on port 8080 before replacing the production container on port 80.

## GitHub Secrets & CI Deploy

CI deploy uses **GitHub OIDC** (no long-lived AWS keys) and **AWS Systems Manager** to run the deploy script on EC2. SSH from GitHub-hosted runners is not required, so the EC2 security group can stay locked to your IP for local `cloudctl` access.

Secret **names** appear in [`.github/workflows/ci.yaml`](.github/workflows/ci.yaml); secret **values** are never committed.

### One-time setup

1. Apply Terraform so the EC2 instance receives the SSM policy, the GitHub OIDC deploy role is created, and the deploy role can discover instances:
   ```bash
   cd cloudctl
   python3 main.py infra apply
   terraform -chdir=../terraform output github_actions_role_arn
   ```
2. In GitHub, create an environment named **`production`** (Settings → Environments).
3. Add these **environment secrets** to `production`:

   | Secret | Description |
   |--------|-------------|
   | `SSH_PRIVATE_KEY` | Private key matching the EC2 key pair. Used locally via `settings.yaml`; stored in GitHub for operational hygiene (CI deploy uses SSM, not SSH). |
   | `GHCR_TOKEN` | GitHub PAT with `read:packages` so EC2 can pull private GHCR images during deploy. |

   CI resolves the deploy target automatically via `ec2:DescribeInstances` (tags `ManagedBy=terraform`, `Name=terraform-ec2`). You do **not** need to update GitHub secrets after reprovisioning an instance.

4. Add this **environment variable** to `production`:

   | Variable | Description |
   |----------|-------------|
   | `AWS_ROLE_ARN` | Value of `terraform output github_actions_role_arn`. |

5. Confirm the instance is SSM-online: AWS Console → Systems Manager → Fleet Manager.

### Workflow behavior

| Job | Trigger | Purpose |
|-----|---------|---------|
| `test` | Every push to `main` and manual runs | Run pytest |
| `build-and-push` | Manual `workflow_dispatch` only | Build and push image to GHCR (`GITHUB_TOKEN`) |
| `deploy` | Manual `workflow_dispatch` only | Deploy via SSM, then HTTP smoke-test `/health` and `/version` |

### Design notes

- **OIDC over static AWS keys** — GitHub Actions assumes a short-lived IAM role via `id-token: write`.
- **Dynamic instance discovery** — Deploy finds the running EC2 instance by Terraform tags, so reprovisioning does not require updating GitHub secrets.
- **SSM over SSH from CI** — Deploy commands run through SSM; port 22 stays restricted to your `allowed_cidr`.
- **Scoped GHCR PAT** — CI push uses the built-in `GITHUB_TOKEN`; EC2 pull uses a read-scoped `GHCR_TOKEN`.
- **Environment gating** — Deploy runs in the `production` environment so secrets are scoped and approval rules can be added later.

If your AWS account already has a GitHub OIDC provider, import it into Terraform or adjust [terraform/github_actions.tf](terraform/github_actions.tf) before applying.

---
*Created by Richard Romero | [LinkedIn](https://www.linkedin.com/in/richardromero15/)*
