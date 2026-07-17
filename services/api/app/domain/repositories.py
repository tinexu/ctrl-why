from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class RepositorySourceType(str, Enum):
    github = "github"
    upload = "upload"


class RepositoryWorkspace(BaseModel):
    id: str
    name: str
    source_type: RepositorySourceType
    source_reference: str
    created_at: datetime
    expires_at: datetime
    file_count: int = Field(ge=0)
    total_bytes: int = Field(ge=0)


class GitHubIngestionRequest(BaseModel):
    repository_url: str = Field(min_length=1, max_length=500)


class IngestionError(Exception):
    """A safe, user-visible repository ingestion failure."""


class InvalidRepositoryError(IngestionError):
    pass


class RepositoryLimitError(IngestionError):
    pass


class RepositoryAcquisitionError(IngestionError):
    pass


class WorkspaceNotFoundError(IngestionError):
    pass

