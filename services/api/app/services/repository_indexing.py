from collections import Counter
from datetime import datetime, timezone
import re

from app.domain.indexing import (
    IndexStats,
    RepositoryIndex,
    RepositorySearchResponse,
    RepositorySearchResult,
)
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

    def search(self, workspace_id: str, query: str, limit: int) -> RepositorySearchResponse:
        self._workspaces.get(workspace_id)
        index = self._indexes.get(workspace_id)
        query = query.strip()
        ranked = self._indexes.search(
            workspace_id,
            self._embedder.embed(query),
            min(max(limit * 4, 20), len(index.chunks)),
        )
        chunks = {chunk.id: chunk for chunk in index.chunks}
        symbols = {symbol.id: symbol for symbol in index.symbols}
        query_terms = {
            term.lower()
            for term in re.findall(r"[A-Za-z_][A-Za-z0-9_]*", query)
            if len(term) > 2
        }
        candidates: list[tuple[float, RepositorySearchResult]] = []

        for chunk_id, vector_score in ranked:
            chunk = chunks[chunk_id]
            symbol = symbols.get(chunk.symbol_id) if chunk.symbol_id else None
            searchable = " ".join(
                part for part in (chunk.path, symbol.qualified_name if symbol else "", chunk.content) if part
            ).lower()
            matched_terms = sorted(term for term in query_terms if term in searchable)
            lexical_boost = min(len(matched_terms) * 0.08, 0.24)
            score = min(max(vector_score, 0.0) + lexical_boost, 1.0)
            reason = _search_reason(chunk.path, symbol.qualified_name if symbol else None, matched_terms)
            candidates.append(
                (
                    score,
                    RepositorySearchResult(
                        chunk_id=chunk.id,
                        path=chunk.path,
                        symbol=symbol.qualified_name if symbol else None,
                        symbol_kind=symbol.kind.value if symbol else None,
                        start_line=chunk.start_line,
                        end_line=chunk.end_line,
                        excerpt=_excerpt(chunk.content),
                        score=round(score, 4),
                        reason=reason,
                    ),
                )
            )

        candidates.sort(key=lambda item: (-item[0], item[1].path, item[1].start_line))
        return RepositorySearchResponse(
            workspace_id=workspace_id,
            query=query,
            results=[result for _, result in candidates[:limit]],
        )

    def delete(self, workspace_id: str) -> None:
        self._indexes.delete(workspace_id)


def _excerpt(content: str, max_characters: int = 1200) -> str:
    normalized = content.strip()
    if len(normalized) <= max_characters:
        return normalized
    return f"{normalized[:max_characters].rstrip()}\n…"


def _search_reason(path: str, symbol: str | None, matched_terms: list[str]) -> str:
    location = f"symbol {symbol}" if symbol else f"file {path}"
    if matched_terms:
        return f"{location.capitalize()} contains: {', '.join(matched_terms[:5])}."
    return f"Code in {location} is structurally similar to the search terms."
