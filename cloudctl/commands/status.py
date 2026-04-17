import typer
from ssh.client import SSHClient, get_terraform_outputs, load_settings

app = typer.Typer()
CONTAINER = "webapp"

STATUS_COMMANDS = [
    (
        "Host runtime",
        "echo \"Host: $(hostname)\" && echo \"Kernel: $(uname -srmo)\" && uptime",
    ),
    ("Docker service state", "sudo systemctl is-active docker"),
    (
        "Running containers",
        "sudo docker ps --format 'table {{.Names}}\\t{{.Image}}\\t{{.Status}}\\t{{.Ports}}'",
    ),
    (
        "Local HTTP status",
        "if command -v curl >/dev/null 2>&1; then curl -sS -o /dev/null -w '%{http_code}\\n' http://localhost; else echo 'curl not installed'; fi",
    ),
    (
        "Listening ports (22/80/443)",
        "sudo ss -tuln | grep -E ':(22|80|443)[[:space:]]' || true",
    ),
    ("Memory usage", "free -h"),
    ("Disk usage", "df -h /"),
]


def show_command_output(ssh: SSHClient, title: str, command: str) -> None:
    """Run one status command and print its output."""
    typer.echo(f"\n[STATUS] {title}")

    out, err = ssh.run(command)
    if out:
        typer.echo(out.rstrip())

    if err:
        typer.echo(f"[WARN] {err.rstrip()}")


@app.callback(invoke_without_command=True)
def status() -> None:
    """Collect runtime and service status details from the target host."""
    typer.echo("[INFO] Retrieving infrastructure info...")

    try:
        outputs = get_terraform_outputs()
        settings = load_settings()
    except Exception as error:
        typer.echo(f"[ERROR] Failed to load local settings or Terraform outputs: {error}")
        raise typer.Exit(code=1)

    host = outputs["public_ip"]
    key_path = settings["ssh"]["key_path"]
    user = settings["ssh"]["user"]

    typer.echo(f"[INFO] Target host: {host}")
    typer.echo("[INFO] Connecting via SSH...")

    try:
        with SSHClient(host=host, key_path=key_path, user=user) as ssh:
            typer.echo("[SUCCESS] SSH connected")

            for title, command in STATUS_COMMANDS:
                show_command_output(ssh, title=title, command=command)

            containers_out, _ = ssh.run("sudo docker ps --format '{{.Names}}'")
            if CONTAINER in containers_out.splitlines():
                show_command_output(
                    ssh,
                    title=f"Recent {CONTAINER} logs",
                    command=f"sudo docker logs --tail 40 {CONTAINER} 2>&1",
                )
            else:
                typer.echo(
                    f"\n[INFO] Skipping {CONTAINER} log output because the container is not running"
                )
    except Exception as error:
        typer.echo(f"[ERROR] Status collection failed: {error}")
        raise typer.Exit(code=1)

    ssh_command = outputs.get("ssh_command", f"ssh -i {key_path} {user}@{host}")

    typer.echo("\n[INFO] Recommended follow-up commands:")
    typer.echo(f"- {ssh_command} \"sudo journalctl -u docker -n 50 --no-pager\"")
    typer.echo(f"- {ssh_command} \"sudo docker logs --tail 100 {CONTAINER}\"")
    typer.echo(f"- {ssh_command} \"sudo docker inspect {CONTAINER}\"")
    typer.echo(f"- {ssh_command} \"sudo ss -tulpen\"")

    typer.echo("\n[SUCCESS] Status collection complete.")
