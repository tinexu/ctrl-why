from uuid import NAMESPACE_URL, uuid5

from app.core.config import Settings
from app.domain.parsing import RepositoryParseResult, SourceFile
from app.ingestion.workspaces import WorkspaceStore
from app.parsing.discovery import discover_source_files
from app.parsing.registry import ParserRegistry
from app.parsing.symbols import count_syntax_errors, extract_symbols


class RepositoryParsingService:
    def __init__(self, settings: Settings, workspaces: WorkspaceStore, parsers: ParserRegistry) -> None:
        self._settings = settings
        self._workspaces = workspaces
        self._parsers = parsers

    def parse(self, workspace_id: str) -> RepositoryParseResult:
        workspace = self._workspaces.get(workspace_id)
        repository_root = workspace.path / "repository"
        discovery = discover_source_files(
            repository_root,
            self._settings.repository_max_source_file_bytes,
        )
        files: list[SourceFile] = []
        symbols = []
        total_syntax_errors = 0

        for discovered in discovery.files:
            source = discovered.path.read_bytes()
            tree = self._parsers.create(discovered.language).parse(source)
            syntax_error_count = count_syntax_errors(tree.root_node)
            total_syntax_errors += syntax_error_count
            file_id = str(uuid5(NAMESPACE_URL, f"{workspace_id}:{discovered.relative_path}"))
            files.append(
                SourceFile(
                    id=file_id,
                    path=discovered.relative_path,
                    language=discovered.language,
                    size_bytes=discovered.size_bytes,
                    line_count=len(source.splitlines()),
                    syntax_error_count=syntax_error_count,
                )
            )
            symbols.extend(
                extract_symbols(
                    tree.root_node,
                    source,
                    discovered.language,
                    workspace_id,
                    file_id,
                    discovered.relative_path,
                )
            )

        return RepositoryParseResult(
            workspace_id=workspace_id,
            files=files,
            symbols=symbols,
            skipped_file_count=discovery.skipped_file_count,
            syntax_error_count=total_syntax_errors,
        )
