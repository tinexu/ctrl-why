import shutil
import tempfile
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import RLock
from uuid import uuid4

from app.domain.repositories import RepositorySourceType, RepositoryWorkspace, WorkspaceNotFoundError


@dataclass(frozen=True)
class WorkspaceRecord:
    metadata: RepositoryWorkspace
    path: Path


class WorkspaceStore:
    """Owns temporary repository directories and their in-memory metadata."""

    def __init__(self, ttl_seconds: int, temp_root: str | None = None) -> None:
        parent = Path(temp_root).resolve() if temp_root else None
        if parent:
            parent.mkdir(parents=True, exist_ok=True)
        self._root = Path(tempfile.mkdtemp(prefix="ctrl-why-", dir=parent))
        self._ttl = timedelta(seconds=ttl_seconds)
        self._records: dict[str, WorkspaceRecord] = {}
        self._lock = RLock()

    def reserve(self) -> tuple[str, Path]:
        workspace_id = str(uuid4())
        path = self._root / workspace_id
        path.mkdir(mode=0o700)
        return workspace_id, path

    def activate(
        self,
        workspace_id: str,
        path: Path,
        name: str,
        source_type: RepositorySourceType,
        source_reference: str,
        file_count: int,
        total_bytes: int,
    ) -> RepositoryWorkspace:
        now = datetime.now(timezone.utc)
        metadata = RepositoryWorkspace(
            id=workspace_id,
            name=name,
            source_type=source_type,
            source_reference=source_reference,
            created_at=now,
            expires_at=now + self._ttl,
            file_count=file_count,
            total_bytes=total_bytes,
        )
        with self._lock:
            self._records[workspace_id] = WorkspaceRecord(metadata=metadata, path=path)
        return metadata

    def get(self, workspace_id: str) -> WorkspaceRecord:
        self.cleanup_expired()
        with self._lock:
            record = self._records.get(workspace_id)
        if record is None:
            raise WorkspaceNotFoundError("Repository workspace was not found or has expired.")
        return record

    def delete(self, workspace_id: str) -> None:
        with self._lock:
            record = self._records.pop(workspace_id, None)
        if record is None:
            raise WorkspaceNotFoundError("Repository workspace was not found or has expired.")
        shutil.rmtree(record.path, ignore_errors=True)

    def discard(self, workspace_id: str, path: Path) -> None:
        with self._lock:
            self._records.pop(workspace_id, None)
        if path.parent == self._root:
            shutil.rmtree(path, ignore_errors=True)

    def cleanup_expired(self) -> None:
        now = datetime.now(timezone.utc)
        with self._lock:
            expired = [key for key, record in self._records.items() if record.metadata.expires_at <= now]
            records = [self._records.pop(key) for key in expired]
        for record in records:
            shutil.rmtree(record.path, ignore_errors=True)

    def close(self) -> None:
        with self._lock:
            self._records.clear()
        shutil.rmtree(self._root, ignore_errors=True)

