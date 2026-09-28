import asyncio
import json
from collections.abc import AsyncIterator
from uuid import uuid4

from packages.connectors.base import Connector
from packages.connectors.base.models import ConnectorCapabilities, HealthStatus, ReadResult
from packages.domain.exceptions import ConnectorAuthenticationError, ConnectorConnectionError
from packages.domain.models.resource import Resource
from packages.secrets import EnvironmentSecretProvider


class AWSConnector(Connector):
    """Read-only AWS connector backed by boto3 EC2 inventory."""

    _OPERATION_TIMEOUT_SECONDS = 30.0

    def __init__(self, resource: Resource, region: str, credential_ref: str) -> None:
        self._resource = resource
        self._region = region
        self._credential_ref = credential_ref
        self._secret_provider = EnvironmentSecretProvider()
        self._client = None

    @property
    def capabilities(self) -> ConnectorCapabilities:
        return ConnectorCapabilities(read=True, write=False, discover=True)

    async def connect(self, resource: Resource) -> None:
        try:
            credentials = json.loads(self._secret_provider.resolve(self._credential_ref))
            import boto3

            self._client = boto3.client(
                "ec2",
                region_name=self._region,
                aws_access_key_id=credentials["access_key_id"],
                aws_secret_access_key=credentials["secret_access_key"],
                aws_session_token=credentials.get("session_token"),
            )
            await self.health_check(resource)
        except TimeoutError as exc:
            raise ConnectorConnectionError("AWS connection timed out") from exc
        except (KeyError, ValueError, json.JSONDecodeError) as exc:
            raise ConnectorAuthenticationError("Invalid AWS credential payload") from exc
        except Exception as exc:
            message = str(exc)
            if any(
                marker in message.lower()
                for marker in ("credential", "accessdenied", "unauthorized")
            ):
                raise ConnectorAuthenticationError("AWS authentication failed") from exc
            raise ConnectorConnectionError(message) from exc

    async def disconnect(self, resource: Resource) -> None:
        self._client = None

    async def health_check(self, resource: Resource) -> HealthStatus:
        if self._client is None:
            return HealthStatus(healthy=False, message="not connected")
        try:
            identity = await asyncio.wait_for(
                asyncio.to_thread(self._client.describe_regions, RegionNames=[self._region]),
                timeout=self._OPERATION_TIMEOUT_SECONDS,
            )
            return HealthStatus(
                healthy=True,
                message="connected",
                details={"region": self._region, "regions": len(identity.get("Regions", []))},
            )
        except TimeoutError as exc:
            raise ConnectorConnectionError("AWS health check timed out") from exc
        except Exception as exc:
            raise ConnectorConnectionError(str(exc)) from exc

    async def discover(self, resource: Resource) -> AsyncIterator[Resource]:
        if self._client is None:
            raise ConnectorConnectionError("AWS connector is not connected")
        try:
            response = await asyncio.wait_for(
                asyncio.to_thread(self._client.describe_instances),
                timeout=self._OPERATION_TIMEOUT_SECONDS,
            )
        except TimeoutError as exc:
            raise ConnectorConnectionError("AWS discovery timed out") from exc
        except Exception as exc:
            raise ConnectorConnectionError(str(exc)) from exc
        for reservation in response.get("Reservations", []):
            for instance in reservation.get("Instances", []):
                instance_id = instance.get("InstanceId", "unknown")
                yield resource.model_copy(
                    update={
                        "id": uuid4(),
                        "parent_resource_id": resource.id,
                        "name": f"{resource.name}/{instance_id}",
                        "description": (
                            f"AWS EC2 instance ({instance.get('InstanceType', 'unknown')})"
                        ),
                        "labels": {
                            **resource.labels,
                            "instance_id": instance_id,
                            "state": str(instance.get("State", {}).get("Name", "unknown")),
                            "instance_type": str(instance.get("InstanceType", "")),
                        },
                    }
                )

    async def execute_read(self, resource: Resource, command: str) -> ReadResult:
        if self._client is None:
            raise ConnectorConnectionError("AWS connector is not connected")
        if command.strip() != "inventory":
            return ReadResult(
                success=False, error="Only the structured 'inventory' read is supported"
            )
        try:
            response = await asyncio.wait_for(
                asyncio.to_thread(self._client.describe_instances),
                timeout=self._OPERATION_TIMEOUT_SECONDS,
            )
        except TimeoutError as exc:
            raise ConnectorConnectionError("AWS inventory read timed out") from exc
        except Exception as exc:
            raise ConnectorConnectionError(str(exc)) from exc
        instances = [
            {
                "instance_id": instance.get("InstanceId"),
                "state": instance.get("State", {}).get("Name"),
                "instance_type": instance.get("InstanceType"),
            }
            for reservation in response.get("Reservations", [])
            for instance in reservation.get("Instances", [])
        ]
        return ReadResult(success=True, data=instances, metadata={"region": self._region})
