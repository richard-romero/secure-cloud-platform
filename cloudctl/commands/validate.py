import typer
import requests
import time
from ssh.client import SSHClient, get_terraform_outputs, load_settings

app = typer.Typer()
CONTAINER = "webapp"


@app.callback(invoke_without_command=True)
def validate():
    """Run post-deployment validation checks against the target host."""
    start = time.perf_counter()

    typer.echo("[INFO] Starting validation...")

    outputs = get_terraform_outputs()
    settings = load_settings()

    host = outputs["public_ip"]
    key_path = settings["ssh"]["key_path"]
    user = settings["ssh"]["user"]

    # -------------------------
    # SSH CHECK
    # -------------------------
    typer.echo("[INFO] Checking SSH connectivity...")

    try:
        with SSHClient(host, key_path, user) as ssh:
            typer.echo("[SUCCESS] SSH reachable")

            # -------------------------
            # DOCKER CHECK
            # -------------------------
            typer.echo("[INFO] Checking Docker service...")

            out, err = ssh.run("sudo systemctl is-active docker")
            service_state = out.strip()

            if service_state != "active":
                details = err.strip() or service_state or "unknown"
                typer.echo(f"[ERROR] Docker not running (state/details: {details})")
                raise typer.Exit(code=1)

            typer.echo("[SUCCESS] Docker running")

            # -------------------------
            # CONTAINER CHECK
            # -------------------------
            typer.echo("[INFO] Checking container status...")

            out, err = ssh.run("sudo docker ps --format '{{.Names}}'")
            running_containers = {name.strip() for name in out.splitlines() if name.strip()}

            if CONTAINER not in running_containers:
                details = err.strip() or out.strip() or "none"
                typer.echo(f"[ERROR] {CONTAINER} container not running (details: {details})")
                raise typer.Exit(code=1)

            typer.echo("[SUCCESS] Container running")
    except typer.Exit:
        raise
    except Exception as e:
        typer.echo(f"[ERROR] SSH failed: {e}")
        raise typer.Exit(code=1)

    # -------------------------
    # HTTP CHECK
    # -------------------------
    typer.echo("[INFO] Checking HTTP response...")

    try:
        r = requests.get(f"http://{host}", timeout=5)

        if r.status_code == 200:
            typer.echo("[SUCCESS] Service reachable")
        else:
            typer.echo("[ERROR] HTTP unhealthy")
            raise typer.Exit(code=1)   
    except Exception:
        typer.echo("[ERROR] Cannot reach HTTP service")
        raise typer.Exit(code=1)

    typer.echo("[SUCCESS] Validation complete.")
    typer.echo(f"[INFO] Completed in {time.perf_counter() - start:.2f}s")