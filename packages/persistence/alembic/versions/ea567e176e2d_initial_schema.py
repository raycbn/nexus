"""initial_schema

Revision ID: ea567e176e2d
Revises:
Create Date: 2026-09-20 09:49:38.779905

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "ea567e176e2d"
down_revision: Sequence[str] | None = None
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


# Define enum types that match the Python StrEnum classes exactly
investigationstatus_enum = postgresql.ENUM(
    "started",
    "collecting",
    "validating",
    "completed",
    "failed",
    name="investigationstatus",
    create_type=False,
)

hypothesisstatus_enum = postgresql.ENUM(
    "proposed",
    "supported",
    "contradicted",
    "validated",
    "unresolved",
    name="hypothesisstatus",
    create_type=False,
)

incidentstatus_enum = postgresql.ENUM(
    "detected",
    "investigating",
    "identified",
    "monitoring",
    "resolved",
    "closed",
    name="incidentstatus",
    create_type=False,
)

severity_enum = postgresql.ENUM(
    "low",
    "medium",
    "high",
    "critical",
    name="severity",
    create_type=False,
)

timelineeventtype_enum = postgresql.ENUM(
    "incident_created",
    "investigation_started",
    "evidence_collected",
    "hypothesis_created",
    "validation_completed",
    "conclusion_reached",
    "status_changed",
    "severity_changed",
    "incident_resolved",
    "incident_closed",
    "investigation_attached",
    name="timelineeventtype",
    create_type=False,
)

eventtype_enum = postgresql.ENUM(
    "agent_started",
    "agent_completed",
    "tool_invoked",
    "policy_checked",
    "incident_created",
    "incident_updated",
    "incident_resolved",
    "incident_status_changed",
    "incident_severity_changed",
    "investigation_attached",
    "incident_closed",
    "audit_logged",
    "connector_connected",
    "connector_disconnected",
    "connector_health_check",
    name="eventtype",
    create_type=False,
)

resultstatus_enum = postgresql.ENUM(
    "success",
    "failure",
    "pending",
    "denied",
    "skipped",
    name="resultstatus",
    create_type=False,
)


def upgrade() -> None:
    # Create enum types first
    investigationstatus_enum.create(op.get_bind(), checkfirst=True)
    hypothesisstatus_enum.create(op.get_bind(), checkfirst=True)
    incidentstatus_enum.create(op.get_bind(), checkfirst=True)
    severity_enum.create(op.get_bind(), checkfirst=True)
    timelineeventtype_enum.create(op.get_bind(), checkfirst=True)
    eventtype_enum.create(op.get_bind(), checkfirst=True)
    resultstatus_enum.create(op.get_bind(), checkfirst=True)

    # investigations table
    op.create_table(
        "investigations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("objective", sa.Text(), nullable=False),
        sa.Column("status", investigationstatus_enum, nullable=False, server_default="started"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_investigations_organization_id", "investigations", ["organization_id"], unique=False
    )
    op.create_index("ix_investigations_started_at", "investigations", ["started_at"], unique=False)

    # evidence table
    op.create_table(
        "evidence",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("investigation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_tool", sa.String(length=255), nullable=False),
        sa.Column("resource_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("observed_value", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("mode", sa.String(length=50), nullable=False, server_default="real"),
        sa.Column("relevance", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["investigation_id"],
            ["investigations.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_evidence_investigation_id", "evidence", ["investigation_id"], unique=False)
    op.create_index("ix_evidence_timestamp", "evidence", ["timestamp"], unique=False)

    # hypotheses table
    op.create_table(
        "hypotheses",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("investigation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column(
            "supporting_evidence_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="[]",
        ),
        sa.Column(
            "contradicting_evidence_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="[]",
        ),
        sa.Column("status", hypothesisstatus_enum, nullable=False, server_default="proposed"),
        sa.ForeignKeyConstraint(
            ["investigation_id"],
            ["investigations.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_hypotheses_investigation_id", "hypotheses", ["investigation_id"], unique=False
    )

    # validations table
    op.create_table(
        "validations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("investigation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("action_tool", sa.String(length=255), nullable=False),
        sa.Column("expected_condition", sa.Text(), nullable=False),
        sa.Column("actual_result", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("passed", sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(
            ["investigation_id"],
            ["investigations.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_validations_investigation_id", "validations", ["investigation_id"], unique=False
    )

    # conclusions table
    op.create_table(
        "conclusions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("investigation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("finding", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column(
            "supporting_evidence_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="[]",
        ),
        sa.Column("unresolved_uncertainty", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["investigation_id"],
            ["investigations.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("investigation_id"),
    )

    # incidents table
    op.create_table(
        "incidents",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("severity", severity_enum, nullable=False, server_default="medium"),
        sa.Column("status", incidentstatus_enum, nullable=False, server_default="detected"),
        sa.Column(
            "affected_resource_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="[]",
        ),
        sa.Column("assigned_agent_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("investigation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "evidence_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="[]",
        ),
        sa.Column("conclusion_finding", sa.Text(), nullable=True),
        sa.Column("conclusion_confidence", sa.Float(), nullable=True),
        sa.Column("conclusion_uncertainty", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("investigation_id"),
    )
    op.create_index("ix_incidents_organization_id", "incidents", ["organization_id"], unique=False)
    op.create_index("ix_incidents_status", "incidents", ["status"], unique=False)
    op.create_index("ix_incidents_severity", "incidents", ["severity"], unique=False)
    op.create_index(
        "ix_incidents_investigation_id", "incidents", ["investigation_id"], unique=False
    )
    op.create_index("ix_incidents_created_at", "incidents", ["created_at"], unique=False)
    op.create_index("ix_incidents_updated_at", "incidents", ["updated_at"], unique=False)

    # incident_timeline_entries table
    op.create_table(
        "incident_timeline_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("incident_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", timelineeventtype_enum, nullable=False),
        sa.Column("actor_type", sa.String(length=50), nullable=False),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("related_tool", sa.String(length=255), nullable=True),
        sa.Column("related_resource_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("related_investigation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "event_metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["incident_id"],
            ["incidents.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_incident_timeline_incident_id",
        "incident_timeline_entries",
        ["incident_id"],
        unique=False,
    )
    op.create_index(
        "ix_incident_timeline_created_at", "incident_timeline_entries", ["created_at"], unique=False
    )

    # audit_events table
    op.create_table(
        "audit_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("actor_type", sa.String(length=50), nullable=False),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", eventtype_enum, nullable=False),
        sa.Column("resource_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("tool_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("action", sa.String(length=255), nullable=False),
        sa.Column("result_status", resultstatus_enum, nullable=False),
        sa.Column(
            "event_metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("incident_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["incident_id"],
            ["incidents.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_audit_events_organization_id", "audit_events", ["organization_id"], unique=False
    )
    op.create_index("ix_audit_events_event_type", "audit_events", ["event_type"], unique=False)
    op.create_index("ix_audit_events_created_at", "audit_events", ["created_at"], unique=False)
    op.create_index("ix_audit_events_incident_id", "audit_events", ["incident_id"], unique=False)


def downgrade() -> None:
    # Drop tables in reverse dependency order using raw SQL for reliability
    op.execute("DROP TABLE IF EXISTS audit_events CASCADE")
    op.execute("DROP TABLE IF EXISTS incident_timeline_entries CASCADE")
    op.execute("DROP TABLE IF EXISTS incidents CASCADE")
    op.execute("DROP TABLE IF EXISTS conclusions CASCADE")
    op.execute("DROP TABLE IF EXISTS validations CASCADE")
    op.execute("DROP TABLE IF EXISTS hypotheses CASCADE")
    op.execute("DROP TABLE IF EXISTS evidence CASCADE")
    op.execute("DROP TABLE IF EXISTS investigations CASCADE")

    # Drop enum types after tables are dropped
    resultstatus_enum.drop(op.get_bind(), checkfirst=True)
    eventtype_enum.drop(op.get_bind(), checkfirst=True)
    timelineeventtype_enum.drop(op.get_bind(), checkfirst=True)
    severity_enum.drop(op.get_bind(), checkfirst=True)
    incidentstatus_enum.drop(op.get_bind(), checkfirst=True)
    hypothesisstatus_enum.drop(op.get_bind(), checkfirst=True)
    investigationstatus_enum.drop(op.get_bind(), checkfirst=True)
