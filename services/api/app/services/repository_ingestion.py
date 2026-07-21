import os
import shutil
import stat
from pathlib import Path

from fastapi import UploadFile

from app.core.config import Settings
from app.domain.repositories import (
    RepositoryLimitError,
    RepositorySourceType,
    RepositoryWorkspace,
)
from app.ingestion.github import clone_public_repository, normalize_github_url
from app.ingestion.uploads import extract_zip_safely, repository_name_from_upload, save_upload
from app.ingestion.workspaces import WorkspaceStore


def inspect_repository(path: Path, max_files: int, max_bytes: int) -> tuple[int, int]:
    file_count = 0
    total_bytes = 0
    for current_root, directory_names, file_names in os.walk(path, followlinks=False):
        root = Path(current_root)
        for directory_name in directory_names:
            if (root / directory_name).is_symlink():
                raise RepositoryLimitError("Repository contains an unexpected symbolic link.")
        for file_name in file_names:
            file_path = root / file_name
            mode = file_path.lstat().st_mode
            if stat.S_ISLNK(mode) or not stat.S_ISREG(mode):
                raise RepositoryLimitError("Repository contains an unsupported filesystem entry.")
            file_count += 1
            total_bytes += file_path.stat().st_size
            if file_count > max_files:
                raise RepositoryLimitError("Repository contains too many files.")
            if total_bytes > max_bytes:
                raise RepositoryLimitError("Repository exceeds the expanded-size limit.")
    return file_count, total_bytes


def remove_symbolic_links(path: Path) -> int:
    """Remove links from a cloned repository without ever following their targets."""
    removed = 0
    for current_root, directory_names, file_names in os.walk(path, followlinks=False):
        root = Path(current_root)
        linked_directories = [name for name in directory_names if (root / name).is_symlink()]
        directory_names[:] = [name for name in directory_names if name not in linked_directories]
        for name in linked_directories:
            (root / name).unlink()
            removed += 1
        for name in file_names:
            entry = root / name
            if entry.is_symlink():
                entry.unlink()
                removed += 1
    return removed


class RepositoryIngestionService:
    def __init__(self, settings: Settings, workspaces: WorkspaceStore) -> None:
        self._settings = settings
        self._workspaces = workspaces

    def ingest_github(self, repository_url: str) -> RepositoryWorkspace:
        normalized_url, _ = normalize_github_url(repository_url)
        workspace_id, workspace_path = self._workspaces.reserve()
        content_path = workspace_path / "repository"
        try:
            repository_name = clone_public_repository(
                repository_url,
                content_path,
                self._settings.repository_clone_timeout_seconds,
            )
            shutil.rmtree(content_path / ".git", ignore_errors=True)
            remove_symbolic_links(content_path)
            file_count, total_bytes = inspect_repository(
                content_path,
                self._settings.repository_max_files,
                self._settings.repository_max_expanded_bytes,
            )
            return self._workspaces.activate(
                workspace_id,
                workspace_path,
                repository_name,
                RepositorySourceType.github,
                normalized_url.removesuffix(".git"),
                file_count,
                total_bytes,
            )
        except Exception:
            self._workspaces.discard(workspace_id, workspace_path)
            raise

    async def ingest_upload(self, upload: UploadFile) -> RepositoryWorkspace:
        repository_name = repository_name_from_upload(upload.filename)
        workspace_id, workspace_path = self._workspaces.reserve()
        archive_path = workspace_path / "upload.zip"
        content_path = workspace_path / "repository"
        try:
            await save_upload(upload, archive_path, self._settings.repository_max_download_bytes)
            extract_zip_safely(
                archive_path,
                content_path,
                self._settings.repository_max_files,
                self._settings.repository_max_expanded_bytes,
            )
            archive_path.unlink(missing_ok=True)
            file_count, total_bytes = inspect_repository(
                content_path,
                self._settings.repository_max_files,
                self._settings.repository_max_expanded_bytes,
            )
            return self._workspaces.activate(
                workspace_id,
                workspace_path,
                repository_name,
                RepositorySourceType.upload,
                upload.filename or "upload.zip",
                file_count,
                total_bytes,
            )
        except Exception:
            self._workspaces.discard(workspace_id, workspace_path)
            raise
        finally:
            await upload.close()

    def get(self, workspace_id: str) -> RepositoryWorkspace:
        return self._workspaces.get(workspace_id).metadata

    def delete(self, workspace_id: str) -> None:
        self._workspaces.delete(workspace_id)
