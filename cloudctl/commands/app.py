from pathlib import Path
import os

import typer

from commands.common import CONTAINER, wait_for_ssh_ready
from commands.validate import run_validation
from ssh.client import SSHClient, get_terraform_outputs, load_settings

app = typer.Typer(help="Application deployment commands.")

BOOTSTRAP = Path(__file__).resolve().parents[1] / "scripts/bootstrap.sh"
DEPLOY_SCRIPT = Path(__file__).resolve().parents[1] / "scripts/deploy_container.sh"


def get_image() -> str:
    """Get the image URI from settings or environment, defaulting to repository/tag."""
    settings = load_settings()
    image_settings = settings.get("image", {})
    uri = image_settings.get("uri") or os.getenv("CONTAINER_IMAGE")
    if uri:
        return uri

    repository = image_settings.get("repository") or os.getenv(
        "CONTAINER_REPOSITORY",
        "ghcr.io/richard-romero/cloud-status-api",
    )
    tag = image_settings.get("tag") or os.getenv("CONTAINER_TAG") or os.getenv(
        "APP_VERSION",
        "latest",
    )
    return f"{repository}:{tag}"


def _image_tag(image: str) -> str:
    return image.rsplit(":", 1)[-1]


def deploy_app() -> str:
    """Deploy the application to the current infrastructure."""
    settings = load_settings()
    image = get_image()

    if not BOOTSTRAP.exists():
        raise FileNotFoundError(f"Bootstrap script was not found at {BOOTSTRAP}")
    if not DEPLOY_SCRIPT.exists():
        raise FileNotFoundError(f"Deploy script was not found at {DEPLOY_SCRIPT}")

    outputs = get_terraform_outputs()

    host = outputs["public_ip"]
    key_path = settings["ssh"]["key_path"]
    user = settings["ssh"]["user"]
    remote_bootstrap = "/home/ec2-user/bootstrap.sh"
    remote_deploy = "/home/ec2-user/deploy_container.sh"

    typer.echo("[INFO] Waiting for SSH readiness...")
    wait_for_ssh_ready(host=host, key_path=key_path, user=user, logger=typer.echo)

    with SSHClient(host=host, key_path=key_path, user=user) as ssh:
        typer.echo("[INFO] Uploading scripts...")
        ssh.upload(str(BOOTSTRAP), remote_bootstrap)
        ssh.upload(str(DEPLOY_SCRIPT), remote_deploy)

        typer.echo("[INFO] Executing bootstrap...")
        bootstrap_out, bootstrap_err = ssh.run(
            f"chmod +x {remote_bootstrap} && sudo {remote_bootstrap}",
            check=True,
        )
        if bootstrap_out:
            typer.echo(bootstrap_out.rstrip())
        if bootstrap_err:
            typer.echo(bootstrap_err.rstrip())

        typer.echo("[INFO] Executing deployment script...")
        deploy_out, deploy_err = ssh.run(
            f"chmod +x {remote_deploy} && sudo {remote_deploy} {image} {CONTAINER}",
            check=True,
        )
        if deploy_out:
            typer.echo(deploy_out.rstrip())
        if deploy_err:
            typer.echo(deploy_err.rstrip())

    typer.echo("[INFO] Validating deployment with external HTTP check...")
    run_validation(
        host=host,
        key_path=key_path,
        user=user,
        expected_image_tag=_image_tag(image),
    )

    return host


@app.command()
def deploy() -> None:
    """Deploy the application to existing infrastructure."""
    try:
        host = deploy_app()
        typer.echo(f"[SUCCESS] App deployment complete. Instance public IP: {host}")
    except typer.Exit:
        raise
    except Exception as error:
        typer.echo(f"[ERROR] App deployment failed: {error}")
        raise typer.Exit(code=1)
