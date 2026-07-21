import io
import zipfile
from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


def repository_archive() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(
            "pkg/auth.py",
            "def verify_token(token: str) -> bool:\n    return token.startswith('valid-')\n",
        )
        archive.writestr(
            "pkg/service.py",
            "from pkg.auth import verify_token\n\ndef authenticate(token: str) -> bool:\n    return verify_token(token)\n",
        )
    return buffer.getvalue()


class FakeResponses:
    def __init__(self) -> None:
        self.request: dict[str, object] = {}

    def create(self, **kwargs: object) -> object:
        self.request = kwargs
        return SimpleNamespace(
            output_text=(
                "Authentication enters through `authenticate`, which delegates token validation "
                "to `verify_token` [1] [2]."
            )
        )


def indexed_workspace(client: TestClient) -> str:
    ingestion = client.post(
        "/api/v1/repositories/uploads",
        files={"repository": ("chat-fixture.zip", repository_archive(), "application/zip")},
    )
    workspace_id = ingestion.json()["id"]
    assert client.post(f"/api/v1/repositories/{workspace_id}/index").status_code == 200
    return workspace_id


def test_chat_answers_with_grounded_citations(tmp_path: Path) -> None:
    app = create_app(Settings(app_env="test", repository_temp_root=str(tmp_path)))
    fake = FakeResponses()
    app.state.repository_chat._client = fake

    with TestClient(app) as client:
        workspace_id = indexed_workspace(client)
        response = client.post(
            f"/api/v1/repositories/{workspace_id}/chat",
            json={
                "question": "How does authentication work?",
                "history": [{"role": "user", "content": "Focus on token verification."}],
            },
        )

    assert response.status_code == 200
    result = response.json()
    assert "verify_token" in result["answer"]
    assert result["citations"]
    assert result["sources"]
    assert all(source["excerpt"] for source in result["sources"])
    assert {citation["path"] for citation in result["citations"]} <= {
        "pkg/auth.py",
        "pkg/service.py",
    }
    assert "Repository evidence:" in str(fake.request["input"])
    assert "Focus on token verification." in str(fake.request["input"])
    assert fake.request["model"] == "gpt-5.6-sol"


def test_chat_reports_missing_api_key(tmp_path: Path) -> None:
    app = create_app(Settings(app_env="test", repository_temp_root=str(tmp_path)))
    app.state.repository_chat._api_key = None

    with TestClient(app) as client:
        workspace_id = indexed_workspace(client)
        response = client.post(
            f"/api/v1/repositories/{workspace_id}/chat",
            json={"question": "How does authentication work?"},
        )

    assert response.status_code == 503
    assert response.json()["detail"] == "OPENAI_API_KEY is not configured for the backend."
