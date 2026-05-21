import requests
import typer

from commands.common import CONTAINER
from ssh.client import SSHClient, get_terraform_outputs, load_settings

app = typer.Typer()
HTTP_TIMEOUT = 5


@app.callback(invoke_without_command=True)
def validate() -> None:
    """Run post-deployment validation checks against the target host."""
    typer.echo("[INFO] Starting validation...")

    try:
        outputs = get_terraform_outputs()
        settings = load_settings()

        host = outputs["public_ip"]
        key_path = settings["ssh"]["key_path"]
        user = settings["ssh"]["user"]
    except Exception as error:
        typer.echo(f"[ERROR] Failed to load Terraform outputs or settings: {error}")
        raise typer.Exit(code=1)

    typer.echo("[INFO] Checking SSH connectivity...")

    image_out = ""

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

            image_out, _ = ssh.run(
                f"sudo docker inspect {CONTAINER} --format='{{{{.Config.Image}}}}'"
            )
    except typer.Exit:
        raise
    except Exception as error:
        typer.echo(f"[ERROR] SSH failed: {error}")
        raise typer.Exit(code=1)

    typer.echo("[INFO] Checking HTTP response...")

    try:
        response = requests.get(f"http://{host}/health", timeout=HTTP_TIMEOUT)
        response.raise_for_status()
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

    if deployed_version:
        typer.echo(f"[INFO] Deployed version: {deployed_version}")
    else:
        typer.echo("[WARN] Version endpoint returned no version")

    if image_out.strip():
        typer.echo(f"[INFO] Running image: {image_out.strip()}")

    typer.echo("[SUCCESS] Validation complete.")
