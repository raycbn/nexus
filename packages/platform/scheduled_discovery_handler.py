from uuid import UUID

from packages.connectors.factory import create_connector
from packages.persistence.repositories.core import CoreRepository
from packages.persistence.repositories.credentials import CredentialRepository
from packages.persistence.repositories.discovery import DiscoveryRunRepository
from packages.persistence.repositories.discovery_schedule import DiscoveryScheduleRepository
from packages.persistence.repositories.resource_connections import ResourceConnectionRepository
from packages.platform.job_types import DISCOVERY_SCHEDULE_JOB
from packages.platform.jobs import JobEnvelope
from packages.secrets import EnvironmentSecretProvider
from packages.secrets.credential_vault import CredentialVaultService


def _snapshot(resources: list) -> list[dict[str, object]]:
    return [
        {
            "id": str(item.id),
            "parent_resource_id": str(item.parent_resource_id) if item.parent_resource_id else None,
            "name": item.name,
            "resource_type": item.resource_type.value,
            "environment": item.environment,
            "description": item.description,
            "enabled": item.enabled,
            "labels": dict(item.labels),
        }
        for item in resources
    ]


class ScheduledDiscoveryHandler:
    def __init__(self, session) -> None:
        self._session = session
        self._schedules = DiscoveryScheduleRepository(session)
        self._resources = CoreRepository(session)
        self._bindings = ResourceConnectionRepository(session)
        self._credentials = CredentialRepository(session)
        self._runs = DiscoveryRunRepository(session)
        self._vault = None

    async def __call__(self, envelope: JobEnvelope) -> bool:
        if envelope.job_type != DISCOVERY_SCHEDULE_JOB:
            return False
        schedule_id = UUID(envelope.payload["schedule_id"])
        resource_id = UUID(envelope.payload["resource_id"])
        schedule = await self._schedules.get_by_id(schedule_id)
        organization_id = UUID(envelope.payload["organization_id"])
        if schedule is None or schedule.organization_id != organization_id:
            return False
        if resource_id != schedule.resource_id or not schedule.enabled:
            return False
        resource = await self._resources.get_resource(
            schedule.organization_id, resource_id, schedule.workspace_id
        )
        binding = await self._bindings.get(
            schedule.organization_id, resource_id, schedule.workspace_id
        )
        if resource is None or binding is None:
            return False
        credential = await self._credentials.get(
            schedule.organization_id, binding.credential_id, schedule.workspace_id
        )
        if credential is None or not credential.enabled:
            return False
        config = dict(binding.config)
        if credential.secret_ref:
            secret = EnvironmentSecretProvider().resolve(credential.secret_ref)
        else:
            if self._vault is None:
                self._vault = CredentialVaultService(self._session)
            secret = await self._vault.resolve(credential.id)
        if binding.connector_key == "kubernetes":
            config["kubeconfig_ref"] = credential.secret_ref or secret
        elif binding.connector_key in {"aws", "azure", "gcp"}:
            config["credential_ref"] = credential.secret_ref or secret
        elif binding.connector_key in {"linux", "windows"}:
            config["auth_ref"] = secret
        elif binding.connector_key in {"postgresql", "sql_server", "vmware"}:
            config["password"] = secret
        connector = create_connector(resource, **config)
        run = await self._runs.create(
            schedule.organization_id, schedule.workspace_id, resource_id, binding.connector_key
        )
        try:
            await connector.connect(resource)
            discovered = [item async for item in connector.discover(resource)]
            await self._runs.complete(run, status="completed", snapshot=_snapshot(discovered))
            await self._session.commit()
            return True
        except Exception:
            await self._runs.complete(run, status="failed", snapshot=[])
            await self._session.commit()
            raise
        finally:
            await connector.disconnect(resource)
