import io
import zipfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.domain.repositories import InvalidRepositoryError
from app.ingestion.github import normalize_github_url
from app.main import create_app
from app.services.repository_ingestion import remove_symbolic_links


def make_zip(entries: dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for path, content in entries.items():
            archive.writestr(path, content)
    return buffer.getvalue()


def test_github_url_normalization_is_strict() -> None:
    assert normalize_github_url("https://github.com/openai/openai-python") == (
        "https://github.com/openai/openai-python.git",
        "openai/openai-python",
    )

    with pytest.raises(InvalidRepositoryError):
        normalize_github_url("https://example.com/openai/openai-python")

    with pytest.raises(InvalidRepositoryError):
        normalize_github_url("https://github.com/openai/openai-python/issues")


def test_zip_upload_lifecycle(tmp_path: Path) -> None:
    app = create_app(Settings(app_env="test", repository_temp_root=str(tmp_path)))
    archive = make_zip({"demo/README.md": b"# demo\n", "demo/src/main.py": b"print('hello')\n"})

    with TestClient(app) as client:
        created = client.post(
            "/api/v1/repositories/uploads",
            files={"repository": ("demo.zip", archive, "application/zip")},
        )
        assert created.status_code == 201
        body = created.json()
        assert body["name"] == "demo"
        assert body["source_type"] == "upload"
        assert body["file_count"] == 2
        assert body["total_bytes"] == 22

        fetched = client.get(f"/api/v1/repositories/{body['id']}")
        assert fetched.status_code == 200
        assert fetched.json() == body

        deleted = client.delete(f"/api/v1/repositories/{body['id']}")
        assert deleted.status_code == 204
        assert client.get(f"/api/v1/repositories/{body['id']}").status_code == 404

    assert list(tmp_path.iterdir()) == []


def test_zip_upload_rejects_path_traversal(tmp_path: Path) -> None:
    app = create_app(Settings(app_env="test", repository_temp_root=str(tmp_path)))
    archive = make_zip({"../escaped.py": b"unsafe"})

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/repositories/uploads",
            files={"repository": ("unsafe.zip", archive, "application/zip")},
        )

    assert response.status_code == 400
    assert not (tmp_path / "escaped.py").exists()
    assert list(tmp_path.iterdir()) == []


def test_github_ingestion_uses_workspace_and_removes_git_metadata(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake_clone(_: str, destination: Path, __: int) -> str:
        destination.mkdir()
        (destination / "README.md").write_text("hello", encoding="utf-8")
        (destination / ".git").mkdir()
        (destination / ".git" / "config").write_text("metadata", encoding="utf-8")
        return "owner/repository"

    monkeypatch.setattr("app.services.repository_ingestion.clone_public_repository", fake_clone)
    app = create_app(Settings(app_env="test", repository_temp_root=str(tmp_path)))

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/repositories/github",
            json={"repository_url": "https://github.com/owner/repository"},
        )

        assert response.status_code == 201
        assert response.json()["file_count"] == 1
        assert response.json()["total_bytes"] == 5

    assert list(tmp_path.iterdir()) == []


def test_github_ingestion_safely_skips_symbolic_links(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    external_file = tmp_path / "outside.py"
    external_file.write_text("do_not_read = True", encoding="utf-8")

    def fake_clone(_: str, destination: Path, __: int) -> str:
        destination.mkdir()
        (destination / "app.py").write_text("print('safe')\n", encoding="utf-8")
        (destination / "linked.py").symlink_to(external_file)
        (destination / "linked-directory").symlink_to(tmp_path, target_is_directory=True)
        return "owner/repository"

    monkeypatch.setattr("app.services.repository_ingestion.clone_public_repository", fake_clone)
    app = create_app(Settings(app_env="test", repository_temp_root=str(tmp_path / "workspaces")))

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/repositories/github",
            json={"repository_url": "https://github.com/owner/repository"},
        )

        assert response.status_code == 201
        assert response.json()["file_count"] == 1
        assert response.json()["total_bytes"] == 14

    assert external_file.read_text(encoding="utf-8") == "do_not_read = True"


def test_remove_symbolic_links_leaves_regular_files(tmp_path: Path) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    source = repository / "source.py"
    source.write_text("value = 1\n", encoding="utf-8")
    (repository / "alias.py").symlink_to(source)

    assert remove_symbolic_links(repository) == 1
    assert source.exists()
    assert not (repository / "alias.py").exists()
