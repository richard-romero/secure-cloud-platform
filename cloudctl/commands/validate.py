import time
from typing import Optional

import requests
import typer

from commands.common import CONTAINER
from ssh.client import SSHClient, get_terraform_outputs, load_settings

app = typer.Typer()
HTTP_TIMEOUT = 5
HTTP_RETRIES = 5
HTTP_RETRY_DELAY = 2


def get_with_retries(url: str) -> requests.Response:
    """Request a URL with retries for transient connectivity issues."""
    last_error: Optional[requests.RequestException] = None

    for attempt in range(1, HTTP_RETRIES + 1):
        try:
            response = requests.get(url, timeout=HTTP_TIMEOUT)
            response.raise_for_status()
            return response
        except requests.RequestException as error:
            last_error = error
            if attempt == HTTP_RETRIES:
                break
            typer.echo(
                f"[INFO] HTTP check failed ({attempt}/{HTTP_RETRIES}). Retrying in {HTTP_RETRY_DELAY}s..."
            )
            time.sleep(HTTP_RETRY_DELAY)

    if last_error is None:
        raise typer.Exit(code=1)

    raise last_error


def run_validation(
    host: str,
    key_path: str,
    user: str,
    expected_image_tag: Optional[str] = None,
) -> None:
    """Run pass/fail smoke tests against the target host.

    Use ``status`` for detailed operational diagnostics.
    """
    typer.echo("[INFO] Starting validation...")
    typer.echo("[INFO] Checking SSH connectivity...")

    try:
        with SSHClient(host=host, key_path=key_path, user=user) as ssh:
            typer.echo("[SUCCESS] SSH reachable")

            typer.echo("[INFO] Checking Docker service...")

            running_out, running_err = ssh.run(
                f"sudo docker inspect -f '{{{{.State.Running}}}}' {CONTAINER}"
            )

            if running_err.strip():
                typer.echo(f"[ERROR] Failed to inspect container: {running_err.strip()}")
                raise typer.Exit(code=1)

            if running_out.strip() != "true":
                typer.echo("[ERROR] Container is not running")
                raise typer.Exit(code=1)

            typer.echo("[SUCCESS] Container running")
    except typer.Exit:
        raise
    except Exception as error:
        typer.echo(f"[ERROR] SSH failed: {error}")
        raise typer.Exit(code=1)

    typer.echo("[INFO] Checking HTTP response...")

    try:
        response = get_with_retries(f"http://{host}/health")
        data = response.json()

        if data.get("status") == "healthy":
            typer.echo("[SUCCESS] Health endpoint healthy")
        else:
            typer.echo("[ERROR] Health endpoint returned unexpected response")
            raise typer.Exit(code=1)
    except (requests.RequestException, ValueError) as error:
        typer.echo(f"[ERROR] Cannot reach HTTP service: {error}")
        raise typer.Exit(code=1)

    typer.echo("[INFO] Checking deployed version...")

    try:
        version_response = requests.get(
            f"http://{host}/version",
            timeout=HTTP_TIMEOUT,
        )
        version_response.raise_for_status()
        version_data = version_response.json()
    except (requests.RequestException, ValueError) as error:
        typer.echo(f"[ERROR] Version endpoint check failed: {error}")
        raise typer.Exit(code=1)

    deployed_version = version_data.get("version")
    deployed_commit = version_data.get("commit")
    deployed_at = version_data.get("deployed_at")

    missing_fields = [
        field
        for field, value in (
            ("version", deployed_version),
            ("commit", deployed_commit),
            ("deployed_at", deployed_at),
        )
        if not value
    ]

    if missing_fields:
        typer.echo(
            f"[ERROR] Version endpoint missing required fields: {', '.join(missing_fields)}"
        )
        raise typer.Exit(code=1)

    typer.echo(f"[SUCCESS] Version metadata valid ({deployed_version})")

    if expected_image_tag and deployed_version != expected_image_tag:
        typer.echo(
            "[ERROR] Deployed version does not match expected image tag "
            f"(expected {expected_image_tag}, got {deployed_version})"
        )
        raise typer.Exit(code=1)

    if expected_image_tag:
        typer.echo(f"[SUCCESS] Deployed image tag matches expected ({expected_image_tag})")

    typer.echo("\n[INFO] Run 'cloudctl status' for detailed operational diagnostics.")
    typer.echo("\n[SUCCESS] Validation complete.")


@app.callback(invoke_without_command=True)
def validate() -> None:
    """Run pass/fail smoke tests against the target host.

    Use ``status`` for detailed operational diagnostics.
    """
    try:
        outputs = get_terraform_outputs()
        settings = load_settings()

        host = outputs["public_ip"]
        key_path = settings["ssh"]["key_path"]
        user = settings["ssh"]["user"]
    except Exception as error:
        typer.echo(f"[ERROR] Failed to load Terraform outputs or settings: {error}")
        raise typer.Exit(code=1)

    run_validation(host=host, key_path=key_path, user=user)
