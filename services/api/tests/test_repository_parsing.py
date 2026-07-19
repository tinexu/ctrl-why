import io
import zipfile
from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


def make_repository_zip() -> bytes:
    files = {
        "sample/app.py": b"""class Greeter:\n    def greet(self, name: str) -> str:\n        return f\"Hello {name}\"\n\ndef main() -> None:\n    print(Greeter().greet(\"world\"))\n""",
        "sample/web.ts": b"""interface User { name: string }\ntype UserId = string;\nexport class UserService {\n  find(id: UserId): User { return { name: id }; }\n}\nexport const loadUser = async (id: UserId) => {\n  return new UserService().find(id);\n};\n""",
        "sample/view.tsx": b"export function Greeting() { return <h1>Hello</h1>; }\n",
        "sample/legacy.js": b"function boot() { return true; }\n",
        "sample/node_modules/ignored.js": b"function ignored() {}\n",
        "sample/bundle.min.js": b"function minified(){}\n",
        "sample/README.md": b"# Not source\n",
    }
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for path, content in files.items():
            archive.writestr(path, content)
    return buffer.getvalue()


def test_parse_repository_extracts_supported_files_and_symbols(tmp_path: Path) -> None:
    app = create_app(Settings(app_env="test", repository_temp_root=str(tmp_path)))

    with TestClient(app) as client:
        ingestion = client.post(
            "/api/v1/repositories/uploads",
            files={"repository": ("sample.zip", make_repository_zip(), "application/zip")},
        )
        workspace_id = ingestion.json()["id"]

        response = client.post(f"/api/v1/repositories/{workspace_id}/parse")

    assert response.status_code == 200
    result = response.json()
    assert result["workspace_id"] == workspace_id
    assert result["syntax_error_count"] == 0
    assert result["skipped_file_count"] == 1
    assert {(item["path"], item["language"]) for item in result["files"]} == {
        ("sample/app.py", "python"),
        ("sample/legacy.js", "javascript"),
        ("sample/view.tsx", "tsx"),
        ("sample/web.ts", "typescript"),
    }

    symbols = {(item["qualified_name"], item["kind"]) for item in result["symbols"]}
    assert ("Greeter", "class") in symbols
    assert ("Greeter.greet", "method") in symbols
    assert ("main", "function") in symbols
    assert ("User", "interface") in symbols
    assert ("UserId", "type_alias") in symbols
    assert ("UserService.find", "method") in symbols
    assert ("loadUser", "function") in symbols
    assert ("Greeting", "function") in symbols
    assert ("boot", "function") in symbols

    greet = next(item for item in result["symbols"] if item["qualified_name"] == "Greeter.greet")
    assert greet["start_line"] == 2
    assert greet["start_column"] == 5
    assert "def greet(self, name: str) -> str" in greet["signature"]


def test_parse_repository_reports_syntax_errors(tmp_path: Path) -> None:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("broken.py", "def broken(:\n    pass\n")
    app = create_app(Settings(app_env="test", repository_temp_root=str(tmp_path)))

    with TestClient(app) as client:
        ingestion = client.post(
            "/api/v1/repositories/uploads",
            files={"repository": ("broken.zip", buffer.getvalue(), "application/zip")},
        )
        response = client.post(f"/api/v1/repositories/{ingestion.json()['id']}/parse")

    assert response.status_code == 200
    assert response.json()["syntax_error_count"] > 0


def test_parse_missing_workspace_returns_not_found(tmp_path: Path) -> None:
    app = create_app(Settings(app_env="test", repository_temp_root=str(tmp_path)))

    with TestClient(app) as client:
        response = client.post("/api/v1/repositories/does-not-exist/parse")

    assert response.status_code == 404


def test_parse_skips_source_files_over_the_per_file_limit(tmp_path: Path) -> None:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("small.py", "def ok(): pass\n")
        archive.writestr("large.py", "#" * 128)
    app = create_app(
        Settings(
            app_env="test",
            repository_temp_root=str(tmp_path),
            repository_max_source_file_bytes=32,
        )
    )

    with TestClient(app) as client:
        ingestion = client.post(
            "/api/v1/repositories/uploads",
            files={"repository": ("limits.zip", buffer.getvalue(), "application/zip")},
        )
        response = client.post(f"/api/v1/repositories/{ingestion.json()['id']}/parse")

    assert response.status_code == 200
    assert [item["path"] for item in response.json()["files"]] == ["small.py"]
    assert response.json()["skipped_file_count"] == 1
