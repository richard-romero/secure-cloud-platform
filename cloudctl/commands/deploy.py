import typer

from commands.app import deploy_app
from commands.infra import apply_infra

app = typer.Typer()


@app.callback(invoke_without_command=True)
def deploy() -> None:
    """Provision infrastructure and deploy service."""
    try:
        apply_infra()
        host = deploy_app()
        typer.echo(f"[SUCCESS] Deployment complete. Instance public IP: {host}")
    except typer.Exit:
        raise
    except Exception as error:
        typer.echo(f"[ERROR] Deployment failed: {error}")
        raise typer.Exit(code=1)
