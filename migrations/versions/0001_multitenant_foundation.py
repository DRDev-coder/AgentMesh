"""Create the AgentMesh multi-tenant SaaS schema.

Revision ID: 0001_multitenant_foundation
Revises: None
"""
from __future__ import annotations

from alembic import op

from api.db.base import Base
from api.db import models  # noqa: F401


revision = "0001_multitenant_foundation"
down_revision = None
branch_labels = None
depends_on = None


TENANT_TABLES = (
    "workspaces",
    "workspace_profile_versions",
    "documents",
    "document_versions",
    "document_chunks",
    "knowledge_releases",
    "api_keys",
    "saas_decisions",
    "decision_sessions",
    "decision_citations",
    "agent_finding_records",
    "tenant_escalations",
    "review_actions",
    "usage_events",
    "usage_reservations",
    "billing_outbox",
    "idempotency_records",
    "webhook_endpoints",
    "webhook_deliveries",
    "email_outbox",
    "background_jobs",
    "abuse_signals",
    "audit_events",
)


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    Base.metadata.create_all(bind=bind)
    if bind.dialect.name == "postgresql":
        for table in TENANT_TABLES:
            op.execute(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY')
            op.execute(f'ALTER TABLE "{table}" FORCE ROW LEVEL SECURITY')
            op.execute(
                f'''CREATE POLICY {table}_tenant_isolation ON "{table}"
                    USING (
                        organization_id = current_setting('app.organization_id', true)
                        OR current_setting('app.platform_access', true) = 'true'
                    )
                    WITH CHECK (
                        organization_id = current_setting('app.organization_id', true)
                        OR current_setting('app.platform_access', true) = 'true'
                    )'''
            )
        op.execute(
            '''CREATE FUNCTION prevent_audit_event_mutation()
               RETURNS trigger AS $$
               BEGIN
                   IF current_setting('app.allow_audit_purge', true) IS DISTINCT FROM 'true' THEN
                       RAISE EXCEPTION 'audit events are immutable';
                   END IF;
                   RETURN OLD;
               END;
               $$ LANGUAGE plpgsql'''
        )
        op.execute(
            '''CREATE TRIGGER audit_events_immutable
               BEFORE UPDATE OR DELETE ON audit_events
               FOR EACH ROW EXECUTE FUNCTION prevent_audit_event_mutation()'''
        )


def downgrade() -> None:
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)
    if bind.dialect.name == "postgresql":
        op.execute("DROP FUNCTION IF EXISTS prevent_audit_event_mutation()")
