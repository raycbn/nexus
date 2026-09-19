from uuid import UUID, uuid4

import pytest
from packages.domain.exceptions import (
    ConnectorError,
    DomainException,
    InvalidAgentConfiguration,
    PolicyViolation,
    ResourceNotFound,
    TenantAccessViolation,
    ToolNotAllowed,
)
from packages.domain.models import (
    ActorType,
    AutonomyLevel,
    EventType,
    IncidentStatus,
    KnowledgeSource,
    Organization,
    Resource,
    ResourceType,
    ResultStatus,
    RiskLevel,
    Severity,
    SourceType,
    Tool,
    User,
    Workspace,
)
from packages.domain.models.agent import Agent
from packages.domain.models.audit_event import AuditEvent
from packages.domain.models.connector import Connector as ConnectorModel
from packages.domain.models.incident import Incident
from packages.domain.models.policy import Policy
from pydantic import ValidationError


class TestUUIDGeneration:
    def test_organization_has_uuid_id(self):
        org = Organization(name="Test Org")
        assert isinstance(org.id, UUID)

    def test_user_has_uuid_id(self):
        user = User(organization_id=uuid4(), email="test@example.com", display_name="Test User")
        assert isinstance(user.id, UUID)

    def test_workspace_has_uuid_id(self):
        workspace = Workspace(organization_id=uuid4(), name="Test Workspace")
        assert isinstance(workspace.id, UUID)

    def test_resource_has_uuid_id(self):
        org_id = uuid4()
        resource = Resource(
            organization_id=org_id,
            workspace_id=uuid4(),
            name="server1",
            resource_type=ResourceType.LINUX_SERVER,
        )
        assert isinstance(resource.id, UUID)

    def test_agent_has_uuid_id(self):
        agent = Agent(
            organization_id=uuid4(),
            name="agent1",
            role="investigator",
            autonomy_level=AutonomyLevel.READ_ONLY,
        )
        assert isinstance(agent.id, UUID)

    def test_tool_has_uuid_id(self):
        tool = Tool(
            organization_id=uuid4(),
            name="read_logs",
            description="Read logs",
            risk_level=RiskLevel.LOW,
        )
        assert isinstance(tool.id, UUID)

    def test_policy_has_uuid_id(self):
        policy = Policy(organization_id=uuid4(), name="default")
        assert isinstance(policy.id, UUID)

    def test_incident_has_uuid_id(self):
        org_id = uuid4()
        incident = Incident(
            organization_id=org_id,
            workspace_id=uuid4(),
            title="Test",
            description="Desc",
            severity=Severity.CRITICAL,
            status=IncidentStatus.DETECTED,
        )
        assert isinstance(incident.id, UUID)

    def test_audit_event_has_uuid_id(self):
        audit = AuditEvent(
            organization_id=uuid4(),
            actor_type=ActorType.SYSTEM,
            actor_id=uuid4(),
            event_type=EventType.AUDIT_LOGGED,
            action="test",
            result_status=ResultStatus.SUCCESS,
        )
        assert isinstance(audit.id, UUID)

    def test_knowledge_source_has_uuid_id(self):
        ks = KnowledgeSource(organization_id=uuid4(), name="docs", source_type=SourceType.DOCUMENT)
        assert isinstance(ks.id, UUID)


class TestRequiredOrganizationId:
    def test_organization_does_not_have_organization_id(self):
        org = Organization(name="Top Level")
        assert not hasattr(org, "organization_id")

    def test_user_requires_organization_id(self):
        with pytest.raises(ValidationError):
            User(email="test@example.com", display_name="Test")

    def test_workspace_requires_organization_id(self):
        with pytest.raises(ValidationError):
            Workspace(name="No Org")

    def test_resource_requires_organization_id(self):
        with pytest.raises(ValidationError):
            Resource(name="r", resource_type=ResourceType.LINUX_SERVER)

    def test_agent_requires_organization_id(self):
        with pytest.raises(ValidationError):
            Agent(name="a", role="r", autonomy_level=AutonomyLevel.READ_ONLY)

    def test_tool_requires_organization_id(self):
        with pytest.raises(ValidationError):
            Tool(name="t", description="d", risk_level=RiskLevel.LOW)

    def test_policy_requires_organization_id(self):
        with pytest.raises(ValidationError):
            Policy(name="p")

    def test_incident_requires_organization_id(self):
        with pytest.raises(ValidationError):
            Incident(
                title="t",
                description="d",
                severity=Severity.CRITICAL,
                status=IncidentStatus.DETECTED,
            )

    def test_audit_event_requires_organization_id(self):
        with pytest.raises(ValidationError):
            AuditEvent(
                actor_type=ActorType.SYSTEM,
                actor_id=uuid4(),
                event_type=EventType.AUDIT_LOGGED,
                action="a",
                result_status=ResultStatus.SUCCESS,
            )

    def test_knowledge_source_requires_organization_id(self):
        with pytest.raises(ValidationError):
            KnowledgeSource(name="k", source_type=SourceType.DOCUMENT)


class TestWorkspaceOwnership:
    def test_resource_can_have_workspace_id(self):
        org_id = uuid4()
        ws_id = uuid4()
        resource = Resource(
            organization_id=org_id,
            workspace_id=ws_id,
            name="r",
            resource_type=ResourceType.LINUX_SERVER,
        )
        assert resource.workspace_id == ws_id

    def test_resource_workspace_id_is_uuid(self):
        org_id = uuid4()
        ws_id = uuid4()
        resource = Resource(
            organization_id=org_id,
            workspace_id=ws_id,
            name="r",
            resource_type=ResourceType.LINUX_SERVER,
        )
        assert isinstance(resource.workspace_id, UUID)

    def test_resource_workspace_id_can_be_none(self):
        org_id = uuid4()
        resource = Resource(
            organization_id=org_id,
            workspace_id=None,
            name="r",
            resource_type=ResourceType.LINUX_SERVER,
        )
        assert resource.workspace_id is None

    def test_agent_can_have_workspace_id(self):
        org_id = uuid4()
        ws_id = uuid4()
        agent = Agent(
            organization_id=org_id,
            workspace_id=ws_id,
            name="a",
            role="r",
            autonomy_level=AutonomyLevel.READ_ONLY,
        )
        assert agent.workspace_id == ws_id

    def test_agent_workspace_id_can_be_none(self):
        org_id = uuid4()
        agent = Agent(
            organization_id=org_id,
            workspace_id=None,
            name="a",
            role="r",
            autonomy_level=AutonomyLevel.READ_ONLY,
        )
        assert agent.workspace_id is None


class TestValidResourceTypes:
    def test_linux_server(self):
        org_id = uuid4()
        resource = Resource(
            organization_id=org_id,
            workspace_id=None,
            name="linux1",
            resource_type=ResourceType.LINUX_SERVER,
        )
        assert resource.resource_type == ResourceType.LINUX_SERVER

    def test_windows_server(self):
        resource = Resource(
            organization_id=uuid4(),
            workspace_id=None,
            name="win1",
            resource_type=ResourceType.WINDOWS_SERVER,
        )
        assert resource.resource_type == ResourceType.WINDOWS_SERVER

    def test_docker_host(self):
        resource = Resource(
            organization_id=uuid4(),
            workspace_id=None,
            name="docker1",
            resource_type=ResourceType.DOCKER_HOST,
        )
        assert resource.resource_type == ResourceType.DOCKER_HOST

    def test_postgresql(self):
        resource = Resource(
            organization_id=uuid4(),
            workspace_id=None,
            name="pg1",
            resource_type=ResourceType.POSTGRESQL,
        )
        assert resource.resource_type == ResourceType.POSTGRESQL

    def test_sql_server(self):
        resource = Resource(
            organization_id=uuid4(),
            workspace_id=None,
            name="mssql1",
            resource_type=ResourceType.SQL_SERVER,
        )
        assert resource.resource_type == ResourceType.SQL_SERVER

    def test_kubernetes(self):
        resource = Resource(
            organization_id=uuid4(),
            workspace_id=None,
            name="k8s1",
            resource_type=ResourceType.KUBERNETES,
        )
        assert resource.resource_type == ResourceType.KUBERNETES

    def test_vmware(self):
        resource = Resource(
            organization_id=uuid4(),
            workspace_id=None,
            name="vm1",
            resource_type=ResourceType.VMWARE,
        )
        assert resource.resource_type == ResourceType.VMWARE

    def test_generic_api(self):
        resource = Resource(
            organization_id=uuid4(),
            workspace_id=None,
            name="api1",
            resource_type=ResourceType.GENERIC_API,
        )
        assert resource.resource_type == ResourceType.GENERIC_API

    def test_invalid_resource_type_rejected(self):
        org_id = uuid4()
        with pytest.raises(ValidationError):
            Resource(
                organization_id=org_id,
                workspace_id=None,
                name="bad",
                resource_type="not_a_real_type",
            )


class TestAutonomyLevels:
    def test_read_only(self):
        agent = Agent(
            organization_id=uuid4(), name="a", role="r", autonomy_level=AutonomyLevel.READ_ONLY
        )
        assert agent.autonomy_level == AutonomyLevel.READ_ONLY

    def test_approval_required(self):
        agent = Agent(
            organization_id=uuid4(),
            name="a",
            role="r",
            autonomy_level=AutonomyLevel.APPROVAL_REQUIRED,
        )
        assert agent.autonomy_level == AutonomyLevel.APPROVAL_REQUIRED

    def test_autonomous(self):
        agent = Agent(
            organization_id=uuid4(), name="a", role="r", autonomy_level=AutonomyLevel.AUTONOMOUS
        )
        assert agent.autonomy_level == AutonomyLevel.AUTONOMOUS

    def test_invalid_autonomy_level_rejected(self):
        with pytest.raises(ValidationError):
            Agent(organization_id=uuid4(), name="a", role="r", autonomy_level="invalid_level")


class TestToolRiskLevels:
    def test_low_risk(self):
        tool = Tool(organization_id=uuid4(), name="t", description="d", risk_level=RiskLevel.LOW)
        assert tool.risk_level == RiskLevel.LOW

    def test_medium_risk(self):
        tool = Tool(organization_id=uuid4(), name="t", description="d", risk_level=RiskLevel.MEDIUM)
        assert tool.risk_level == RiskLevel.MEDIUM

    def test_high_risk(self):
        tool = Tool(organization_id=uuid4(), name="t", description="d", risk_level=RiskLevel.HIGH)
        assert tool.risk_level == RiskLevel.HIGH

    def test_critical_risk(self):
        tool = Tool(
            organization_id=uuid4(), name="t", description="d", risk_level=RiskLevel.CRITICAL
        )
        assert tool.risk_level == RiskLevel.CRITICAL

    def test_invalid_risk_level_rejected(self):
        with pytest.raises(ValidationError):
            Tool(organization_id=uuid4(), name="t", description="d", risk_level="dangerous")


class TestIncidentStatuses:
    def test_detected(self):
        incident = Incident(
            organization_id=uuid4(),
            workspace_id=uuid4(),
            title="t",
            description="d",
            severity=Severity.CRITICAL,
            status=IncidentStatus.DETECTED,
        )
        assert incident.status == IncidentStatus.DETECTED

    def test_investigating(self):
        incident = Incident(
            organization_id=uuid4(),
            workspace_id=uuid4(),
            title="t",
            description="d",
            severity=Severity.CRITICAL,
            status=IncidentStatus.INVESTIGATING,
        )
        assert incident.status == IncidentStatus.INVESTIGATING

    def test_identified(self):
        incident = Incident(
            organization_id=uuid4(),
            workspace_id=uuid4(),
            title="t",
            description="d",
            severity=Severity.CRITICAL,
            status=IncidentStatus.IDENTIFIED,
        )
        assert incident.status == IncidentStatus.IDENTIFIED

    def test_monitoring(self):
        incident = Incident(
            organization_id=uuid4(),
            workspace_id=uuid4(),
            title="t",
            description="d",
            severity=Severity.CRITICAL,
            status=IncidentStatus.MONITORING,
        )
        assert incident.status == IncidentStatus.MONITORING

    def test_resolved(self):
        incident = Incident(
            organization_id=uuid4(),
            workspace_id=uuid4(),
            title="t",
            description="d",
            severity=Severity.CRITICAL,
            status=IncidentStatus.RESOLVED,
        )
        assert incident.status == IncidentStatus.RESOLVED

    def test_closed(self):
        incident = Incident(
            organization_id=uuid4(),
            workspace_id=uuid4(),
            title="t",
            description="d",
            severity=Severity.CRITICAL,
            status=IncidentStatus.CLOSED,
        )
        assert incident.status == IncidentStatus.CLOSED


class TestPolicyDefinitions:
    def test_empty_policy(self):
        policy = Policy(organization_id=uuid4(), name="empty")
        assert policy.allowed_tool_ids == []
        assert policy.denied_tool_ids == []
        assert policy.approval_required_tool_ids == []
        assert policy.max_risk_level == RiskLevel.MEDIUM
        assert policy.allowed_resource_ids == []

    def test_policy_with_allowed_tools(self):
        policy = Policy(organization_id=uuid4(), name="restricted", allowed_tool_ids=["tool-1"])
        assert "tool-1" in policy.allowed_tool_ids

    def test_policy_with_denied_tools(self):
        policy = Policy(organization_id=uuid4(), name="restricted", denied_tool_ids=["tool-1"])
        assert "tool-1" in policy.denied_tool_ids

    def test_policy_with_approval_required(self):
        policy = Policy(
            organization_id=uuid4(), name="restricted", approval_required_tool_ids=["tool-1"]
        )
        assert "tool-1" in policy.approval_required_tool_ids

    def test_policy_max_risk_level(self):
        policy = Policy(organization_id=uuid4(), name="restricted", max_risk_level=RiskLevel.LOW)
        assert policy.max_risk_level == RiskLevel.LOW


class TestAuditEventCreation:
    def test_audit_event_with_all_fields(self):
        org_id = uuid4()
        audit = AuditEvent(
            organization_id=org_id,
            workspace_id=uuid4(),
            actor_type=ActorType.AGENT,
            actor_id=uuid4(),
            event_type=EventType.AGENT_STARTED,
            resource_id=uuid4(),
            tool_id=uuid4(),
            action="agent_started",
            result_status=ResultStatus.SUCCESS,
        )
        assert audit.organization_id == org_id
        assert audit.actor_type == ActorType.AGENT
        assert audit.action == "agent_started"

    def test_audit_event_requires_organization_id(self):
        with pytest.raises(ValidationError):
            AuditEvent(
                actor_type=ActorType.SYSTEM,
                actor_id=uuid4(),
                event_type=EventType.AUDIT_LOGGED,
                action="a",
                result_status=ResultStatus.SUCCESS,
            )

    def test_audit_event_requires_actor_type(self):
        with pytest.raises(ValidationError):
            AuditEvent(
                organization_id=uuid4(),
                actor_id=uuid4(),
                event_type=EventType.AUDIT_LOGGED,
                action="a",
                result_status=ResultStatus.SUCCESS,
            )

    def test_audit_event_generates_uuid(self):
        audit = AuditEvent(
            organization_id=uuid4(),
            actor_type=ActorType.SYSTEM,
            actor_id=uuid4(),
            event_type=EventType.AUDIT_LOGGED,
            action="a",
            result_status=ResultStatus.SUCCESS,
        )
        assert isinstance(audit.id, UUID)


class TestDomainExceptions:
    def test_resource_not_found(self):
        exc = ResourceNotFound("res-123")
        assert exc.resource_id == "res-123"
        assert "res-123" in str(exc)

    def test_connector_error(self):
        exc = ConnectorError("connection failed")
        assert "connection failed" in str(exc)

    def test_tool_not_allowed(self):
        exc = ToolNotAllowed("tool-456")
        assert exc.tool_id == "tool-456"
        assert "tool-456" in str(exc)

    def test_policy_violation(self):
        exc = PolicyViolation("rule violated")
        assert exc.reason == "rule violated"
        assert "rule violated" in str(exc)

    def test_tenant_access_violation(self):
        exc = TenantAccessViolation("access denied")
        assert "access denied" in str(exc)

    def test_invalid_agent_configuration(self):
        exc = InvalidAgentConfiguration("bad config")
        assert "bad config" in str(exc)

    def test_domain_exception_base(self):
        exc = DomainException("base error")
        assert "base error" in str(exc)
        assert isinstance(exc, Exception)


class TestMultiTenancyExplicit:
    def test_all_tenant_scoped_models_have_organization_id(self):
        tenant_scoped = [
            ("User", User, {"organization_id": uuid4(), "email": "e@e.com", "display_name": "U"}),
            ("Workspace", Workspace, {"organization_id": uuid4(), "name": "W"}),
            (
                "Resource",
                Resource,
                {
                    "organization_id": uuid4(),
                    "workspace_id": None,
                    "name": "R",
                    "resource_type": ResourceType.LINUX_SERVER,
                },
            ),
            (
                "ConnectorModel",
                ConnectorModel,
                {
                    "organization_id": uuid4(),
                    "resource_id": uuid4(),
                    "name": "C",
                    "connector_type": "ssh",
                },
            ),
            (
                "Agent",
                Agent,
                {
                    "organization_id": uuid4(),
                    "name": "A",
                    "role": "r",
                    "autonomy_level": AutonomyLevel.READ_ONLY,
                },
            ),
            (
                "Tool",
                Tool,
                {
                    "organization_id": uuid4(),
                    "name": "T",
                    "description": "d",
                    "risk_level": RiskLevel.LOW,
                },
            ),
            ("Policy", Policy, {"organization_id": uuid4(), "name": "P"}),
            (
                "Incident",
                Incident,
                {
                    "organization_id": uuid4(),
                    "workspace_id": None,
                    "title": "t",
                    "description": "d",
                    "severity": Severity.LOW,
                    "status": IncidentStatus.DETECTED,
                },
            ),
            (
                "AuditEvent",
                AuditEvent,
                {
                    "organization_id": uuid4(),
                    "actor_type": ActorType.SYSTEM,
                    "actor_id": uuid4(),
                    "event_type": EventType.AUDIT_LOGGED,
                    "action": "a",
                    "result_status": ResultStatus.SUCCESS,
                },
            ),
            (
                "KnowledgeSource",
                KnowledgeSource,
                {"organization_id": uuid4(), "name": "K", "source_type": SourceType.DOCUMENT},
            ),
        ]
        for name, model, kwargs in tenant_scoped:
            instance = model(**kwargs)
            assert hasattr(instance, "organization_id"), f"{name} missing organization_id"
            assert instance.organization_id is not None, f"{name} organization_id is None"
            assert isinstance(instance.organization_id, UUID), f"{name} organization_id is not UUID"

    def test_organization_is_root_tenant_entity(self):
        org = Organization(name="Test")
        assert not hasattr(org, "organization_id")

    def test_resource_belongs_to_workspace_within_org(self):
        org_id = uuid4()
        ws_id = uuid4()
        resource = Resource(
            organization_id=org_id,
            workspace_id=ws_id,
            name="r",
            resource_type=ResourceType.LINUX_SERVER,
        )
        assert resource.organization_id == org_id
        assert resource.workspace_id == ws_id

    def test_agent_can_be_scoped_to_workspace(self):
        org_id = uuid4()
        ws_id = uuid4()
        agent = Agent(
            organization_id=org_id,
            workspace_id=ws_id,
            name="a",
            role="r",
            autonomy_level=AutonomyLevel.READ_ONLY,
        )
        assert agent.organization_id == org_id
        assert agent.workspace_id == ws_id
