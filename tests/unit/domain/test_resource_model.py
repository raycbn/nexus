from uuid import uuid4

from packages.domain.models.enums import ResourceType
from packages.domain.models.resource import Resource


def test_resource_supports_parent_hierarchy():
    parent_id = uuid4()
    resource = Resource(
        organization_id=uuid4(),
        workspace_id=uuid4(),
        parent_resource_id=parent_id,
        name="nginx",
        resource_type=ResourceType.SERVICE,
    )

    assert resource.parent_resource_id == parent_id
    assert resource.resource_type == ResourceType.SERVICE


def test_resource_supports_application_and_database_types():
    assert ResourceType.APPLICATION.value == "application"
    assert ResourceType.DATABASE.value == "database"
