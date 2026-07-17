from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.health import router as health_router
from app.api.repositories import router as repositories_router
from app.core.config import Settings, get_settings
from app.domain.repositories import (
    InvalidRepositoryError,
    RepositoryAcquisitionError,
    RepositoryLimitError,
    WorkspaceNotFoundError,
)
from app.ingestion.workspaces import WorkspaceStore
from app.services.repository_ingestion import RepositoryIngestionService


def create_app(settings: Settings | None = None) -> FastAPI:
    runtime_settings = settings or get_settings()
    workspaces = WorkspaceStore(
        ttl_seconds=runtime_settings.repository_workspace_ttl_seconds,
        temp_root=runtime_settings.repository_temp_root,
    )

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        yield
        workspaces.close()

    application = FastAPI(
        title="WTF Does This Repo Do? API",
        version="0.1.0",
        docs_url="/docs" if runtime_settings.app_env != "production" else None,
        redoc_url=None,
        lifespan=lifespan,
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=runtime_settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["Content-Type", "Authorization"],
    )
    application.state.repository_ingestion = RepositoryIngestionService(runtime_settings, workspaces)
    application.include_router(health_router)
    application.include_router(repositories_router)

    application.add_exception_handler(
        InvalidRepositoryError,
        lambda _, error: JSONResponse(status_code=400, content={"detail": str(error)}),
    )
    application.add_exception_handler(
        RepositoryLimitError,
        lambda _, error: JSONResponse(status_code=413, content={"detail": str(error)}),
    )
    application.add_exception_handler(
        RepositoryAcquisitionError,
        lambda _, error: JSONResponse(status_code=502, content={"detail": str(error)}),
    )
    application.add_exception_handler(
        WorkspaceNotFoundError,
        lambda _, error: JSONResponse(status_code=404, content={"detail": str(error)}),
    )
    return application


app = create_app()
