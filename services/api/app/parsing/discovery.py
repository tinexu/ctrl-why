import os
from dataclasses import dataclass
from pathlib import Path

from app.domain.parsing import SourceLanguage

IGNORED_DIRECTORIES = frozenset(
    {
        ".git", ".hg", ".svn", ".idea", ".next", ".nuxt", ".pytest_cache",
        ".tox", ".venv", ".vscode", "__pycache__", "build", "coverage",
        "dist", "node_modules", "site-packages", "target", "vendor", "venv",
    }
)
IGNORED_FILENAMES = frozenset(
    {"bun.lockb", "package-lock.json", "pnpm-lock.yaml", "yarn.lock"}
)
LANGUAGE_BY_SUFFIX = {
    ".py": SourceLanguage.python,
    ".js": SourceLanguage.javascript,
    ".jsx": SourceLanguage.javascript,
    ".mjs": SourceLanguage.javascript,
    ".cjs": SourceLanguage.javascript,
    ".ts": SourceLanguage.typescript,
    ".mts": SourceLanguage.typescript,
    ".cts": SourceLanguage.typescript,
    ".tsx": SourceLanguage.tsx,
}


@dataclass(frozen=True)
class DiscoveredFile:
    path: Path
    relative_path: str
    language: SourceLanguage
    size_bytes: int


@dataclass(frozen=True)
class DiscoveryResult:
    files: list[DiscoveredFile]
    skipped_file_count: int


def discover_source_files(repository_root: Path, max_file_bytes: int) -> DiscoveryResult:
    files: list[DiscoveredFile] = []
    skipped = 0
    for current_root, directory_names, file_names in os.walk(repository_root, followlinks=False):
        directory_names[:] = sorted(
            name
            for name in directory_names
            if name not in IGNORED_DIRECTORIES and not (Path(current_root) / name).is_symlink()
        )
        root = Path(current_root)
        for filename in sorted(file_names):
            path = root / filename
            language = LANGUAGE_BY_SUFFIX.get(path.suffix.lower())
            if language is None or filename in IGNORED_FILENAMES or path.is_symlink():
                continue
            size_bytes = path.stat().st_size
            if size_bytes > max_file_bytes or ".min." in filename:
                skipped += 1
                continue
            with path.open("rb") as source:
                if b"\0" in source.read(8192):
                    skipped += 1
                    continue
            files.append(
                DiscoveredFile(
                    path=path,
                    relative_path=path.relative_to(repository_root).as_posix(),
                    language=language,
                    size_bytes=size_bytes,
                )
            )
    return DiscoveryResult(files=files, skipped_file_count=skipped)

