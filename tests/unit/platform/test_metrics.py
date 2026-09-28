import pytest
from packages.platform.metrics import MetricsRegistry, _normalize


def test_increment_and_snapshot_are_deterministic() -> None:
    registry = MetricsRegistry()
    registry.increment("remediation.success")
    registry.increment("remediation.success", 2)
    assert registry.snapshot() == {"remediation.success": 3}


def test_negative_increment_is_rejected() -> None:
    with pytest.raises(ValueError):
        MetricsRegistry().increment("x", -1)


def test_prometheus_format_and_name_normalization() -> None:
    registry = MetricsRegistry()
    registry.increment("remediation.success")
    assert _normalize("remediation.success") == "nexus_remediation_success"
    assert "# TYPE nexus_remediation_success counter" in registry.prometheus()
    assert "nexus_remediation_success 1" in registry.prometheus()
