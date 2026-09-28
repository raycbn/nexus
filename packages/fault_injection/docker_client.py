import json
import subprocess
from dataclasses import dataclass

LAB_CONTAINER_NAME = "linux-lab-01"
POSTGRES_CONTAINER_NAME = "lab-postgres"
REDIS_CONTAINER_NAME = "lab-redis"
COMPOSE_FILE = "infrastructure/lab/compose.yml"


@dataclass
class DockerCommandResult:
    success: bool
    stdout: str
    stderr: str
    returncode: int


def _decode_output(value: bytes | str | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode(errors="replace")
    return value


def _run_docker_cmd(args: list[str], timeout: int = 30) -> DockerCommandResult:
    cmd = ["docker", *args]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return DockerCommandResult(
            success=result.returncode == 0,
            stdout=result.stdout.strip(),
            stderr=result.stderr.strip(),
            returncode=result.returncode,
        )
    except subprocess.TimeoutExpired as e:
        return DockerCommandResult(
            success=False,
            stdout=e.stdout or "",
            stderr=str(e),
            returncode=-1,
        )
    except Exception as e:
        return DockerCommandResult(
            success=False,
            stdout="",
            stderr=str(e),
            returncode=-1,
        )


def _run_compose_cmd(args: list[str], timeout: int = 120) -> DockerCommandResult:
    cmd = ["docker", "compose", "-f", COMPOSE_FILE, *args]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return DockerCommandResult(
            success=result.returncode == 0,
            stdout=result.stdout.strip(),
            stderr=result.stderr.strip(),
            returncode=result.returncode,
        )
    except subprocess.TimeoutExpired as e:
        return DockerCommandResult(
            success=False,
            stdout=e.stdout or "",
            stderr=str(e),
            returncode=-1,
        )
    except Exception as e:
        return DockerCommandResult(
            success=False,
            stdout="",
            stderr=str(e),
            returncode=-1,
        )


def get_container_status(container_name: str) -> str | None:
    result = _run_docker_cmd(["inspect", "--format={{.State.Status}}", container_name])
    if result.success:
        return result.stdout
    return None


def pause_container(container_name: str) -> DockerCommandResult:
    return _run_docker_cmd(["pause", container_name])


def unpause_container(container_name: str) -> DockerCommandResult:
    return _run_docker_cmd(["unpause", container_name])


def stop_container(container_name: str) -> DockerCommandResult:
    return _run_docker_cmd(["stop", container_name])


def start_container(container_name: str) -> DockerCommandResult:
    return _run_docker_cmd(["start", container_name])


def restart_container(container_name: str) -> DockerCommandResult:
    return _run_docker_cmd(["restart", container_name])


def is_container_running(container_name: str) -> bool:
    status = get_container_status(container_name)
    return status == "running"


def is_container_paused(container_name: str) -> bool:
    status = get_container_status(container_name)
    return status == "paused"


def get_compose_service_status() -> dict[str, str]:
    result = _run_compose_cmd(["ps", "--format=json"])
    if not result.success:
        return {}
    try:
        lines = result.stdout.strip().split("\n")
        status_map = {}
        for line in lines:
            if not line.strip():
                continue
            data = json.loads(line)
            name = data.get("Name", "")
            state = data.get("State", "")
            if name:
                status_map[name] = state
        return status_map
    except Exception:
        return {}


def check_lab_health() -> bool:
    import urllib.request

    try:
        with urllib.request.urlopen("http://localhost:8080/health", timeout=5) as resp:
            return resp.status == 200
    except Exception:
        return False
