import json
from typing import Optional

import typer

from commands.common import CONTAINER
from ssh.client import SSHClient, get_terraform_outputs, load_settings

app = typer.Typer()
CURL_FLAGS = "-sS --max-time 5"

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
        "Listening ports (22/80/443)",
        "sudo ss -tuln | grep -E ':(22|80|443)[[:space:]]' || true",
    ),
    ("Memory usage", "free -h"),
    ("Disk usage", "df -h /"),
    ("Metrics endpoint", f"curl {CURL_FLAGS} http://localhost/metrics"),
]


def _parse_json_output(out: str) -> Optional[dict]:
    """Parse JSON from remote command output, returning None on failure."""
    text = out.strip()
    if not text:
        return None

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return None

    return data if isinstance(data, dict) else None


def _image_tag(image_ref: str) -> str:
    if ":" in image_ref:
        return image_ref.rsplit(":", 1)[-1]
    return image_ref


def show_deployment_summary(ssh: SSHClient) -> None:
    """Display deployment metadata and container health (informational only)."""
    typer.echo("\n[STATUS] Deployment summary")

    running_out, _ = ssh.run(
        f"sudo docker inspect -f '{{{{.State.Running}}}}' {CONTAINER} 2>/dev/null || true"
    )
    status_out, _ = ssh.run(
        f"sudo docker inspect -f '{{{{.State.Status}}}}' {CONTAINER} 2>/dev/null || true"
    )
    image_out, _ = ssh.run(
        f"sudo docker inspect {CONTAINER} --format='{{{{.Config.Image}}}}' 2>/dev/null || true"
    )

    is_running = running_out.strip() == "true"
    docker_status = status_out.strip() or "unavailable"

    health_out, _ = ssh.run(
        f"curl {CURL_FLAGS} http://localhost/health 2>/dev/null || true"
    )
    version_out, _ = ssh.run(
        f"curl {CURL_FLAGS} http://localhost/version 2>/dev/null || true"
    )

    health_data = _parse_json_output(health_out)
    version_data = _parse_json_output(version_out)

    app_health = health_data.get("status") if health_data else None
    if is_running and app_health == "healthy":
        container_health = f"{docker_status} / healthy"
    elif is_running:
        container_health = f"{docker_status} / {app_health or 'unhealthy'}"
    else:
        container_health = "not running"

    image_ref = image_out.strip()
    deployed_tag = _image_tag(image_ref) if image_ref else None
    running_version = version_data.get("version") if version_data else None
    deployed_at = version_data.get("deployed_at") if version_data else None
    commit = version_data.get("commit") if version_data else None

    if not deployed_tag and running_version:
        deployed_tag = running_version

    typer.echo(f"  Deployed image tag: {deployed_tag or 'unavailable'}")
    typer.echo(f"  Container health:   {container_health}")
    typer.echo(f"  Deployment time:    {deployed_at or 'unavailable'}")
    typer.echo(f"  Running version:    {running_version or 'unavailable'}")
    if commit:
        typer.echo(f"  Commit:               {commit}")


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
    """Collect operational status and host diagnostics from the target host."""
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

            show_deployment_summary(ssh)

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

    typer.echo("\n[INFO] Run 'cloudctl validate' for a pass/fail smoke test.")
    typer.echo("\n[SUCCESS] Status collection complete.")
