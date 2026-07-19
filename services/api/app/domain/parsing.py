from enum import Enum

from pydantic import BaseModel, Field


class SourceLanguage(str, Enum):
    python = "python"
    javascript = "javascript"
    typescript = "typescript"
    tsx = "tsx"


class SymbolKind(str, Enum):
    function = "function"
    method = "method"
    class_ = "class"
    interface = "interface"
    type_alias = "type_alias"


class SourceFile(BaseModel):
    id: str
    path: str
    language: SourceLanguage
    size_bytes: int = Field(ge=0)
    line_count: int = Field(ge=0)
    syntax_error_count: int = Field(ge=0)


class SourceSymbol(BaseModel):
    id: str
    file_id: str
    name: str
    qualified_name: str
    kind: SymbolKind
    start_line: int = Field(ge=1)
    start_column: int = Field(ge=1)
    end_line: int = Field(ge=1)
    end_column: int = Field(ge=1)
    signature: str


class RepositoryParseResult(BaseModel):
    workspace_id: str
    files: list[SourceFile]
    symbols: list[SourceSymbol]
    skipped_file_count: int = Field(ge=0)
    syntax_error_count: int = Field(ge=0)

