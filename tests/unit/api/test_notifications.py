from apps.api.routes.notifications import PROVIDERS, _payload


def test_supported_notification_providers() -> None:
    assert {"webhook", "slack", "teams", "pagerduty", "opsgenie"} == PROVIDERS


def test_slack_payload_is_provider_aware() -> None:
    payload = _payload("slack", "incident.created", {"message": "Database is slow"})
    assert payload["text"] == "NEXUS incident.created: Database is slow"


def test_webhook_payload_is_passthrough() -> None:
    source = {"title": "test", "severity": "high"}
    assert _payload("webhook", "incident.created", source) == source
