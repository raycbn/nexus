import pytest
from packages.remediation.retry_policy import RetryPolicy


def test_retry_policy_converts_attempts_to_retries():
    assert RetryPolicy(max_attempts=3).max_retries == 2


def test_retry_policy_uses_exponential_backoff():
    policy = RetryPolicy(max_attempts=5, base_delay_seconds=1, max_delay_seconds=5)
    assert [policy.delay_for_retry(i) for i in range(1, 5)] == [1, 2, 4, 5]


def test_retry_policy_rejects_invalid_attempt_count():
    with pytest.raises(ValueError, match="max_attempts"):
        RetryPolicy(max_attempts=0)


def test_retry_policy_rejects_invalid_retry_number():
    with pytest.raises(ValueError, match="retry_number"):
        RetryPolicy().delay_for_retry(0)
