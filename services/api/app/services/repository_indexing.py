from collections import Counter
from datetime import datetime, timezone

from app.domain.indexing import IndexStats, RepositoryIndex
from app.indexing.chunking import build_chunks
from app.indexing.dependencies import extract_dependencies
from app.indexing.embeddings import FeatureHashEmbedder, VectorEntry
from app.indexing.graph import build_graph
from app.indexing.store import RepositoryIndexStore
from app.ingestion.workspaces import WorkspaceStore
from app.parsing.registry import ParserRegistry
from app.services.repository_parsing import RepositoryParsingService


class RepositoryIndexingService:
    def __init__(
        self,
        workspaces: WorkspaceStore,
        parsing: RepositoryParsingService,
        parsers: ParserRegistry,
        indexes: RepositoryIndexStore,
        embedder: FeatureHashEmbedder,
    ) -> None:
        self._workspaces = workspaces
        self._parsing = parsing
        self._parsers = parsers
        self._indexes = indexes
        self._embedder = embedder

    def build(self, workspace_id: str) -> RepositoryIndex:
        workspace = self._workspaces.get(workspace_id)
        parse_result = self._parsing.parse(workspace_id)
        repository_root = workspace.path / "repository"
        source_bytes = {
            file.path: (repository_root / file.path).read_bytes()
            for file in parse_result.files
        }
        source_text = {
            path: content.decode("utf-8", errors="replace")
            for path, content in source_bytes.items()
        }
        references = extract_dependencies(
            parse_result.files,
            parse_result.symbols,
            source_bytes,
            self._parsers,
        )
        nodes, edges = build_graph(
            workspace_id,
            parse_result.files,
            parse_result.symbols,
            references,
        )
        chunks = build_chunks(
            workspace_id,
            parse_result.files,
            parse_result.symbols,
            source_text,
        )
        vectors = [
            VectorEntry(chunk.id, self._embedder.embed(f"{chunk.path}\n{chunk.content}"))
            for chunk in chunks
        ]
        language_counts = Counter(file.language.value for file in parse_result.files)
        index = RepositoryIndex(
            workspace_id=workspace_id,
            indexed_at=datetime.now(timezone.utc),
            files=parse_result.files,
            symbols=parse_result.symbols,
            nodes=nodes,
            edges=edges,
            chunks=chunks,
            stats=IndexStats(
                file_count=len(parse_result.files),
                symbol_count=len(parse_result.symbols),
                edge_count=len(edges),
                chunk_count=len(chunks),
                embedded_chunk_count=len(vectors),
                languages=dict(sorted(language_counts.items())),
            ),
        )
        self._indexes.put(workspace_id, index, workspace.metadata.expires_at, vectors)
        return index

    def get(self, workspace_id: str) -> RepositoryIndex:
        self._workspaces.get(workspace_id)
        return self._indexes.get(workspace_id)

    def delete(self, workspace_id: str) -> None:
        self._indexes.delete(workspace_id)

