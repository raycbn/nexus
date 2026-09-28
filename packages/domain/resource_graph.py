from uuid import UUID

from packages.domain.models.resource import Resource


class ResourceGraph:
    def __init__(self, resources: list[Resource]) -> None:
        self._resources = {resource.id: resource for resource in resources}
        self._validate_acyclic()

    def ancestors(self, resource_id: UUID) -> list[Resource]:
        result: list[Resource] = []
        current = self._resources.get(resource_id)
        while current is not None and current.parent_resource_id is not None:
            parent = self._resources.get(current.parent_resource_id)
            if parent is None:
                break
            result.append(parent)
            current = parent
        return result

    def children(self, resource_id: UUID) -> list[Resource]:
        return [
            resource
            for resource in self._resources.values()
            if resource.parent_resource_id == resource_id
        ]

    def lineage(self, resource_id: UUID) -> list[Resource]:
        resource = self._resources.get(resource_id)
        if resource is None:
            return []
        return [resource, *self.ancestors(resource_id)]

    def descendants(self, resource_id: UUID) -> list[Resource]:
        result: list[Resource] = []
        pending = list(self.children(resource_id))
        while pending:
            current = pending.pop(0)
            result.append(current)
            pending.extend(self.children(current.id))
        return result

    def topology(self, resource_id: UUID) -> list[Resource]:
        resource = self._resources.get(resource_id)
        if resource is None:
            return []
        return [resource, *self.descendants(resource_id)]

    def roots(self) -> list[Resource]:
        return [
            resource
            for resource in self._resources.values()
            if resource.parent_resource_id is None
        ]

    def lineage_ids(self, resource_id: UUID) -> list[UUID]:
        return [resource.id for resource in self.lineage(resource_id)]

    def expand_lineage_ids(self, resource_ids: list[UUID]) -> list[UUID]:
        expanded: list[UUID] = []
        seen: set[UUID] = set()
        for resource_id in resource_ids:
            for lineage_id in self.lineage_ids(resource_id):
                if lineage_id not in seen:
                    seen.add(lineage_id)
                    expanded.append(lineage_id)
        return expanded

    def validate_scope(self, organization_id: UUID, workspace_id: UUID | None) -> None:
        for resource in self._resources.values():
            if resource.organization_id != organization_id:
                raise ValueError("Resource graph contains a foreign organization resource")
            if resource.workspace_id not in {None, workspace_id}:
                raise ValueError("Resource graph contains a foreign workspace resource")

    def _validate_acyclic(self) -> None:
        for resource in self._resources.values():
            seen: set[UUID] = set()
            current = resource
            while current.parent_resource_id is not None:
                if current.id in seen:
                    raise ValueError("Resource hierarchy contains a cycle")
                seen.add(current.id)
                parent = self._resources.get(current.parent_resource_id)
                if parent is None:
                    break
                current = parent
