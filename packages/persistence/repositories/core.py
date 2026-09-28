from collections.abc import Sequence
from uuid import UUID, uuid4

from packages.domain.models.agent import Agent
from packages.domain.models.resource import Resource
from packages.domain.resource_graph import ResourceGraph
from packages.persistence.models.core import (
    AgentModel,
    OrganizationModel,
    ResourceModel,
    UserModel,
    WorkspaceModel,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


def _resource_to_domain(model: ResourceModel) -> Resource:
    from packages.domain.models.enums import ResourceType

    return Resource(
        id=model.id,
        organization_id=model.organization_id,
        workspace_id=model.workspace_id,
        owner_user_id=model.owner_user_id,
        parent_resource_id=model.parent_resource_id,
        name=model.name,
        resource_type=ResourceType(model.resource_type),
        environment=model.environment,
        description=model.description,
        enabled=model.enabled,
        labels=model.labels,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _agent_to_domain(model: AgentModel) -> Agent:
    from packages.domain.models.enums import AutonomyLevel

    return Agent(
        id=model.id,
        organization_id=model.organization_id,
        workspace_id=model.workspace_id,
        name=model.name,
        role=model.role,
        description=model.description,
        system_instructions=model.system_instructions,
        enabled=model.enabled,
        autonomy_level=AutonomyLevel(model.autonomy_level),
        allowed_tool_ids=[UUID(value) for value in model.allowed_tool_ids if _is_uuid(value)],
        policy_id=model.policy_id,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _is_uuid(value: str) -> bool:
    try:
        UUID(value)
    except ValueError:
        return False
    return True


class CoreRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def ensure_local_bootstrap(
        self, email: str, password_hash: str, organization_name: str = "NEXUS Local"
    ) -> tuple[OrganizationModel, UserModel, WorkspaceModel]:
        org_result = await self._session.execute(
            select(OrganizationModel).where(OrganizationModel.name == organization_name)
        )
        organization = org_result.scalar_one_or_none()
        if organization is None:
            organization = OrganizationModel(id=uuid4(), name=organization_name)
            self._session.add(organization)
            await self._session.flush()

        workspace_result = await self._session.execute(
            select(WorkspaceModel).where(
                WorkspaceModel.organization_id == organization.id,
                WorkspaceModel.name == "Default",
            )
        )
        workspace = workspace_result.scalar_one_or_none()
        if workspace is None:
            workspace = WorkspaceModel(
                id=uuid4(),
                organization_id=organization.id,
                name="Default",
                description="Default NEXUS workspace",
            )
            self._session.add(workspace)
            await self._session.flush()

        user_result = await self._session.execute(select(UserModel).where(UserModel.email == email))
        user = user_result.scalar_one_or_none()
        if user is None:
            user = UserModel(
                id=uuid4(),
                organization_id=organization.id,
                email=email.lower(),
                display_name="NEXUS Administrator",
                password_hash=password_hash,
                role="admin",
                default_workspace_id=workspace.id,
            )
            self._session.add(user)
        else:
            user.organization_id = organization.id
            user.role = "admin"
            user.default_workspace_id = workspace.id
        await self._session.flush()
        return organization, user, workspace

    async def is_initialized(self) -> bool:
        result = await self._session.execute(select(UserModel.id).limit(1))
        return result.scalar_one_or_none() is not None

    async def create_initial_installation(
        self,
        organization_name: str,
        admin_email: str,
        admin_display_name: str,
        password_hash: str,
    ) -> tuple[OrganizationModel, WorkspaceModel, UserModel]:
        if await self.is_initialized():
            raise ValueError("NEXUS is already initialized")
        organization = OrganizationModel(id=uuid4(), name=organization_name.strip())
        self._session.add(organization)
        await self._session.flush()
        workspace = WorkspaceModel(
            id=uuid4(),
            organization_id=organization.id,
            name="Default",
            description="Default NEXUS workspace",
        )
        self._session.add(workspace)
        await self._session.flush()
        user = UserModel(
            id=uuid4(),
            organization_id=organization.id,
            email=admin_email.strip().lower(),
            display_name=admin_display_name.strip(),
            password_hash=password_hash,
            role="admin",
            default_workspace_id=workspace.id,
        )
        self._session.add(user)
        await self._session.flush()
        return organization, workspace, user

    async def list_workspaces(self, organization_id: UUID) -> list[WorkspaceModel]:
        result = await self._session.execute(
            select(WorkspaceModel)
            .where(WorkspaceModel.organization_id == organization_id)
            .order_by(WorkspaceModel.name)
        )
        return list(result.scalars().all())

    async def get_workspace(
        self, organization_id: UUID, workspace_id: UUID
    ) -> WorkspaceModel | None:
        result = await self._session.execute(
            select(WorkspaceModel).where(
                WorkspaceModel.id == workspace_id,
                WorkspaceModel.organization_id == organization_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_user_by_email(self, email: str) -> UserModel | None:
        result = await self._session.execute(
            select(UserModel).where(UserModel.email == email.lower())
        )
        return result.scalar_one_or_none()

    async def get_user_by_id(self, user_id: UUID, organization_id: UUID) -> UserModel | None:
        result = await self._session.execute(
            select(UserModel).where(
                UserModel.id == user_id,
                UserModel.organization_id == organization_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_resources(
        self, organization_id: UUID, workspace_id: UUID | None
    ) -> list[Resource]:
        stmt = select(ResourceModel).where(ResourceModel.organization_id == organization_id)
        if workspace_id is not None:
            stmt = stmt.where(ResourceModel.workspace_id == workspace_id)
        result = await self._session.execute(stmt.order_by(ResourceModel.name))
        return [_resource_to_domain(model) for model in result.scalars().all()]

    async def get_resources_by_ids(
        self, organization_id: UUID, resource_ids: Sequence[UUID], workspace_id: UUID | None
    ) -> list[Resource]:
        if not resource_ids:
            return []
        stmt = select(ResourceModel).where(
            ResourceModel.organization_id == organization_id,
            ResourceModel.id.in_(list(resource_ids)),
        )
        if workspace_id is not None:
            stmt = stmt.where(ResourceModel.workspace_id == workspace_id)
        result = await self._session.execute(stmt)
        return [_resource_to_domain(model) for model in result.scalars().all()]

    async def get_resource_graph(
        self, organization_id: UUID, workspace_id: UUID | None
    ) -> ResourceGraph:
        resources = await self.list_resources(organization_id, workspace_id)
        graph = ResourceGraph(resources)
        graph.validate_scope(organization_id, workspace_id)
        return graph

    async def get_resource(
        self, organization_id: UUID, resource_id: UUID, workspace_id: UUID | None = None
    ) -> Resource | None:
        stmt = select(ResourceModel).where(
            ResourceModel.id == resource_id,
            ResourceModel.organization_id == organization_id,
        )
        if workspace_id is not None:
            stmt = stmt.where(ResourceModel.workspace_id == workspace_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return _resource_to_domain(model) if model else None

    async def ensure_dev_resource(
        self, organization_id: UUID, workspace_id: UUID | None
    ) -> Resource:
        result = await self._session.execute(
            select(ResourceModel).where(
                ResourceModel.organization_id == organization_id,
                ResourceModel.workspace_id == workspace_id,
                ResourceModel.name == "linux-lab-01",
            )
        )
        model = result.scalar_one_or_none()
        if model is None:
            model = ResourceModel(
                id=uuid4(),
                organization_id=organization_id,
                workspace_id=workspace_id,
                name="linux-lab-01",
                resource_type="linux_server",
                environment="development",
                description="Local Linux lab for development",
                enabled=True,
                labels={"purpose": "development", "location": "local"},
            )
            self._session.add(model)
            await self._session.flush()
        return _resource_to_domain(model)

    async def create_resource(
        self,
        organization_id: UUID,
        workspace_id: UUID | None,
        *,
        owner_user_id: UUID | None = None,
        name: str,
        resource_type: str,
        environment: str = "development",
        description: str | None = None,
        enabled: bool = True,
        labels: dict[str, str] | None = None,
        parent_resource_id: UUID | None = None,
    ) -> Resource:
        from packages.domain.models.enums import ResourceType

        ResourceType(resource_type)
        if (
            workspace_id is not None
            and await self.get_workspace(organization_id, workspace_id) is None
        ):
            raise ValueError("Workspace not found")
        if (
            owner_user_id is not None
            and await self.get_user_by_id(owner_user_id, organization_id) is None
        ):
            raise ValueError("Owner user not found")
        if (
            parent_resource_id is not None
            and await self.get_resource(organization_id, parent_resource_id, workspace_id) is None
        ):
            raise ValueError("Parent resource not found")
        model = ResourceModel(
            id=uuid4(),
            organization_id=organization_id,
            workspace_id=workspace_id,
            owner_user_id=owner_user_id,
            parent_resource_id=parent_resource_id,
            name=name.strip(),
            resource_type=resource_type,
            environment=environment.strip(),
            description=description.strip() if description else None,
            enabled=enabled,
            labels=labels or {},
        )
        if not model.name:
            raise ValueError("Resource name is required")
        self._session.add(model)
        await self._session.flush()
        return _resource_to_domain(model)

    async def update_resource(
        self, organization_id: UUID, resource_id: UUID, workspace_id: UUID | None, **changes: object
    ) -> Resource | None:
        model = await self._session.get(ResourceModel, resource_id)
        if model is None or model.organization_id != organization_id:
            return None
        if workspace_id is not None and model.workspace_id != workspace_id:
            return None
        if "resource_type" in changes and changes["resource_type"] is not None:
            from packages.domain.models.enums import ResourceType

            ResourceType(str(changes["resource_type"]))
        if (
            "owner_user_id" in changes
            and changes["owner_user_id"] is not None
            and await self.get_user_by_id(changes["owner_user_id"], organization_id) is None
        ):
            raise ValueError("Owner user not found")
        if "parent_resource_id" in changes and changes["parent_resource_id"] is not None:
            parent_id = changes["parent_resource_id"]
            if (
                parent_id == resource_id
                or await self.get_resource(organization_id, parent_id, workspace_id) is None
            ):
                raise ValueError("Invalid parent resource")
        for key, value in changes.items():
            if value is not None or key in {"description", "parent_resource_id"}:
                if key in {"name", "environment"} and isinstance(value, str):
                    value = value.strip()
                    if not value:
                        raise ValueError(f"{key} is required")
                if hasattr(model, key):
                    setattr(model, key, value)
        await self._session.flush()
        return _resource_to_domain(model)

    async def delete_resource(
        self, organization_id: UUID, resource_id: UUID, workspace_id: UUID | None
    ) -> bool:
        model = await self._session.get(ResourceModel, resource_id)
        if model is None or model.organization_id != organization_id:
            return False
        if workspace_id is not None and model.workspace_id != workspace_id:
            return False
        child_result = await self._session.execute(
            select(ResourceModel.id).where(ResourceModel.parent_resource_id == resource_id).limit(1)
        )
        if child_result.scalar_one_or_none() is not None:
            raise ValueError("Resource has child resources")
        await self._session.delete(model)
        await self._session.flush()
        return True

    async def list_agents(self, organization_id: UUID, workspace_id: UUID | None) -> list[Agent]:
        stmt = select(AgentModel).where(AgentModel.organization_id == organization_id)
        if workspace_id is not None:
            stmt = stmt.where(AgentModel.workspace_id == workspace_id)
        result = await self._session.execute(stmt.order_by(AgentModel.name))
        return [_agent_to_domain(model) for model in result.scalars().all()]

    async def get_agent(
        self, organization_id: UUID, agent_id: UUID, workspace_id: UUID | None = None
    ) -> Agent | None:
        stmt = select(AgentModel).where(
            AgentModel.id == agent_id,
            AgentModel.organization_id == organization_id,
        )
        if workspace_id is not None:
            stmt = stmt.where(AgentModel.workspace_id == workspace_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return _agent_to_domain(model) if model else None

    async def ensure_dev_agent(self, organization_id: UUID, workspace_id: UUID | None) -> Agent:
        result = await self._session.execute(
            select(AgentModel).where(
                AgentModel.organization_id == organization_id,
                AgentModel.workspace_id == workspace_id,
                AgentModel.name == "Linux Investigator",
            )
        )
        model = result.scalar_one_or_none()
        if model is None:
            model = AgentModel(
                id=uuid4(),
                organization_id=organization_id,
                workspace_id=workspace_id,
                name="Linux Investigator",
                role="investigator",
                description="Investigates Linux system issues",
                system_instructions="You are an expert Linux system investigator.",
                enabled=True,
                autonomy_level="read_only",
                allowed_tool_ids=[],
            )
            self._session.add(model)
            await self._session.flush()
        return _agent_to_domain(model)

    async def create_organization_with_owner(
        self,
        organization_name: str,
        owner_email: str,
        owner_display_name: str,
        password_hash: str,
    ) -> tuple[OrganizationModel, WorkspaceModel, UserModel]:
        email = owner_email.strip().lower()
        existing = await self.get_user_by_email(email)
        if existing is not None:
            raise ValueError("Email is already registered")
        name = organization_name.strip()
        if not name:
            raise ValueError("Organization name is required")
        organization = OrganizationModel(id=uuid4(), name=name)
        self._session.add(organization)
        await self._session.flush()
        workspace = WorkspaceModel(
            id=uuid4(), organization_id=organization.id,
            name="Default", description="Default NEXUS workspace",
        )
        self._session.add(workspace)
        await self._session.flush()
        user = UserModel(
            id=uuid4(), organization_id=organization.id, email=email,
            display_name=owner_display_name.strip(), password_hash=password_hash,
            role="admin", default_workspace_id=workspace.id, email_verified_at=None,
        )
        self._session.add(user)
        await self._session.flush()
        return organization, workspace, user
