from types import SimpleNamespace
from uuid import uuid4

from packages.domain.models.resource import Resource
from packages.remediation.autonomous_service import autonomous_preflight


def resource(environment="lab"):
    return Resource(
        organization_id=uuid4(), workspace_id=uuid4(), name="preflight",
        resource_type="linux_server", environment=environment,
    )


def connector(write=True):
    return SimpleNamespace(capabilities=SimpleNamespace(write=write))


def test_dry_run_does_not_require_write():
    result = autonomous_preflight(connector(False), resource(), dry_run=True)
    assert result.allowed is True


def test_non_lab_is_blocked():
    result = autonomous_preflight(connector(True), resource("production"), dry_run=False)
    assert result.allowed is False
    assert "lab" in result.reason


def test_write_capability_is_required(monkeypatch):
    monkeypatch.setattr(
        "packages.remediation.autonomous_service.check_kill_switch",
        lambda: SimpleNamespace(allowed=True, reason=None),
    )
    result = autonomous_preflight(connector(False), resource(), dry_run=False)
    assert result.allowed is False
    assert "write capability" in result.reason
