# ⚡ cloudctl (Custom Cloud CLI)

**Python-powered CLI tool orchestrating Terraform deployments and cloud environment management.**

## Overview

`cloudctl` is a custom command-line interface built in Python that abstracts complex infrastructure operations into simple, repeatable commands. It acts as the control plane for the Secure Cloud Platform, managing everything from bootstrapping infrastructure to validation and connection testing.

## Technologies Used

* **Python 3.9+**
* **Typer:** Modern CLI framework leveraging Python type hints (builds on Click).
* **Subprocess Management:** Interfacing with Terraform binaries.
* **Paramiko / Subprocess SSH:** Secure connection testing and remote execution.

## Installation & Setup

1. **Prerequisites:** Ensure Python 3.9+ and Terraform are installed.
2. **Virtual Environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate
   ```
3. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
4. **Configuration:**
   Review and update `config/settings.yaml` to specify the `key_path` (your local SSH private key) and `user` (e.g., `ec2-user`) for remote host connections.

## Command Reference

Run the main entrypoint to see available commands: `python main.py --help`

| Command | Description |
|---|---|
| `deploy` | Provisions infrastructure via Terraform and deploys the web service container. |
| `destroy` | Safely stops/removes remote containers and destroys all Terraform-managed infrastructure. |
| `status` | Collects runtime metrics and service status (Docker, memory, ports) directly from the remote host. |
| `validate` | Runs post-deployment checks against the target host (SSH connectivity, Docker state, HTTP response). |

## Extending the CLI

To add new functionality, create a new module in the `commands/` directory and register it in `main.py`. Use `commands/common.py` for shared helper functions across the CLI.
