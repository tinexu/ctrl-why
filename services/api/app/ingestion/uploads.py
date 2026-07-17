import stat
import zipfile
from pathlib import Path, PurePosixPath

from fastapi import UploadFile

from app.domain.repositories import InvalidRepositoryError, RepositoryLimitError


async def save_upload(upload: UploadFile, destination: Path, max_download_bytes: int) -> None:
    written = 0
    with destination.open("wb") as output:
        while chunk := await upload.read(1024 * 1024):
            written += len(chunk)
            if written > max_download_bytes:
                raise RepositoryLimitError("The uploaded archive exceeds the compressed-size limit.")
            output.write(chunk)


def _safe_relative_path(member: zipfile.ZipInfo) -> Path:
    if "\\" in member.filename:
        raise InvalidRepositoryError("The ZIP archive contains an invalid path.")
    path = PurePosixPath(member.filename)
    if path.is_absolute() or not path.parts or any(part in {"", ".", ".."} for part in path.parts):
        raise InvalidRepositoryError("The ZIP archive contains an unsafe path.")
    unix_mode = member.external_attr >> 16
    if stat.S_ISLNK(unix_mode):
        raise InvalidRepositoryError("Symbolic links are not allowed in uploaded repositories.")
    return Path(*path.parts)


def extract_zip_safely(
    archive_path: Path,
    destination: Path,
    max_files: int,
    max_expanded_bytes: int,
) -> None:
    if not zipfile.is_zipfile(archive_path):
        raise InvalidRepositoryError("Repository uploads must be valid ZIP archives.")
    destination.mkdir()
    with zipfile.ZipFile(archive_path) as archive:
        members = archive.infolist()
        files = [member for member in members if not member.is_dir()]
        if len(files) > max_files:
            raise RepositoryLimitError("The uploaded repository contains too many files.")
        if sum(member.file_size for member in files) > max_expanded_bytes:
            raise RepositoryLimitError("The uploaded repository exceeds the expanded-size limit.")

        extracted_bytes = 0
        for member in members:
            relative_path = _safe_relative_path(member)
            target = destination / relative_path
            if member.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(member) as source, target.open("wb") as output:
                while chunk := source.read(1024 * 1024):
                    extracted_bytes += len(chunk)
                    if extracted_bytes > max_expanded_bytes:
                        raise RepositoryLimitError("The uploaded repository exceeds the expanded-size limit.")
                    output.write(chunk)


def repository_name_from_upload(filename: str | None) -> str:
    if not filename:
        return "uploaded-repository"
    name = Path(filename).name
    if not name.lower().endswith(".zip"):
        raise InvalidRepositoryError("Repository uploads must use a .zip filename.")
    return name[:-4] or "uploaded-repository"
