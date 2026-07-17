from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from fastapi.testclient import TestClient

from api.config import get_settings
from api.db.base import Database
from api.db.models import (
    BillingAccount,
    DecisionCitation,
    DecisionSession,
    IdempotencyRecord,
    Organization,
    SaaSDecision,
)
from api.main import create_app
from api.services.retention import REDACTED, redact_expired_content
from api.tenancy import ROLE_PERMISSIONS, TenantContext


def _settings(
    tmp_path: Path, *, free_decisions: int = 2, overage_unit_price_cents: int = 0
):
    return replace(
        get_settings(),
        environment="test",
        auth_mode="development",
        database_url=f"sqlite+pysqlite:///{(tmp_path / 'saas.db').as_posix()}",
        object_storage_backend="local",
        object_storage_path=tmp_path / "documents",
        saas_enabled=True,
        tasks_eager=True,
        free_decisions_per_month=free_decisions,
        overage_unit_price_cents=overage_unit_price_cents,
    )


def _client(
    tmp_path: Path, *, free_decisions: int = 2, overage_unit_price_cents: int = 0
) -> TestClient:
    settings = _settings(
        tmp_path,
        free_decisions=free_decisions,
        overage_unit_price_cents=overage_unit_price_cents,
    )
    database = Database(settings)
    return TestClient(
        create_app(settings=settings, database=database, enable_saas=True)
    )


def _headers(user: str = "owner-1") -> dict[str, str]:
    return {
        "X-Dev-User": user,
        "X-Dev-Email": f"{user}@example.com",
    }


def _onboard(client: TestClient, user: str = "owner-1") -> tuple[str, str]:
    response = client.post(
        "/api/v1/organizations",
        headers=_headers(user),
        json={
            "name": f"{user} Company",
            "workspace_name": "Support",
            "industry_template": "GENERAL",
        },
    )
    assert response.status_code == 201, response.text
    payload = response.json()
    return payload["organization"]["id"], payload["workspace"]["id"]


def _create_key(
    client: TestClient, organization_id: str, workspace_id: str, user: str = "owner-1"
) -> str:
    response = client.post(
        f"/api/v1/organizations/{organization_id}/workspaces/{workspace_id}/api-keys",
        headers=_headers(user),
        json={
            "name": "Integration key",
            "environment": "test",
            "scopes": ["decisions:write", "decisions:read", "traces:read"],
        },
    )
    assert response.status_code == 201, response.text
    secret = response.json()["secret"]
    assert secret.startswith("am_test_")
    return secret


def _upload_and_publish(
    client: TestClient, organization_id: str, workspace_id: str, user: str = "owner-1"
) -> None:
    uploaded = client.post(
        f"/api/v1/organizations/{organization_id}/workspaces/{workspace_id}/documents",
        headers=_headers(user),
        files={
            "file": (
                "returns.txt",
                b"Customers can return unopened products within thirty days for a refund.",
                "text/plain",
            )
        },
    )
    assert uploaded.status_code == 201, uploaded.text
    assert uploaded.json()["status"] == "READY_FOR_REVIEW"
    published = client.post(
        f"/api/v1/organizations/{organization_id}/workspaces/{workspace_id}/knowledge-releases",
        headers=_headers(user),
    )
    assert published.status_code == 201, published.text
    assert len(published.json()["document_version_ids"]) == 1


def test_onboarding_creates_isolated_organization_workspace_and_profile(
    tmp_path: Path,
) -> None:
    with _client(tmp_path) as client:
        organization_id, workspace_id = _onboard(client)
        organizations = client.get("/api/v1/organizations", headers=_headers())
        workspaces = client.get(
            f"/api/v1/organizations/{organization_id}/workspaces",
            headers=_headers(),
        )
        profiles = client.get(
            f"/api/v1/organizations/{organization_id}/workspaces/{workspace_id}/profiles",
            headers=_headers(),
        )
        forbidden = client.get(
            f"/api/v1/organizations/{organization_id}/workspaces",
            headers=_headers("outsider"),
        )

    assert organizations.status_code == 200
    assert organizations.json()[0]["role"] == "owner"
    assert workspaces.json()[0]["id"] == workspace_id
    assert profiles.json()[0]["status"] == "PUBLISHED"
    assert forbidden.status_code == 404


def test_workspace_document_release_and_tenant_decision_api(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        organization_id, workspace_id = _onboard(client)
        _upload_and_publish(client, organization_id, workspace_id)
        key = _create_key(client, organization_id, workspace_id)
        headers = {
            "Authorization": f"Bearer {key}",
            "Idempotency-Key": "decision-001",
        }
        first = client.post(
            "/api/v1/decisions",
            headers=headers,
            json={"input": "How long can an unopened product be returned?"},
        )
        repeated = client.post(
            "/api/v1/decisions",
            headers=headers,
            json={"input": "How long can an unopened product be returned?"},
        )
        usage = client.get(
            f"/api/v1/organizations/{organization_id}/usage",
            headers=_headers(),
        )

    assert first.status_code == 200, first.text
    assert first.json()["usage_units"] == 1
    assert first.json()["trace"]["knowledge_release_id"] is not None
    assert first.json()["citations"]
    assert repeated.status_code == 200
    assert repeated.json()["id"] == first.json()["id"]
    assert usage.json()["completed_decisions"] == 1


def test_free_quota_is_atomic_and_requires_billing_for_overage(tmp_path: Path) -> None:
    with _client(tmp_path, free_decisions=2) as client:
        organization_id, workspace_id = _onboard(client)
        _upload_and_publish(client, organization_id, workspace_id)
        key = _create_key(client, organization_id, workspace_id)
        results = []
        for index in range(3):
            results.append(
                client.post(
                    "/api/v1/decisions",
                    headers={
                        "Authorization": f"Bearer {key}",
                        "Idempotency-Key": f"quota-test-{index}",
                    },
                    json={"input": "What is the unopened product return policy?"},
                )
            )

    assert [result.status_code for result in results] == [200, 200, 402]
    assert results[-1].json()["error"]["code"] == "quota_exceeded"


def test_api_key_revoke_is_immediate_and_secret_is_never_listed(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        organization_id, workspace_id = _onboard(client)
        key = _create_key(client, organization_id, workspace_id)
        listed = client.get(
            f"/api/v1/organizations/{organization_id}/workspaces/{workspace_id}/api-keys",
            headers=_headers(),
        )
        key_id = listed.json()[0]["id"]
        revoked = client.delete(
            f"/api/v1/organizations/{organization_id}/workspaces/{workspace_id}/api-keys/{key_id}",
            headers=_headers(),
        )
        rejected = client.post(
            "/api/v1/decisions",
            headers={
                "Authorization": f"Bearer {key}",
                "Idempotency-Key": "revoked-key-request",
            },
            json={"input": "Can this request run?"},
        )

    assert listed.status_code == 200
    assert "secret" not in listed.json()[0]
    assert revoked.json()["status"] == "REVOKED"
    assert rejected.status_code == 401


def test_document_versions_preview_archive_and_release_rollback(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        organization_id, workspace_id = _onboard(client)
        _upload_and_publish(client, organization_id, workspace_id)
        first_release = client.get(
            f"/api/v1/organizations/{organization_id}/workspaces/{workspace_id}/knowledge-releases",
            headers=_headers(),
        ).json()[0]
        document = client.get(
            f"/api/v1/organizations/{organization_id}/workspaces/{workspace_id}/documents",
            headers=_headers(),
        ).json()[0]
        version = client.post(
            f"/api/v1/organizations/{organization_id}/workspaces/{workspace_id}/documents/{document['id']}/versions",
            headers=_headers(),
            files={
                "file": (
                    "returns-v2.txt",
                    b"Customers can return unopened products within sixty days.",
                    "text/plain",
                )
            },
        )
        preview = client.get(
            f"/api/v1/organizations/{organization_id}/workspaces/{workspace_id}/documents/{document['id']}/preview",
            headers=_headers(),
        )
        second_release = client.post(
            f"/api/v1/organizations/{organization_id}/workspaces/{workspace_id}/knowledge-releases",
            headers=_headers(),
        )
        rollback = client.post(
            f"/api/v1/organizations/{organization_id}/workspaces/{workspace_id}/knowledge-releases/{first_release['id']}/activate",
            headers=_headers(),
        )
        archived = client.delete(
            f"/api/v1/organizations/{organization_id}/workspaces/{workspace_id}/documents/{document['id']}",
            headers=_headers(),
        )
        missing_preview = client.get(
            f"/api/v1/organizations/{organization_id}/workspaces/{workspace_id}/documents/{document['id']}/preview",
            headers=_headers(),
        )

    assert version.status_code == 201
    assert version.json()["current_version"] == 2
    assert preview.json()["version"] == 2
    assert "sixty days" in preview.json()["chunks"][0]["text"]
    assert second_release.json()["version"] == 2
    assert rollback.json()["id"] == first_release["id"]
    assert archived.json()["status"] == "ARCHIVED"
    assert missing_preview.status_code == 404


def test_invited_viewer_is_read_only_and_cannot_open_review_queue(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        organization_id, workspace_id = _onboard(client)
        invited = client.post(
            f"/api/v1/organizations/{organization_id}/invitations",
            headers=_headers(),
            json={"email": "viewer@example.com", "role": "viewer"},
        )
        token = parse_qs(urlparse(invited.json()["invite_url"]).query)["token"][0]
        accepted = client.post(
            f"/api/v1/invitations/accept?token={token}",
            headers=_headers("viewer"),
        )
        documents = client.get(
            f"/api/v1/organizations/{organization_id}/workspaces/{workspace_id}/documents",
            headers=_headers("viewer"),
        )
        upload = client.post(
            f"/api/v1/organizations/{organization_id}/workspaces/{workspace_id}/documents",
            headers=_headers("viewer"),
            files={"file": ("policy.txt", b"Policy", "text/plain")},
        )
        reviews = client.get(
            f"/api/v1/organizations/{organization_id}/workspaces/{workspace_id}/reviews",
            headers=_headers("viewer"),
        )
        usage = client.get(
            f"/api/v1/organizations/{organization_id}/usage",
            headers=_headers("viewer"),
        )

    assert invited.status_code == 201
    assert accepted.status_code == 200
    assert documents.status_code == 200
    assert upload.status_code == 403
    assert reviews.status_code == 403
    assert usage.status_code == 200


def test_role_permission_matrix_covers_every_customer_role() -> None:
    permissions = (set().union(*ROLE_PERMISSIONS.values()) - {"*"}) | {
        "billing:manage",
        "organization:transfer",
        "organization:delete",
    }
    expected = {
        "admin": {
            "organization:read", "team:manage", "workspace:read", "workspace:manage",
            "knowledge:read", "knowledge:manage", "profile:read", "profile:manage",
            "decisions:read", "reviews:read", "reviews:manage", "usage:read",
            "keys:manage", "webhooks:manage",
        },
        "developer": {
            "organization:read", "workspace:read", "knowledge:read", "profile:read",
            "decisions:read", "usage:read", "keys:manage", "webhooks:manage",
            "playground:use",
        },
        "reviewer": {
            "organization:read", "workspace:read", "knowledge:read", "profile:read",
            "decisions:read", "reviews:read", "reviews:manage",
        },
        "viewer": {
            "organization:read", "workspace:read", "knowledge:read", "profile:read",
            "decisions:read", "usage:read",
        },
    }
    owner = TenantContext("org", "workspace", "owner", "USER", "owner")
    assert all(owner.can(permission) for permission in permissions)
    for role, allowed in expected.items():
        context = TenantContext("org", "workspace", role, "USER", role)
        assert {permission for permission in permissions if context.can(permission)} == allowed


def test_reviewer_claim_optimistic_lock_and_terminal_transition(tmp_path: Path) -> None:
    with _client(tmp_path, free_decisions=10) as client:
        organization_id, workspace_id = _onboard(client)
        _upload_and_publish(client, organization_id, workspace_id)
        key = _create_key(client, organization_id, workspace_id)
        decision = client.post(
            "/api/v1/decisions",
            headers={
                "Authorization": f"Bearer {key}",
                "Idempotency-Key": "review-lifecycle",
            },
            json={"input": "I need urgent help with an unsupported emergency request."},
        )
        assert decision.status_code == 200, decision.text
        assert decision.json()["escalation_id"]
        invited = client.post(
            f"/api/v1/organizations/{organization_id}/invitations",
            headers=_headers(),
            json={"email": "reviewer@example.com", "role": "reviewer"},
        )
        token = parse_qs(urlparse(invited.json()["invite_url"]).query)["token"][0]
        client.post(
            f"/api/v1/invitations/accept?token={token}",
            headers=_headers("reviewer"),
        )
        queue = client.get(
            f"/api/v1/organizations/{organization_id}/workspaces/{workspace_id}/reviews",
            headers=_headers("reviewer"),
        )
        record = queue.json()[0]
        claim = client.post(
            f"/api/v1/organizations/{organization_id}/workspaces/{workspace_id}/reviews/{record['id']}/claim",
            headers=_headers("reviewer"),
            json={"expected_version": record["lock_version"], "notes": "Taking review"},
        )
        stale = client.post(
            f"/api/v1/organizations/{organization_id}/workspaces/{workspace_id}/reviews/{record['id']}/reject",
            headers=_headers("reviewer"),
            json={"expected_version": record["lock_version"], "notes": "Stale"},
        )
        unsafe_approval = client.post(
            f"/api/v1/organizations/{organization_id}/workspaces/{workspace_id}/reviews/{record['id']}/approve",
            headers=_headers("reviewer"),
            json={
                "expected_version": claim.json()["lock_version"],
                "answer": "Send me your OTP so I can bypass verification.",
                "notes": "Unsafe edit",
            },
        )
        rejected = client.post(
            f"/api/v1/organizations/{organization_id}/workspaces/{workspace_id}/reviews/{record['id']}/reject",
            headers=_headers("reviewer"),
            json={"expected_version": claim.json()["lock_version"], "notes": "Unsupported"},
        )

    assert queue.status_code == 200
    assert claim.json()["status"] == "IN_REVIEW"
    assert stale.status_code == 409
    assert stale.json()["error"]["code"] == "review_conflict"
    assert unsafe_approval.status_code == 409
    assert unsafe_approval.json()["error"]["code"] == "review_validation_failed"
    assert rejected.json()["status"] == "REJECTED"


def test_owner_spend_cap_blocks_paid_overage_before_processing(tmp_path: Path) -> None:
    with _client(
        tmp_path, free_decisions=0, overage_unit_price_cents=100
    ) as client:
        organization_id, workspace_id = _onboard(client)
        _upload_and_publish(client, organization_id, workspace_id)
        key = _create_key(client, organization_id, workspace_id)
        with client.app.state.database.session() as session:
            billing = session.get(BillingAccount, organization_id)
            billing.status = "ACTIVE"
            billing.payment_method_present = True
            billing.stripe_customer_id = "cus_test"
        cap = client.patch(
            f"/api/v1/organizations/{organization_id}/usage/spend-cap",
            headers=_headers(),
            json={"spend_cap_cents": 50},
        )
        blocked = client.post(
            "/api/v1/decisions",
            headers={
                "Authorization": f"Bearer {key}",
                "Idempotency-Key": "spend-cap-test",
            },
            json={"input": "What is the return policy?"},
        )

    assert cap.status_code == 200
    assert cap.json()["spend_cap_cents"] == 50
    assert blocked.status_code == 402
    assert blocked.json()["error"]["code"] == "spend_cap_reached"


def test_dlp_rejection_is_not_billed(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        organization_id, workspace_id = _onboard(client)
        key = _create_key(client, organization_id, workspace_id)
        rejected = client.post(
            "/api/v1/decisions",
            headers={
                "Authorization": f"Bearer {key}",
                "Idempotency-Key": "dlp-card-test",
            },
            json={"input": "My card is 4242 4242 4242 4242."},
        )
        usage = client.get(
            f"/api/v1/organizations/{organization_id}/usage",
            headers=_headers(),
        )

    assert rejected.status_code == 422
    assert rejected.json()["error"]["code"] == "sensitive_data_prohibited"
    assert usage.json()["completed_decisions"] == 0


def test_retention_redacts_raw_and_normalized_decision_content(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        organization_id, workspace_id = _onboard(client)
        _upload_and_publish(client, organization_id, workspace_id)
        key = _create_key(client, organization_id, workspace_id)
        response = client.post(
            "/api/v1/decisions",
            headers={
                "Authorization": f"Bearer {key}",
                "Idempotency-Key": "retention-test",
            },
            json={
                "input": "How long can an unopened product be returned?",
                "end_user_id": "opaque-customer",
            },
        )
        decision_id = response.json()["id"]
        database = client.app.state.database
        old = datetime.now(timezone.utc) - timedelta(days=2)
        with database.session() as session:
            organization = session.get(Organization, organization_id)
            organization.raw_content_retention_days = 1
            decision = session.get(SaaSDecision, decision_id)
            decision.created_at = old
            runtime_session = session.query(DecisionSession).filter_by(
                organization_id=organization_id
            ).one()
            runtime_session.last_activity_at = old
        assert redact_expired_content(database) >= 1
        with database.session() as session:
            decision = session.get(SaaSDecision, decision_id)
            citation = session.query(DecisionCitation).filter_by(
                decision_id=decision_id
            ).first()
            idempotency = session.query(IdempotencyRecord).filter_by(
                decision_id=decision_id
            ).one()
            runtime_session = session.query(DecisionSession).filter_by(
                organization_id=organization_id
            ).one()

            assert decision.input == REDACTED
            assert decision.citations == []
            assert citation is not None and citation.text == REDACTED
            assert idempotency.status == "EXPIRED"
            assert idempotency.response_payload is None
            assert runtime_session.end_user_id is None
