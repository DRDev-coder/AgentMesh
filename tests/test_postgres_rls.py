from __future__ import annotations

import os
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import DBAPIError

from api.config import get_settings
from api.db.base import Database
from api.errors import APIError
from api.services.usage import reserve_usage
from api.tenancy import set_tenant_database_context


RLS_URL = os.getenv("RLS_TEST_DATABASE_URL")
ADMIN_URL = os.getenv("DATABASE_URL")


@pytest.mark.skipif(not RLS_URL or not ADMIN_URL, reason="PostgreSQL RLS test URLs are not configured")
def test_postgres_rls_hides_and_rejects_cross_tenant_rows() -> None:
    organization_a = str(uuid.uuid4())
    organization_b = str(uuid.uuid4())
    event_a = str(uuid.uuid4())
    event_b = str(uuid.uuid4())
    admin = create_engine(ADMIN_URL)
    tenant = create_engine(RLS_URL)
    try:
        with admin.begin() as connection:
            connection.execute(
                text("SELECT set_config('app.allow_audit_purge', 'true', true)")
            )
            connection.execute(
                text(
                    "INSERT INTO organizations "
                    "(id, name, slug, status, billing_email, raw_content_retention_days, created_at, updated_at) "
                    "VALUES (:a, 'Tenant A', :slug_a, 'ACTIVE', 'a@example.com', 30, now(), now()), "
                    "(:b, 'Tenant B', :slug_b, 'ACTIVE', 'b@example.com', 30, now(), now())"
                ),
                {
                    "a": organization_a,
                    "b": organization_b,
                    "slug_a": f"tenant-a-{organization_a[:8]}",
                    "slug_b": f"tenant-b-{organization_b[:8]}",
                },
            )
            for event_id, organization_id in (
                (event_a, organization_a),
                (event_b, organization_b),
            ):
                connection.execute(
                    text(
                        "INSERT INTO audit_events "
                        "(id, organization_id, actor_type, actor_id, action, resource_type, details, event_hash, created_at) "
                        "VALUES (:id, :org, 'SYSTEM', 'rls-test', 'test.created', 'test', '{}'::jsonb, :hash, now())"
                    ),
                    {"id": event_id, "org": organization_id, "hash": event_id.replace("-", "")},
                )
        with tenant.begin() as connection:
            connection.execute(
                text("SELECT set_config('app.organization_id', :org, true)"),
                {"org": organization_a},
            )
            rows = connection.execute(
                text("SELECT organization_id FROM audit_events ORDER BY organization_id")
            ).scalars().all()
            assert rows == [organization_a]
            with pytest.raises(DBAPIError):
                with connection.begin_nested():
                    connection.execute(
                        text(
                            "INSERT INTO audit_events "
                            "(id, organization_id, actor_type, actor_id, action, resource_type, details, event_hash, created_at) "
                            "VALUES (:id, :org, 'SYSTEM', 'rls-test', 'test.denied', 'test', '{}'::jsonb, :hash, now())"
                        ),
                        {
                            "id": str(uuid.uuid4()),
                            "org": organization_b,
                            "hash": uuid.uuid4().hex,
                        },
                    )
    finally:
        with admin.begin() as connection:
            connection.execute(
                text("SELECT set_config('app.allow_audit_purge', 'true', true)")
            )
            connection.execute(
                text("DELETE FROM organizations WHERE id IN (:a, :b)"),
                {"a": organization_a, "b": organization_b},
            )
        tenant.dispose()
        admin.dispose()


@pytest.mark.skipif(not ADMIN_URL, reason="PostgreSQL integration URL is not configured")
def test_postgres_usage_reservations_enforce_quota_under_concurrency() -> None:
    organization_id = str(uuid.uuid4())
    workspace_id = str(uuid.uuid4())
    admin = create_engine(ADMIN_URL)
    with admin.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO organizations "
                "(id, name, slug, status, billing_email, raw_content_retention_days, created_at, updated_at) "
                "VALUES (:id, 'Quota tenant', :slug, 'ACTIVE', 'quota@example.com', 30, now(), now())"
            ),
            {"id": organization_id, "slug": f"quota-{organization_id[:8]}"},
        )
        connection.execute(
            text(
                "INSERT INTO workspaces "
                "(id, organization_id, name, slug, industry_template, status, created_at, updated_at) "
                "VALUES (:id, :org, 'Support', 'support', 'GENERAL', 'ACTIVE', now(), now())"
            ),
            {"id": workspace_id, "org": organization_id},
        )
        connection.execute(
            text(
                "INSERT INTO billing_accounts "
                "(organization_id, status, payment_method_present, created_at, updated_at) "
                "VALUES (:org, 'FREE', false, now(), now())"
            ),
            {"org": organization_id},
        )
    settings = replace(
        get_settings(),
        database_url=ADMIN_URL,
        free_decisions_per_month=2,
        provider_cost_cap_cents=0,
    )

    def reserve(index: int) -> int:
        database = Database(settings)
        try:
            with database.session() as session:
                set_tenant_database_context(session, organization_id)
                reserve_usage(
                    session,
                    settings,
                    organization_id,
                    workspace_id,
                    f"concurrent-{index}",
                )
            return 200
        except APIError as exc:
            return exc.status_code
        finally:
            database.dispose()

    try:
        with ThreadPoolExecutor(max_workers=3) as executor:
            statuses = sorted(executor.map(reserve, range(3)))
        assert statuses == [200, 200, 402]
    finally:
        with admin.begin() as connection:
            connection.execute(
                text("DELETE FROM organizations WHERE id = :id"),
                {"id": organization_id},
            )
        admin.dispose()
