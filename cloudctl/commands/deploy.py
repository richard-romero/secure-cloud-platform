import typer
import subprocess
import time
from pathlib import Path
from ssh.client import SSHClient, get_terraform_outputs, load_settings

app = typer.Typer()

TERRAFORM_DIR = Path(__file__).resolve().parents[2] / "terraform"
BOOTSTRAP = Path(__file__).resolve().parents[1] / "scripts/bootstrap.sh"

IMAGE = "nginx:latest"
CONTAINER = "webapp"


def run(cmd):
    subprocess.run(cmd, cwd=TERRAFORM_DIR, check=True)


def wait_for_ssh_ready(host: str, key_path: str, user: str, retries: int = 20, delay: int = 10) -> None:
    """Wait for the instance SSH service to become reachable."""
    last_error = None
    for attempt in range(1, retries + 1):
        try:
            with SSHClient(host=host, key_path=key_path, user=user):
                return
        except Exception as error:  # pragma: no cover - network conditions are environment-specific.
            last_error = error
            if attempt == retries:
                break
            print(f"[INFO] SSH not ready yet ({attempt}/{retries}). Retrying in {delay}s...")
            time.sleep(delay)

    raise RuntimeError(f"SSH did not become ready for {host}: {last_error}")


def deploy_container(ssh: SSHClient, image: str = IMAGE, container: str = CONTAINER) -> tuple[str, str]:
    """Deploy (or redeploy) the application container on the target host."""
    commands = (
        "set -euo pipefail\n"
        "sudo systemctl start docker\n"
        f"sudo docker pull {image}\n"
        f"sudo docker rm -f {container} >/dev/null 2>&1 || true\n"
        f"sudo docker run -d --name {container} -p 80:80 --restart unless-stopped {image}\n"
    )
    return ssh.run(command=commands, check=True)


@app.callback(invoke_without_command=True)
def deploy():
    """Provision infrastructure and deploy service"""

    try:
        print("[INFO] Initializing Terraform...")
        run(["terraform", "init"])

        print("[INFO] Applying Infrastructure...")
        run(["terraform", "apply", "-auto-approve"])

        if not BOOTSTRAP.exists():
            raise FileNotFoundError(f"Bootstrap script was not found at {BOOTSTRAP}")

        outputs = get_terraform_outputs()
        settings = load_settings()

        host = outputs["public_ip"]
        key_path = settings["ssh"]["key_path"]
        user = settings["ssh"]["user"]

        print("[INFO] Waiting for SSH readiness...")
        wait_for_ssh_ready(host=host, key_path=key_path, user=user)

        remote_script = "/home/ec2-user/bootstrap.sh"

        with SSHClient(host=host, key_path=key_path, user=user) as ssh:
            print("[INFO] Uploading bootstrap script...")
            ssh.upload(str(BOOTSTRAP), remote_script)

            print("[INFO] Executing bootstrap...")
            bootstrap_out, bootstrap_err = ssh.run(
                f"chmod +x {remote_script} && sudo {remote_script}",
                check=True,
            )

            print("[INFO] Deploying container...")
            container_out, container_err = deploy_container(ssh)

        if bootstrap_out.strip():
            print(bootstrap_out.strip())
        if bootstrap_err.strip():
            print(bootstrap_err.strip())
        if container_out.strip():
            print(container_out.strip())
        if container_err.strip():
            print(container_err.strip())

        print(f"[SUCCESS] Deployment complete. Instance public IP: {host}")
    except Exception as error:
        print(f"[ERROR] Deployment failed: {error}")
        raise typer.Exit(code=1)