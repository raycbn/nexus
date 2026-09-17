from enum import StrEnum


class ResourceType(StrEnum):
    LINUX_SERVER = "linux_server"
    WINDOWS_SERVER = "windows_server"
    DOCKER_HOST = "docker_host"
    POSTGRESQL = "postgresql"
    SQL_SERVER = "sql_server"
    KUBERNETES = "kubernetes"
    VMWARE = "vmware"
    GENERIC_API = "generic_api"


class AutonomyLevel(StrEnum):
    READ_ONLY = "read_only"
    APPROVAL_REQUIRED = "approval_required"
    AUTONOMOUS = "autonomous"


class RiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class IncidentStatus(StrEnum):
    DETECTED = "detected"
    INVESTIGATING = "investigating"
    AWAITING_APPROVAL = "awaiting_approval"
    MITIGATING = "mitigating"
    RESOLVED = "resolved"
    FAILED = "failed"
    CLOSED = "closed"


class Severity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class SourceType(StrEnum):
    DOCUMENT = "document"
    RUNBOOK = "runbook"
    URL = "url"
    KNOWLEDGE_BASE = "knowledge_base"


class ActorType(StrEnum):
    USER = "user"
    AGENT = "agent"
    SYSTEM = "system"
    CONNECTOR = "connector"


class EventType(StrEnum):
    AGENT_STARTED = "agent_started"
    AGENT_COMPLETED = "agent_completed"
    TOOL_INVOKED = "tool_invoked"
    POLICY_CHECKED = "policy_checked"
    INCIDENT_CREATED = "incident_created"
    INCIDENT_UPDATED = "incident_updated"
    INCIDENT_RESOLVED = "incident_resolved"
    AUDIT_LOGGED = "audit_logged"
    CONNECTOR_CONNECTED = "connector_connected"
    CONNECTOR_DISCONNECTED = "connector_disconnected"
    CONNECTOR_HEALTH_CHECK = "connector_health_check"


class ResultStatus(StrEnum):
    SUCCESS = "success"
    FAILURE = "failure"
    PENDING = "pending"
    DENIED = "denied"
    SKIPPED = "skipped"
