from __future__ import annotations

from celery import Celery

from api.config import get_settings
from api.db.base import Database
from api.services.knowledge import process_document_version
from api.services.object_storage import create_object_storage
from api.services.billing import reconcile_meter_outbox, report_meter_events
from api.services.email import deliver_pending as deliver_pending_email
from api.services.retention import redact_expired_content
from api.services.webhooks import deliver_pending
from api.db.models import BackgroundJob, DocumentVersion
from api.tenancy import set_platform_database_context, set_tenant_database_context
from sqlalchemy import select
from datetime import datetime, timezone


settings = get_settings()
celery_app = Celery("agentmesh", broker=settings.redis_url, backend=settings.redis_url)
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)


@celery_app.task(
    name="agentmesh.process_document",
    autoretry_for=(RuntimeError,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 4},
)
def process_document(document_version_id: str) -> None:
    database = Database(settings)
    storage = create_object_storage(settings)
    failed = False
    try:
        with database.session() as session:
            set_platform_database_context(session, True)
            process_document_version(session, storage, document_version_id)
            version = session.get(DocumentVersion, document_version_id)
            failed = bool(version and version.status == "FAILED")
    finally:
        database.dispose()
    if failed:
        raise RuntimeError("Document ingestion failed")


def enqueue_document(document_version_id: str) -> None:
    if settings.tasks_eager:
        process_document(document_version_id)
    else:
        process_document.delay(document_version_id)


@celery_app.task(name="agentmesh.report_meter_events")
def report_usage_to_stripe() -> int:
    if not settings.stripe_secret_key:
        return 0
    database = Database(settings)
    try:
        return report_meter_events(database, settings)
    finally:
        database.dispose()


@celery_app.task(name="agentmesh.reconcile_meter_outbox")
def reconcile_usage_with_stripe_outbox() -> int:
    database = Database(settings)
    try:
        return reconcile_meter_outbox(database, settings)
    finally:
        database.dispose()


@celery_app.task(name="agentmesh.deliver_webhooks")
def deliver_webhooks() -> int:
    database = Database(settings)
    try:
        return deliver_pending(database, settings)
    finally:
        database.dispose()


@celery_app.task(name="agentmesh.deliver_email")
def deliver_email() -> int:
    database = Database(settings)
    try:
        return deliver_pending_email(database, settings)
    finally:
        database.dispose()


@celery_app.task(name="agentmesh.enforce_retention")
def enforce_retention() -> int:
    database = Database(settings)
    try:
        return redact_expired_content(database)
    finally:
        database.dispose()


@celery_app.task(name="agentmesh.delete_stored_documents")
def delete_stored_documents(limit: int = 50) -> int:
    database = Database(settings)
    storage = create_object_storage(settings)
    completed = 0
    try:
        with database.session() as session:
            set_platform_database_context(session, True)
            jobs = session.scalars(
                select(BackgroundJob)
                .where(
                    BackgroundJob.job_type == "DELETE_STORED_DOCUMENT",
                    BackgroundJob.status.in_(["PENDING", "RETRY"]),
                )
                .order_by(BackgroundJob.created_at)
                .limit(limit)
            ).all()
            for job in jobs:
                if job.organization_id:
                    set_tenant_database_context(session, job.organization_id)
                try:
                    storage.delete(str(job.payload["storage_key"]))
                    job.status = "COMPLETED"
                    job.completed_at = datetime.now(timezone.utc)
                    job.error = None
                    completed += 1
                except Exception as exc:
                    job.attempts += 1
                    job.status = "FAILED" if job.attempts >= 8 else "RETRY"
                    job.error = str(exc)[:500]
        return completed
    finally:
        database.dispose()


celery_app.conf.beat_schedule = {
    "report-meter-events-every-minute": {
        "task": "agentmesh.report_meter_events",
        "schedule": 60.0,
    },
    "deliver-webhooks-every-minute": {
        "task": "agentmesh.deliver_webhooks",
        "schedule": 60.0,
    },
    "deliver-email-every-minute": {
        "task": "agentmesh.deliver_email",
        "schedule": 60.0,
    },
    "delete-stored-documents-every-five-minutes": {
        "task": "agentmesh.delete_stored_documents",
        "schedule": 300.0,
    },
    "enforce-retention-daily": {
        "task": "agentmesh.enforce_retention",
        "schedule": 86400.0,
    },
    "reconcile-meter-outbox-daily": {
        "task": "agentmesh.reconcile_meter_outbox",
        "schedule": 86400.0,
    },
}
