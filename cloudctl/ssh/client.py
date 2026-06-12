import json
import subprocess
from pathlib import Path

import paramiko
import yaml

BASE_DIR = Path(__file__).resolve().parents[2]
TERRAFORM_DIR = BASE_DIR / "terraform"
CONFIG_PATH = BASE_DIR / "cloudctl/config/settings.yaml"


def load_settings() -> dict:
    """Load settings from config/settings.yaml."""
    with open(CONFIG_PATH, "r", encoding="utf-8") as config_file:
        return yaml.safe_load(config_file)


def get_terraform_outputs() -> dict:
    """Read Terraform outputs and return fields used by command modules."""
    try:
        result = subprocess.run(
            ["terraform", "output", "-json"],
            cwd=TERRAFORM_DIR,
            capture_output=True,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError as error:
        raise RuntimeError(f"Failed to fetch Terraform outputs: {error}") from error

    try:
        raw_outputs = json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise RuntimeError(f"Terraform output is not valid JSON: {error}") from error

    try:
        return {
            "public_ip": raw_outputs["instance_public_ip"]["value"],
            "instance_id": raw_outputs["instance_id"]["value"],
            "region": raw_outputs["configured_region"]["value"],
            "ssh_command": raw_outputs["ssh_command"]["value"],
        }
    except (KeyError, TypeError) as error:
        raise RuntimeError(f"Terraform outputs are missing required fields: {error}") from error


class SSHClient:
    """A context-managed SSH client wrapper using Paramiko."""

    def __init__(self, host: str, key_path: str, user: str = "ec2-user") -> None:
        self.host = host
        self.user = user
        self.key_path = str(Path(key_path).expanduser())
        self.client: paramiko.SSHClient | None = None

    def connect(self) -> None:
        """Establish the SSH connection to the remote host."""
        key = self._load_private_key()

        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        self.client.connect(
            hostname=self.host,
            username=self.user,
            pkey=key,
            timeout=10,
        )

    def _load_private_key(self):
        """Load the SSH private key using a supported Paramiko key class."""
        key_types = (
            paramiko.Ed25519Key,
            paramiko.RSAKey,
            paramiko.ECDSAKey,
        )

        last_error = None
        for key_type in key_types:
            try:
                return key_type.from_private_key_file(self.key_path)
            except (paramiko.SSHException, ValueError, TypeError) as error:
                last_error = error

        raise paramiko.SSHException(
            f"Unable to load SSH private key from {self.key_path}: {last_error}"
        )

    def run(self, command: str, check: bool = False) -> tuple[str, str]:
        """Execute a command on the remote host and return (stdout, stderr)."""
        if self.client is None:
            raise RuntimeError("SSH Client is not connected. Call .connect() first.")

        _, stdout, stderr = self.client.exec_command(command)

        stdout_text = stdout.read().decode()
        stderr_text = stderr.read().decode()
        exit_code = stdout.channel.recv_exit_status()

        if check and exit_code != 0:
            details = []
            if stdout_text.strip():
                details.append(stdout_text.rstrip())
            if stderr_text.strip():
                details.append(stderr_text.rstrip())
            output = "\n".join(details)
            raise RuntimeError(
                f"Remote command failed with exit code {exit_code}: {command}"
                + (f"\n{output}" if output else "")
            )

        return stdout_text, stderr_text

    def upload(self, local_path: str, remote_path: str) -> None:
        """Upload a local file to the remote host over SFTP."""
        if not self.client:
            raise RuntimeError("SSH Client is not connected. Call .connect() first.")

        source_path = Path(local_path).expanduser().resolve()
        if not source_path.exists() or not source_path.is_file():
            raise FileNotFoundError(f"Local file not found: {source_path}")

        with self.client.open_sftp() as sftp:
            sftp.put(str(source_path), remote_path)
    
    def close(self) -> None:
        """Close the SSH connection safely."""
        if self.client:
            self.client.close()
            self.client = None

    def __enter__(self):
        """Allow the client to be used as a context manager."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Ensure connection is closed when the context manager exits."""
        self.close()