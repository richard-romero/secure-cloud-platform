import typer

from commands.common import run_terraform
from ssh.client import load_settings

app = typer.Typer(help="Infrastructure commands.")


def apply_infra() -> None:
    """Apply infrastructure via Terraform."""
    settings = load_settings()
    ssh_allowed_cidr = settings.get("ssh", {}).get("allowed_cidr")

    typer.echo("[INFO] Initializing Terraform...")
    run_terraform(["terraform", "init"])

    typer.echo("[INFO] Applying infrastructure...")
    apply_command = ["terraform", "apply", "-auto-approve"]
    if ssh_allowed_cidr:
        apply_command.extend(["-var", f"ssh_allowed_cidr={ssh_allowed_cidr}"])
    run_terraform(apply_command)

    typer.echo("[SUCCESS] Infrastructure apply complete.")


@app.command()
def apply() -> None:
    """Apply infrastructure via Terraform."""
    try:
        apply_infra()
    except typer.Exit:
        raise
    except Exception as error:
        typer.echo(f"[ERROR] Infrastructure apply failed: {error}")
        raise typer.Exit(code=1)
