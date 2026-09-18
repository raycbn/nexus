import os
import subprocess
import sys

import yaml

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

LAB_DIR = os.path.join(os.path.dirname(__file__), "..")


def _lab_path(*parts):
    return os.path.join(LAB_DIR, *parts)


def test_compose_yaml_valid():
    path = _lab_path("compose.yml")
    with open(path) as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict)
    assert "services" in data
    services = data["services"]
    assert "linux-lab-01" in services
    assert "postgres" in services
    assert "redis" in services


def test_compose_services_have_required_fields():
    path = _lab_path("compose.yml")
    with open(path) as f:
        data = yaml.safe_load(f)
    services = data["services"]

    for name in ["linux-lab-01", "postgres", "redis"]:
        assert name in services
        svc = services[name]
        assert "image" in svc or "build" in svc

    lab = services["linux-lab-01"]
    assert "ports" in lab
    assert "2222:22" in [str(p) for p in lab["ports"]]
    assert "8080:80" in [str(p) for p in lab["ports"]]
    assert "depends_on" in lab
    assert "postgres" in lab["depends_on"]
    assert "redis" in lab["depends_on"]
    assert "healthcheck" in lab
    assert "deploy" in lab
    assert "resources" in lab["deploy"]

    pg = services["postgres"]
    assert pg["image"] == "postgres:16-alpine"
    assert "POSTGRES_USER" in pg["environment"]
    assert "POSTGRES_PASSWORD" in pg["environment"]
    assert "POSTGRES_DB" in pg["environment"]
    assert "healthcheck" in pg

    r = services["redis"]
    assert r["image"] == "redis:7-alpine"
    assert "healthcheck" in r


def test_compose_has_network():
    path = _lab_path("compose.yml")
    with open(path) as f:
        data = yaml.safe_load(f)
    assert "networks" in data
    assert "lab-network" in data["networks"]
    assert data["networks"]["lab-network"]["driver"] == "bridge"


def test_compose_has_volumes():
    path = _lab_path("compose.yml")
    with open(path) as f:
        data = yaml.safe_load(f)
    assert "volumes" in data


def test_dockerfile_exists():
    path = _lab_path("linux-lab", "Dockerfile")
    assert os.path.isfile(path)


def test_dockerfile_based_on_ubuntu():
    path = _lab_path("linux-lab", "Dockerfile")
    with open(path) as f:
        content = f.read()
    assert "ubuntu:24.04" in content


def test_dockerfile_installs_required_packages():
    path = _lab_path("linux-lab", "Dockerfile")
    with open(path) as f:
        content = f.read()
    required = [
        "openssh-server",
        "nginx",
        "python3",
        "python3-pip",
        "procps",
        "iproute2",
        "curl",
        "net-tools",
        "lsof",
        "ca-certificates",
    ]
    for pkg in required:
        assert pkg in content, f"Missing package: {pkg}"


def test_dockerfile_creates_nexus_user():
    path = _lab_path("linux-lab", "Dockerfile")
    with open(path) as f:
        content = f.read()
    assert "nexus" in content


def test_dockerfile_has_healthcheck():
    path = _lab_path("linux-lab", "Dockerfile")
    with open(path) as f:
        content = f.read()
    assert "HEALTHCHECK" in content


def test_entrypoint_sh_exists():
    path = _lab_path("linux-lab", "entrypoint.sh")
    assert os.path.isfile(path)


def test_entrypoint_sh_starts_sshd():
    path = _lab_path("linux-lab", "entrypoint.sh")
    with open(path) as f:
        content = f.read()
    assert "sshd" in content


def test_entrypoint_sh_starts_nginx():
    path = _lab_path("linux-lab", "entrypoint.sh")
    with open(path) as f:
        content = f.read()
    assert "nginx" in content


def test_entrypoint_sh_starts_api():
    path = _lab_path("linux-lab", "entrypoint.sh")
    with open(path) as f:
        content = f.read()
    assert "python3" in content or "app.py" in content


def test_entrypoint_sh_is_shell():
    path = _lab_path("linux-lab", "entrypoint.sh")
    with open(path) as f:
        content = f.read()
    assert content.startswith("#!/bin/bash")


def test_nginx_conf_exists():
    path = _lab_path("config", "nginx.conf")
    assert os.path.isfile(path)


def test_nginx_conf_has_health_endpoint():
    path = _lab_path("config", "nginx.conf")
    with open(path) as f:
        content = f.read()
    assert "/health" in content
    assert "proxy_pass" in content


def test_api_py_exists():
    path = _lab_path("config", "api.py")
    assert os.path.isfile(path)


def test_api_has_health_endpoint():
    path = _lab_path("config", "api.py")
    with open(path) as f:
        content = f.read()
    assert "/health" in content or "health" in content


def test_api_has_required_endpoints():
    path = _lab_path("config", "api.py")
    with open(path) as f:
        content = f.read()
    endpoints = ["/api/status", "/api/slow", "/api/error", "/api/db", "/api/redis"]
    for ep in endpoints:
        assert ep in content, f"Missing endpoint: {ep}"


def test_api_has_slow_and_error():
    path = _lab_path("config", "api.py")
    with open(path) as f:
        content = f.read()
    assert "sleep" in content or "time.sleep" in content
    assert "500" in content


def test_api_has_db_and_redis():
    path = _lab_path("config", "api.py")
    with open(path) as f:
        content = f.read()
    assert "postgres" in content.lower() or "psycopg" in content
    assert "redis" in content.lower()


def test_requirements_txt_exists():
    path = _lab_path("config", "requirements.txt")
    assert os.path.isfile(path)


def test_requirements_has_db_and_cache():
    path = _lab_path("config", "requirements.txt")
    with open(path) as f:
        content = f.read().lower()
    assert "psycopg" in content
    assert "redis" in content


def test_gitignore_prevents_key_commit():
    path = _lab_path(".gitignore")
    with open(path) as f:
        content = f.read()
    assert "ssh" in content or "id_" in content or "key" in content.lower()


def test_ssh_config_exists():
    path = _lab_path("linux-lab", "ssh", "sshd_config")
    assert os.path.isfile(path)


def test_ssh_config_disables_password():
    path = _lab_path("linux-lab", "ssh", "sshd_config")
    with open(path) as f:
        content = f.read()
    assert "PasswordAuthentication no" in content
    assert "PubkeyAuthentication yes" in content


def test_compose_ports_not_host_default():
    path = _lab_path("compose.yml")
    with open(path) as f:
        data = yaml.safe_load(f)
    lab = data["services"]["linux-lab-01"]
    port_strings = [str(p) for p in lab["ports"]]
    assert "2222:22" in port_strings, "SSH should map host 2222 to container 22"
    assert "8080:80" in port_strings, "HTTP should map host 8080 to container 80"


def test_compose_volume_uses_staging_path():
    path = _lab_path("compose.yml")
    with open(path) as f:
        data = yaml.safe_load(f)
    lab = data["services"]["linux-lab-01"]
    volumes = lab["volumes"]
    for vol in volumes:
        if (
            isinstance(vol, dict)
            and "target" in vol
            and "authorized_keys" in str(vol.get("target", ""))
        ):
            assert vol["target"] == "/run/nexus/authorized_keys", (
                f"authorized_keys should mount to staging path "
                f"/run/nexus/authorized_keys, got {vol['target']}"
            )
            assert vol.get("read_only") is True, "authorized_keys mount should be read-only"


def test_entrypoint_stages_authorized_keys():
    path = _lab_path("linux-lab", "entrypoint.sh")
    with open(path) as f:
        content = f.read()
    assert "/run/nexus/authorized_keys" in content
    assert "/home/nexus/.ssh/authorized_keys" in content
    assert "cp " in content and "authorized_keys" in content
    assert "nexus:nexus" in content
    assert "chmod 600" in content
    assert "chmod 700" in content


def test_entrypoint_fails_if_staged_key_missing():
    path = _lab_path("linux-lab", "entrypoint.sh")
    with open(path) as f:
        content = f.read()
    assert "/run/nexus/authorized_keys" in content
    assert "ERROR" in content and "authorized_keys" in content


def test_private_key_never_in_dockerfile_or_compose():
    dockerfile = _lab_path("linux-lab", "Dockerfile")
    compose = _lab_path("compose.yml")
    with open(dockerfile) as f:
        docker_content = f.read()
    with open(compose) as f:
        compose_content = f.read()
    for name, content in [("Dockerfile", docker_content), ("compose.yml", compose_content)]:
        assert "ssh_key" not in content, f"Private key reference found in {name}"
        assert "id_rsa" not in content, f"Private key reference found in {name}"
        assert "id_ed25519" not in content, f"Private key reference found in {name}"


def test_gitignore_prevents_ssh_key():
    path = _lab_path(".gitignore")
    with open(path) as f:
        content = f.read()
    assert "ssh_key" in content, "ssh_key not in .gitignore"
    assert "ssh_key.pub" in content, "ssh_key.pub not in .gitignore"


def test_gitignore_prevents_authorized_keys():
    path = _lab_path(".gitignore")
    with open(path) as f:
        content = f.read()
    assert "authorized_keys" in content, "authorized_keys not in .gitignore"


def test_authorized_keys_example_exists():
    path = _lab_path("linux-lab", "ssh", "authorized_keys.example")
    assert os.path.isfile(path), "authorized_keys.example does not exist"


def test_authorized_keys_example_is_placeholder():
    path = _lab_path("linux-lab", "ssh", "authorized_keys.example")
    with open(path) as f:
        content = f.read()
    assert "example" in content.lower() or "template" in content.lower(), (
        "authorized_keys.example should indicate it is a placeholder"
    )
    assert "ssh-ed25519 AAAA" not in content, (
        "authorized_keys.example should not contain a real key"
    )


def test_real_authorized_keys_is_gitignored():
    path = _lab_path("linux-lab", "ssh", "authorized_keys")
    result = subprocess.run(
        ["git", "check-ignore", str(path)],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, "authorized_keys is not gitignored"
