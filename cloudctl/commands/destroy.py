import typer
from commands.common import run_terraform, wait_for_ssh_ready
from ssh.client import SSHClient, get_terraform_outputs, load_settings

app = typer.Typer()
CONTAINER = "webapp"


def destroy_containers(ssh: SSHClient) -> None:
    """Stop and remove all Docker containers from the instance."""
    container_ids, _ = ssh.run("sudo docker ps -aq", check=True)

    if not container_ids.split():
        return

    ssh.run(
        "ids=$(sudo docker ps -aq); if [ -n \"$ids\" ]; then sudo docker rm -f $ids; fi",
        check=True,
    )

    remaining_ids, _ = ssh.run("sudo docker ps -aq", check=True)
    if remaining_ids.split():
        raise RuntimeError("Some Docker containers still exist after cleanup.")


@app.callback(invoke_without_command=True)
def destroy() -> None:
    confirm = typer.confirm("This will destroy ALL resources. Continue?")

    if not confirm:
        print("[INFO] Aborted.")
        return
    
    """Destroy service infrastructure."""
    typer.echo("[INFO] Starting destroy...")

    host = None
    key_path = None
    user = None

    try:
        outputs = get_terraform_outputs()
        settings = load_settings()

        host = outputs["public_ip"]
        key_path = settings["ssh"]["key_path"]
        user = settings["ssh"]["user"]
    except Exception as error:
        typer.echo(f"[WARN] Unable to load target host details for remote cleanup: {error}")
        typer.echo("[INFO] Continuing with Terraform destroy only.")

    if host and key_path and user:
        try:
            typer.echo("[INFO] Waiting for SSH readiness...")
            wait_for_ssh_ready(host=host, key_path=key_path, user=user, logger=typer.echo)

            with SSHClient(host=host, key_path=key_path, user=user) as ssh:
                typer.echo("[INFO] Destroying all Docker containers...")
                destroy_containers(ssh)

            typer.echo("[SUCCESS] Remote container cleanup complete")
        except Exception as error:
            typer.echo(f"[WARN] Remote cleanup failed: {error}")
            typer.echo("[INFO] Continuing with Terraform destroy...")

    try:
        typer.echo("[INFO] Initializing Terraform...")
        run_terraform(["terraform", "init"])

        typer.echo("[INFO] Destroying infrastructure...")
        run_terraform(["terraform", "destroy", "-auto-approve"])

        typer.echo("[SUCCESS] Destruction complete.")
    except Exception as error:
        typer.echo(f"[ERROR] Destruction failed: {error}")
        raise typer.Exit(code=1)
