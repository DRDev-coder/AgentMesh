from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, File, Request, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.auth import Principal, get_principal
from api.db.models import DocumentVersion
from api.saas_schemas import DocumentPreview, DocumentView, KnowledgeReleaseView
from api.services import knowledge
from api.tenancy import get_db_session, workspace_context
from api.worker import enqueue_document


router = APIRouter(tags=["knowledge"])


@router.get(
    "/organizations/{organization_id}/workspaces/{workspace_id}/documents",
    response_model=list[DocumentView],
)
def documents(
    organization_id: str,
    workspace_id: str,
    session: Session = Depends(get_db_session),
    principal: Principal = Depends(get_principal),
) -> list[DocumentView]:
    workspace_context(
        organization_id, workspace_id, "knowledge:read", session, principal
    )
    return knowledge.list_documents(session, organization_id, workspace_id)


@router.post(
    "/organizations/{organization_id}/workspaces/{workspace_id}/documents",
    response_model=DocumentView,
    status_code=201,
)
async def upload_document(
    request: Request,
    background_tasks: BackgroundTasks,
    organization_id: str,
    workspace_id: str,
    file: UploadFile = File(),
    session: Session = Depends(get_db_session),
    principal: Principal = Depends(get_principal),
) -> DocumentView:
    context = workspace_context(
        organization_id, workspace_id, "knowledge:manage", session, principal
    )
    content = await file.read(request.app.state.settings.document_max_bytes + 1)
    result = knowledge.create_document(
        session,
        request.app.state.object_storage,
        request.app.state.settings,
        context,
        file.filename or "document",
        file.content_type or "application/octet-stream",
        content,
    )
    version_id = session.scalar(
        select(DocumentVersion.id).where(DocumentVersion.document_id == result.id)
    )
    session.commit()
    if version_id:
        if request.app.state.settings.tasks_eager:
            knowledge.process_document_version(
                session, request.app.state.object_storage, version_id
            )
            session.commit()
            refreshed = knowledge.list_documents(session, organization_id, workspace_id)
            result = next(item for item in refreshed if item.id == result.id)
        else:
            background_tasks.add_task(enqueue_document, version_id)
    return result


@router.post(
    "/organizations/{organization_id}/workspaces/{workspace_id}/documents/{document_id}/versions",
    response_model=DocumentView,
    status_code=201,
)
async def upload_document_version(
    request: Request,
    background_tasks: BackgroundTasks,
    organization_id: str,
    workspace_id: str,
    document_id: str,
    file: UploadFile = File(),
    session: Session = Depends(get_db_session),
    principal: Principal = Depends(get_principal),
) -> DocumentView:
    context = workspace_context(
        organization_id, workspace_id, "knowledge:manage", session, principal
    )
    content = await file.read(request.app.state.settings.document_max_bytes + 1)
    result, version_id = knowledge.create_document_version(
        session,
        request.app.state.object_storage,
        request.app.state.settings,
        context,
        document_id,
        file.filename or "document",
        file.content_type or "application/octet-stream",
        content,
    )
    session.commit()
    if request.app.state.settings.tasks_eager:
        knowledge.process_document_version(
            session, request.app.state.object_storage, version_id
        )
        session.commit()
        refreshed = knowledge.list_documents(session, organization_id, workspace_id)
        result = next(item for item in refreshed if item.id == document_id)
    else:
        background_tasks.add_task(enqueue_document, version_id)
    return result


@router.get(
    "/organizations/{organization_id}/workspaces/{workspace_id}/documents/{document_id}/preview",
    response_model=DocumentPreview,
)
def preview_document(
    organization_id: str,
    workspace_id: str,
    document_id: str,
    session: Session = Depends(get_db_session),
    principal: Principal = Depends(get_principal),
) -> DocumentPreview:
    context = workspace_context(
        organization_id, workspace_id, "knowledge:read", session, principal
    )
    return knowledge.preview_document(session, context, document_id)


@router.delete(
    "/organizations/{organization_id}/workspaces/{workspace_id}/documents/{document_id}",
    response_model=DocumentView,
)
def archive_document(
    organization_id: str,
    workspace_id: str,
    document_id: str,
    session: Session = Depends(get_db_session),
    principal: Principal = Depends(get_principal),
) -> DocumentView:
    context = workspace_context(
        organization_id, workspace_id, "knowledge:manage", session, principal
    )
    return knowledge.archive_document(session, context, document_id)


@router.get(
    "/organizations/{organization_id}/workspaces/{workspace_id}/knowledge-releases",
    response_model=list[KnowledgeReleaseView],
)
def knowledge_releases(
    organization_id: str,
    workspace_id: str,
    session: Session = Depends(get_db_session),
    principal: Principal = Depends(get_principal),
) -> list[KnowledgeReleaseView]:
    workspace_context(
        organization_id, workspace_id, "knowledge:read", session, principal
    )
    return knowledge.list_releases(session, organization_id, workspace_id)


@router.post(
    "/organizations/{organization_id}/workspaces/{workspace_id}/knowledge-releases",
    response_model=KnowledgeReleaseView,
    status_code=201,
)
def publish_knowledge_release(
    organization_id: str,
    workspace_id: str,
    session: Session = Depends(get_db_session),
    principal: Principal = Depends(get_principal),
) -> KnowledgeReleaseView:
    context = workspace_context(
        organization_id, workspace_id, "knowledge:manage", session, principal
    )
    return knowledge.publish_release(session, context)


@router.post(
    "/organizations/{organization_id}/workspaces/{workspace_id}/knowledge-releases/{release_id}/activate",
    response_model=KnowledgeReleaseView,
)
def activate_knowledge_release(
    organization_id: str,
    workspace_id: str,
    release_id: str,
    session: Session = Depends(get_db_session),
    principal: Principal = Depends(get_principal),
) -> KnowledgeReleaseView:
    context = workspace_context(
        organization_id, workspace_id, "knowledge:manage", session, principal
    )
    return knowledge.activate_release(session, context, release_id)
