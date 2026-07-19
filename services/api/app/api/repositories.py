from typing import Annotated

from fastapi import APIRouter, File, Request, Response, UploadFile, status
from starlette.concurrency import run_in_threadpool

from app.domain.repositories import GitHubIngestionRequest, RepositoryWorkspace
from app.domain.indexing import RepositoryIndex, RepositorySearchRequest, RepositorySearchResponse
from app.domain.parsing import RepositoryParseResult
from app.services.repository_ingestion import RepositoryIngestionService
from app.services.repository_indexing import RepositoryIndexingService
from app.services.repository_parsing import RepositoryParsingService

router = APIRouter(prefix="/api/v1/repositories", tags=["repositories"])


def get_service(request: Request) -> RepositoryIngestionService:
    return request.app.state.repository_ingestion


def get_parsing_service(request: Request) -> RepositoryParsingService:
    return request.app.state.repository_parsing


def get_indexing_service(request: Request) -> RepositoryIndexingService:
    return request.app.state.repository_indexing


@router.post("/github", response_model=RepositoryWorkspace, status_code=status.HTTP_201_CREATED)
async def ingest_github(payload: GitHubIngestionRequest, request: Request) -> RepositoryWorkspace:
    return await run_in_threadpool(get_service(request).ingest_github, payload.repository_url)


@router.post("/uploads", response_model=RepositoryWorkspace, status_code=status.HTTP_201_CREATED)
async def ingest_upload(
    repository: Annotated[UploadFile, File(description="A ZIP archive containing a repository")],
    request: Request,
) -> RepositoryWorkspace:
    return await get_service(request).ingest_upload(repository)


@router.post("/{workspace_id}/parse", response_model=RepositoryParseResult)
async def parse_repository(workspace_id: str, request: Request) -> RepositoryParseResult:
    return await run_in_threadpool(get_parsing_service(request).parse, workspace_id)


@router.post("/{workspace_id}/index", response_model=RepositoryIndex)
async def index_repository(workspace_id: str, request: Request) -> RepositoryIndex:
    return await run_in_threadpool(get_indexing_service(request).build, workspace_id)


@router.get("/{workspace_id}/index", response_model=RepositoryIndex)
def get_repository_index(workspace_id: str, request: Request) -> RepositoryIndex:
    return get_indexing_service(request).get(workspace_id)


@router.post("/{workspace_id}/search", response_model=RepositorySearchResponse)
def search_repository(
    workspace_id: str,
    payload: RepositorySearchRequest,
    request: Request,
) -> RepositorySearchResponse:
    return get_indexing_service(request).search(workspace_id, payload.query, payload.limit)


@router.get("/{workspace_id}", response_model=RepositoryWorkspace)
def get_repository(workspace_id: str, request: Request) -> RepositoryWorkspace:
    return get_service(request).get(workspace_id)


@router.delete("/{workspace_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_repository(workspace_id: str, request: Request) -> Response:
    get_indexing_service(request).delete(workspace_id)
    get_service(request).delete(workspace_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
