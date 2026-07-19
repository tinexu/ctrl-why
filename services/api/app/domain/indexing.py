from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

from app.domain.parsing import SourceFile, SourceSymbol


class GraphNodeType(str, Enum):
    file = "file"
    symbol = "symbol"
    external_module = "external_module"


class GraphEdgeType(str, Enum):
    contains = "contains"
    imports = "imports"
    calls = "calls"


class GraphNode(BaseModel):
    id: str
    type: GraphNodeType
    label: str
    path: str | None = None
    entity_id: str | None = None
    metadata: dict[str, str] = Field(default_factory=dict)


class GraphEdge(BaseModel):
    id: str
    source_id: str
    target_id: str
    type: GraphEdgeType
    line: int | None = Field(default=None, ge=1)
    label: str
    confidence: float = Field(ge=0, le=1)


class CodeChunk(BaseModel):
    id: str
    file_id: str
    symbol_id: str | None = None
    path: str
    start_line: int = Field(ge=1)
    end_line: int = Field(ge=1)
    content: str = Field(exclude=True)
    content_hash: str
    token_estimate: int = Field(ge=0)


class IndexStats(BaseModel):
    file_count: int = Field(ge=0)
    symbol_count: int = Field(ge=0)
    edge_count: int = Field(ge=0)
    chunk_count: int = Field(ge=0)
    embedded_chunk_count: int = Field(ge=0)
    languages: dict[str, int]


class RepositoryIndex(BaseModel):
    workspace_id: str
    indexed_at: datetime
    files: list[SourceFile]
    symbols: list[SourceSymbol]
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    chunks: list[CodeChunk]
    stats: IndexStats
