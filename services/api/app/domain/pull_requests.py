from enum import Enum

from pydantic import BaseModel, Field


class RiskLevel(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


class ChangeKind(str, Enum):
    added = "added"
    modified = "modified"
    deleted = "deleted"
    renamed = "renamed"


class PullRequestAnalysisRequest(BaseModel):
    diff: str = Field(min_length=10, max_length=200_000)
    title: str | None = Field(default=None, max_length=300)
    description: str | None = Field(default=None, max_length=2_000)


class ChangedFile(BaseModel):
    path: str
    previous_path: str | None = None
    kind: ChangeKind
    additions: int = Field(ge=0)
    deletions: int = Field(ge=0)
    changed_lines: list[int]
    changed_symbols: list[str]
    indexed: bool


class ImpactedFile(BaseModel):
    path: str
    relationship: str
    evidence_line: int | None = Field(default=None, ge=1)
    confidence: float = Field(ge=0, le=1)


class AnalysisEvidence(BaseModel):
    reference: int = Field(ge=1)
    path: str
    start_line: int = Field(ge=1)
    end_line: int = Field(ge=1)
    description: str


class RiskFinding(BaseModel):
    severity: RiskLevel
    title: str
    explanation: str
    evidence: list[int] = Field(default_factory=list)


class PullRequestAnalysisResponse(BaseModel):
    workspace_id: str
    summary: str
    risk_score: int = Field(ge=0, le=100)
    risk_level: RiskLevel
    ai_enhanced: bool
    changed_files: list[ChangedFile]
    affected_files: list[ImpactedFile]
    behavior_changes: list[RiskFinding]
    breaking_risks: list[RiskFinding]
    suggested_tests: list[str]
    security_concerns: list[RiskFinding]
    evidence: list[AnalysisEvidence]
