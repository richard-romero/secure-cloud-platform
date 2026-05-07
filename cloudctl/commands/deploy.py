from pathlib import Path

import typer

from commands.common import run_terraform, wait_for_ssh_ready
from ssh.client import SSHClient, get_terraform_outputs, load_settings

app = typer.Typer()

BOOTSTRAP = Path(__file__).resolve().parents[1] / "scripts/bootstrap.sh"
IMAGE = "nginx:latest"
CONTAINER = "webapp"


def deploy_container(ssh: SSHClient) -> None:
    """Install Docker if needed and run the web container."""
    commands = [
        "if ! sudo systemctl list-unit-files | grep -q '^docker\\.service'; then sudo dnf install -y docker; fi",
        "sudo systemctl enable --now docker",
        f"sudo docker pull {IMAGE}",
        f"sudo docker rm -f {CONTAINER} >/dev/null 2>&1 || true",
        f"sudo docker run -d --name {CONTAINER} -p 80:80 --restart unless-stopped {IMAGE}",
    ]

    for command in commands:
        ssh.run(command, check=True)

    container_list, _ = ssh.run("sudo docker ps --format '{{.Names}}'", check=True)
    if CONTAINER not in container_list.splitlines():
        raise RuntimeError(f"Container '{CONTAINER}' is not running after deploy.")


@app.callback(invoke_without_command=True)
def deploy() -> None:
    """Provision infrastructure and deploy service."""
    try:
        settings = load_settings()
        ssh_allowed_cidr = settings.get("ssh", {}).get("allowed_cidr")

        typer.echo("[INFO] Initializing Terraform...")
        run_terraform(["terraform", "init"])

        typer.echo("[INFO] Applying infrastructure...")
        apply_command = ["terraform", "apply", "-auto-approve"]
        if ssh_allowed_cidr:
            apply_command.extend(["-var", f"ssh_allowed_cidr={ssh_allowed_cidr}"])
        run_terraform(apply_command)

        if not BOOTSTRAP.exists():
            raise FileNotFoundError(f"Bootstrap script was not found at {BOOTSTRAP}")

        outputs = get_terraform_outputs()

        host = outputs["public_ip"]
        key_path = settings["ssh"]["key_path"]
        user = settings["ssh"]["user"]
        remote_script = "/home/ec2-user/bootstrap.sh"

        typer.echo("[INFO] Waiting for SSH readiness...")
        wait_for_ssh_ready(host=host, key_path=key_path, user=user, logger=typer.echo)

        with SSHClient(host=host, key_path=key_path, user=user) as ssh:
            typer.echo("[INFO] Uploading bootstrap script...")
            ssh.upload(str(BOOTSTRAP), remote_script)

            typer.echo("[INFO] Executing bootstrap...")
            bootstrap_out, bootstrap_err = ssh.run(
                f"chmod +x {remote_script} && sudo {remote_script}",
                check=True,
            )
            if bootstrap_out:
                typer.echo(bootstrap_out.rstrip())
            if bootstrap_err:
                typer.echo(bootstrap_err.rstrip())

            typer.echo("[INFO] Deploying container...")
            deploy_container(ssh)

        typer.echo(f"[SUCCESS] Deployment complete. Instance public IP: {host}")
    except Exception as error:
        typer.echo(f"[ERROR] Deployment failed: {error}")
        raise typer.Exit(code=1)
