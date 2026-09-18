import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

LAB_DIR = Path(__file__).resolve().parent.parent
COMPOSE_FILE = LAB_DIR / "compose.yml"


def _run(cmd, timeout=30):
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    return result


def _compose(*args):
    return _run(["docker", "compose", "-f", str(COMPOSE_FILE), *args], timeout=120)


@pytest.mark.live
class TestLabDocker:
    @pytest.fixture(autouse=True, scope="module")
    def setup(self):
        _compose("up", "-d")
        max_wait = 120
        start = time.time()
        while time.time() - start < max_wait:
            result = _compose("ps")
            if result.returncode == 0 and "Up" in result.stdout and "linux-lab-01" in result.stdout:
                break
            time.sleep(2)
        max_wait = 60
        start = time.time()
        while time.time() - start < max_wait:
            try:
                urllib.request.urlopen("http://localhost:8080/api/status", timeout=5)
                break
            except Exception:
                time.sleep(2)
        yield
        _compose("down")

    def test_containers_running(self):
        result = _compose("ps")
        assert result.returncode == 0
        assert "linux-lab-01" in result.stdout
        assert "postgres" in result.stdout
        assert "redis" in result.stdout

    def test_health_endpoint(self):
        for _ in range(20):
            try:
                resp = urllib.request.urlopen("http://localhost:8080/health", timeout=5)
                data = json.loads(resp.read())
                assert data["status"] == "healthy"
                break
            except Exception:
                time.sleep(2)
        else:
            pytest.fail("Health endpoint did not respond")

    def test_api_status(self):
        for _ in range(20):
            try:
                resp = urllib.request.urlopen("http://localhost:8080/api/status", timeout=5)
                data = json.loads(resp.read())
                assert data["status"] == "running"
                break
            except Exception:
                time.sleep(2)
        else:
            pytest.fail("API status endpoint did not respond correctly")

    def test_slow_endpoint(self):
        for _ in range(20):
            try:
                start = time.time()
                resp = urllib.request.urlopen(
                    "http://localhost:8080/api/slow?seconds=2", timeout=10
                )
                elapsed = time.time() - start
                data = json.loads(resp.read())
                assert data["status"] == "completed"
                assert elapsed >= 1.5
                break
            except Exception:
                time.sleep(2)
        else:
            pytest.fail("Slow endpoint did not respond correctly")

    def test_error_endpoint(self):
        http_error = None
        for _ in range(20):
            try:
                urllib.request.urlopen("http://localhost:8080/api/error", timeout=5)
                pytest.fail("Expected HTTPError was not raised")
            except urllib.error.HTTPError as e:
                http_error = e
                if e.code == 500:
                    break
                time.sleep(2)
        else:
            pytest.fail("Error endpoint did not return 500")
        assert http_error.code == 500, f"Expected status 500, got {http_error.code}"
        body = http_error.read().decode("utf-8")
        data = json.loads(body)
        assert "error" in data
        assert "code" in data
        assert data["code"] == "LAB_ERROR_001"

    def test_db_connectivity(self):
        for _ in range(20):
            try:
                resp = urllib.request.urlopen("http://localhost:8080/api/db", timeout=10)
                data = json.loads(resp.read())
                assert data.get("connected") is True
                break
            except Exception:
                time.sleep(2)
        else:
            pytest.fail("DB connectivity test failed")

    def test_redis_connectivity(self):
        for _ in range(20):
            try:
                resp = urllib.request.urlopen("http://localhost:8080/api/redis", timeout=10)
                data = json.loads(resp.read())
                assert data.get("connected") is True
                break
            except Exception:
                time.sleep(2)
        else:
            pytest.fail("Redis connectivity test failed")
