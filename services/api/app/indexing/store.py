from dataclasses import dataclass
from datetime import datetime, timezone
from threading import RLock

from app.domain.indexing import RepositoryIndex
from app.domain.repositories import WorkspaceNotFoundError
from app.indexing.embeddings import VectorEntry, cosine_similarity


@dataclass(frozen=True)
class StoredIndex:
    index: RepositoryIndex
    expires_at: datetime
    vectors: tuple[VectorEntry, ...]


class RepositoryIndexStore:
    def __init__(self) -> None:
        self._indexes: dict[str, StoredIndex] = {}
        self._lock = RLock()

    def put(self, workspace_id: str, index: RepositoryIndex, expires_at: datetime, vectors: list[VectorEntry]) -> None:
        with self._lock:
            self._indexes[workspace_id] = StoredIndex(index, expires_at, tuple(vectors))

    def get(self, workspace_id: str) -> RepositoryIndex:
        self.cleanup_expired()
        with self._lock:
            stored = self._indexes.get(workspace_id)
        if stored is None:
            raise WorkspaceNotFoundError("Repository index was not found. Index the active workspace first.")
        return stored.index

    def search(self, workspace_id: str, query_vector: list[float], limit: int) -> list[tuple[str, float]]:
        self.cleanup_expired()
        with self._lock:
            stored = self._indexes.get(workspace_id)
        if stored is None:
            raise WorkspaceNotFoundError("Repository index was not found. Index the active workspace first.")
        scores = [(entry.chunk_id, cosine_similarity(query_vector, entry.vector)) for entry in stored.vectors]
        return sorted(scores, key=lambda item: item[1], reverse=True)[:limit]

    def delete(self, workspace_id: str) -> None:
        with self._lock:
            self._indexes.pop(workspace_id, None)

    def cleanup_expired(self) -> None:
        now = datetime.now(timezone.utc)
        with self._lock:
            expired = [key for key, stored in self._indexes.items() if stored.expires_at <= now]
            for key in expired:
                self._indexes.pop(key, None)

    def close(self) -> None:
        with self._lock:
            self._indexes.clear()

