import asyncio
import json
from collections.abc import AsyncIterator
from uuid import uuid4

from packages.connectors.base import Connector
from packages.connectors.base.models import ConnectorCapabilities, HealthStatus, ReadResult
from packages.domain.exceptions import ConnectorAuthenticationError, ConnectorConnectionError
from packages.domain.models.resource import Resource
from packages.secrets import EnvironmentSecretProvider


class GCPConnector(Connector):
    """Read-only Google Cloud Compute Engine connector."""

    _OPERATION_TIMEOUT_SECONDS = 30.0

    def __init__(self, resource: Resource, project_id: str, credential_ref: str) -> None:
        self._resource = resource
        self._project_id = project_id
        self._credential_ref = credential_ref
        self._secret_provider = EnvironmentSecretProvider()
        self._client = None
        self._credentials = None

    @property
    def capabilities(self) -> ConnectorCapabilities:
        return ConnectorCapabilities(read=True, write=False, discover=True)

    async def connect(self, resource: Resource) -> None:
        try:
            from google.cloud import compute_v1
            from google.oauth2 import service_account

            payload = json.loads(self._secret_provider.resolve(self._credential_ref))
            self._credentials = service_account.Credentials.from_service_account_info(payload)
            self._client = compute_v1.InstancesClient(credentials=self._credentials)
            await self.health_check(resource)
        except (KeyError, ValueError, json.JSONDecodeError) as exc:
            raise ConnectorAuthenticationError("Invalid GCP service account payload") from exc
        except TimeoutError as exc:
            raise ConnectorConnectionError("GCP connection timed out") from exc
        except Exception as exc:
            if any(
                marker in str(exc).lower()
                for marker in ("credential", "unauthorized", "permission denied", "authentication")
            ):
                raise ConnectorAuthenticationError("GCP authentication failed") from exc
            raise ConnectorConnectionError(str(exc)) from exc

    async def disconnect(self, resource: Resource) -> None:
        self._client = None
        self._credentials = None

    async def health_check(self, resource: Resource) -> HealthStatus:
        if self._client is None:
            return HealthStatus(healthy=False, message="not connected")
        return HealthStatus(
            healthy=True, message="connected", details={"project_id": self._project_id}
        )

    async def discover(self, resource: Resource) -> AsyncIterator[Resource]:
        if self._client is None:
            raise ConnectorConnectionError("GCP connector is not connected")
        try:
            request = self._client.aggregated_list(request={"project": self._project_id})
            pages = await asyncio.wait_for(
                asyncio.to_thread(lambda: list(request)), timeout=self._OPERATION_TIMEOUT_SECONDS
            )
        except TimeoutError as exc:
            raise ConnectorConnectionError("GCP discovery timed out") from exc
        except Exception as exc:
            raise ConnectorConnectionError(str(exc)) from exc
        for _scope, response in pages:
            for instance in getattr(response, "instances", []) or []:
                yield resource.model_copy(
                    update={
                        "id": uuid4(),
                        "parent_resource_id": resource.id,
                        "name": f"{resource.name}/{instance.name}",
                        "description": f"GCP Compute Engine instance ({instance.machine_type})",
                        "labels": {
                            **resource.labels,
                            "instance_id": str(instance.id),
                            "zone": str(instance.zone),
                            "status": str(instance.status),
                        },
                    }
                )

    async def execute_read(self, resource: Resource, command: str) -> ReadResult:
        if self._client is None:
            raise ConnectorConnectionError("GCP connector is not connected")
        if command.strip() != "inventory":
            return ReadResult(
                success=False, error="Only the structured 'inventory' read is supported"
            )
        try:
            request = self._client.aggregated_list(request={"project": self._project_id})
            pages = await asyncio.wait_for(
                asyncio.to_thread(lambda: list(request)), timeout=self._OPERATION_TIMEOUT_SECONDS
            )
        except TimeoutError as exc:
            raise ConnectorConnectionError("GCP inventory read timed out") from exc
        except Exception as exc:
            raise ConnectorConnectionError(str(exc)) from exc
        data = []
        for _, response in pages:
            for instance in getattr(response, "instances", []) or []:
                data.append(
                    {"name": instance.name, "id": str(instance.id), "status": str(instance.status)}
                )
        return ReadResult(success=True, data=data, metadata={"project_id": self._project_id})
