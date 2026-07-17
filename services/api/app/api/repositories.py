from typing import Annotated

from fastapi import APIRouter, File, Request, Response, UploadFile, status
from starlette.concurrency import run_in_threadpool

from app.domain.repositories import GitHubIngestionRequest, RepositoryWorkspace
from app.services.repository_ingestion import RepositoryIngestionService

router = APIRouter(prefix="/api/v1/repositories", tags=["repositories"])


def get_service(request: Request) -> RepositoryIngestionService:
    return request.app.state.repository_ingestion


@router.post("/github", response_model=RepositoryWorkspace, status_code=status.HTTP_201_CREATED)
async def ingest_github(payload: GitHubIngestionRequest, request: Request) -> RepositoryWorkspace:
    return await run_in_threadpool(get_service(request).ingest_github, payload.repository_url)


@router.post("/uploads", response_model=RepositoryWorkspace, status_code=status.HTTP_201_CREATED)
async def ingest_upload(
    repository: Annotated[UploadFile, File(description="A ZIP archive containing a repository")],
    request: Request,
) -> RepositoryWorkspace:
    return await get_service(request).ingest_upload(repository)


@router.get("/{workspace_id}", response_model=RepositoryWorkspace)
def get_repository(workspace_id: str, request: Request) -> RepositoryWorkspace:
    return get_service(request).get(workspace_id)


@router.delete("/{workspace_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_repository(workspace_id: str, request: Request) -> Response:
    get_service(request).delete(workspace_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

