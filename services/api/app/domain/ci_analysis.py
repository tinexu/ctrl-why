from enum import Enum

from pydantic import BaseModel, Field

from app.domain.indexing import RepositorySearchResult


class FailureCategory(str, Enum):
    test = "test"
    typecheck = "typecheck"
    lint = "lint"
    build = "build"
    dependency = "dependency"
    configuration = "configuration"
    unknown = "unknown"


class CIAnalysisRequest(BaseModel):
    logs: str = Field(min_length=10, max_length=200_000)
    workflow_name: str | None = Field(default=None, max_length=200)


class LogEvidence(BaseModel):
    reference: int = Field(ge=1)
    line: int = Field(ge=1)
    content: str


class CIAnalysisResponse(BaseModel):
    workspace_id: str
    category: FailureCategory
    summary: str
    likely_root_cause: str
    confidence: float = Field(ge=0, le=1)
    ai_enhanced: bool
    failed_commands: list[str]
    affected_files: list[str]
    recommendations: list[str]
    validation_steps: list[str]
    log_evidence: list[LogEvidence]
    repository_evidence: list[RepositorySearchResult]
