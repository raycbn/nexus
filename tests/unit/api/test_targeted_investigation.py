from uuid import uuid4

import pytest
from apps.api.models import InvestigationCreateDTO
from apps.api.services.targeted_investigation_service import (
    TargetedInvestigationApplicationService,
)
from packages.domain.models.context import TenantContext
from packages.domain.models.resource import Resource


class FakeCoreRepository:
    def __init__(self, resource):
        self.resource = resource
        self.requested_ids = []

    async def get_resource(self, organization_id, resource_id, workspace_id=None):
        self.requested_ids.append(resource_id)
        if resource_id == self.resource.id:
            return self.resource
        return None


def test_targeted_create_dto_accepts_resource_id():
    resource_id = uuid4()
    dto = InvestigationCreateDTO(objective="check service", resource_id=resource_id)
    assert dto.resource_id == resource_id


@pytest.mark.asyncio
async def test_targeted_service_uses_selected_resource():
    organization_id = uuid4()
    workspace_id = uuid4()
    resource = Resource(
        organization_id=organization_id,
        workspace_id=workspace_id,
        name="target",
        resource_type="linux_server",
        environment="lab",
        labels={"service": "nginx", "ssh_port": "2223"},
    )
    tenant = TenantContext(
        user_id=uuid4(),
        organization_id=organization_id,
        workspace_id=workspace_id,
        role="operator",
    )
    service = TargetedInvestigationApplicationService(
        tenant_context=tenant,
        session=None,
        resource_id=resource.id,
    )
    fake = FakeCoreRepository(resource)
    service._core_repository = fake

    selected = await service._get_or_create_resource()

    assert selected.id == resource.id
    assert fake.requested_ids == [resource.id]


@pytest.mark.asyncio
async def test_targeted_service_rejects_missing_resource():
    organization_id = uuid4()
    workspace_id = uuid4()
    resource = Resource(
        organization_id=organization_id,
        workspace_id=workspace_id,
        name="target",
        resource_type="linux_server",
        environment="lab",
    )
    tenant = TenantContext(
        user_id=uuid4(), organization_id=organization_id,
        workspace_id=workspace_id, role="operator",
    )
    service = TargetedInvestigationApplicationService(
        tenant_context=tenant, session=None, resource_id=uuid4()
    )
    service._core_repository = FakeCoreRepository(resource)

    with pytest.raises(ValueError, match="resource not found"):
        await service._get_or_create_resource()


@pytest.mark.asyncio
async def test_targeted_service_rejects_disabled_resource():
    organization_id = uuid4()
    resource = Resource(
        organization_id=organization_id,
        name="disabled",
        resource_type="linux_server",
        environment="lab",
        enabled=False,
    )
    tenant = TenantContext(
        user_id=uuid4(), organization_id=organization_id,
        workspace_id=None, role="operator",
    )
    service = TargetedInvestigationApplicationService(
        tenant_context=tenant, session=None, resource_id=resource.id
    )
    service._core_repository = FakeCoreRepository(resource)
    with pytest.raises(ValueError, match="resource not found or disabled"):
        await service._get_or_create_resource()



