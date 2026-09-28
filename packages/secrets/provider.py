import os
from abc import ABC, abstractmethod


class SecretProvider(ABC):
    """Resolve secret references without exposing secret values to domain models."""

    @abstractmethod
    def resolve(self, secret_ref: str) -> str:
        """Resolve a provider-specific reference to a secret value."""


class EnvironmentSecretProvider(SecretProvider):
    """Development/local provider backed by process environment variables."""

    def resolve(self, secret_ref: str) -> str:
        if not secret_ref:
            raise ValueError("Secret reference is required")
        value = os.environ.get(secret_ref)
        if not value:
            raise ValueError("Secret reference could not be resolved")
        return value
