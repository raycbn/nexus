from uuid import uuid4

import pytest
from packages.domain.models.enums import ResourceType
from packages.domain.models.resource import Resource
from packages.domain.resource_graph import ResourceGraph


def make_resource(name, parent=None):
    return Resource(
        organization_id=uuid4(), name=name, resource_type=ResourceType.LINUX_SERVER,
        parent_resource_id=parent,
    )


def test_resource_graph_expands_lineage_ids_without_duplicates():
    host = make_resource("host")
    service = make_resource("service", host.id)
    graph = ResourceGraph([host, service])

    assert graph.expand_lineage_ids([service.id, host.id]) == [service.id, host.id]


def test_resource_graph_rejects_foreign_scope():
    organization_id = uuid4()
    resource = Resource(
        organization_id=uuid4(), name="foreign", resource_type=ResourceType.LINUX_SERVER
    )
    graph = ResourceGraph([resource])

    with pytest.raises(ValueError, match="foreign organization"):
        graph.validate_scope(organization_id, None)


def test_resource_graph_lists_children():
    host = make_resource("host")
    nginx = make_resource("nginx", host.id)
    api = make_resource("api", host.id)
    graph = ResourceGraph([host, nginx, api])

    assert [item.name for item in graph.children(host.id)] == ["nginx", "api"]


def test_resource_graph_lists_descendants_breadth_first():
    host = make_resource("host")
    nginx = make_resource("nginx", host.id)
    api = make_resource("api", nginx.id)
    worker = make_resource("worker", host.id)
    graph = ResourceGraph([host, nginx, api, worker])

    assert [item.name for item in graph.descendants(host.id)] == ["nginx", "worker", "api"]


def test_resource_graph_returns_topology():
    host = make_resource("host")
    service = make_resource("nginx", host.id)
    app = make_resource("api", service.id)
    graph = ResourceGraph([host, service, app])

    assert [item.name for item in graph.topology(host.id)] == ["host", "nginx", "api"]


def test_resource_graph_lists_roots():
    first = make_resource("first")
    child = make_resource("child", first.id)
    second = make_resource("second")
    graph = ResourceGraph([first, child, second])

    assert [item.name for item in graph.roots()] == ["first", "second"]


def test_resource_graph_returns_empty_topology_for_unknown_resource():
    graph = ResourceGraph([])

    assert graph.topology(uuid4()) == []


def test_resource_graph_resolves_lineage():
    host = make_resource("host")
    service = make_resource("nginx", host.id)
    app = make_resource("api", service.id)
    graph = ResourceGraph([host, service, app])

    assert [item.name for item in graph.lineage(app.id)] == ["api", "nginx", "host"]
    assert graph.lineage_ids(app.id) == [app.id, service.id, host.id]


def test_resource_graph_rejects_cycles():
    first = make_resource("first")
    second = make_resource("second", first.id)
    first.parent_resource_id = second.id

    with pytest.raises(ValueError, match="cycle"):
        ResourceGraph([first, second])
