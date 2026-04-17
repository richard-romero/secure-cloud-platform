import subprocess
import time
from pathlib import Path

from ssh.client import SSHClient

TERRAFORM_DIR = Path(__file__).resolve().parents[2] / "terraform"


def run_terraform(command: list[str]) -> None:
    """Run a Terraform command in the project Terraform directory."""
    subprocess.run(command, cwd=TERRAFORM_DIR, check=True)


def wait_for_ssh_ready(
    host: str,
    key_path: str,
    user: str,
    retries: int = 20,
    delay: int = 10,
    logger=print,
) -> None:
    """Keep trying SSH until the target host becomes reachable."""
    last_error = None

    for attempt in range(1, retries + 1):
        try:
            with SSHClient(host=host, key_path=key_path, user=user):
                return
        except Exception as error:  # pragma: no cover - network conditions are environment-specific.
            last_error = error
            if attempt == retries:
                break
            logger(f"[INFO] SSH not ready yet ({attempt}/{retries}). Retrying in {delay}s...")
            time.sleep(delay)

    raise RuntimeError(f"SSH did not become ready for {host}: {last_error}")
