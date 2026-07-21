import io
import json
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
            "pkg/users.py",
            "def create_user(name: str) -> dict[str, str]:\n    return {'name': name}\n",
        )
        archive.writestr(
            "tests/test_users.py",
            "from pkg.users import create_user\n\ndef test_create_user():\n    assert create_user('Ada')['name'] == 'Ada'\n",
        )
    return buffer.getvalue()


LOGS = """Run pytest
$ pytest tests/test_users.py
================ FAILURES ================
________________ test_create_user ________________
tests/test_users.py:4: AssertionError
E AssertionError: assert None == 'Ada'
FAILED tests/test_users.py::test_create_user
Process completed with exit code 1
API_TOKEN=super-secret-value
"""


class FakeResponses:
    def __init__(self) -> None:
        self.request: dict[str, object] = {}

    def create(self, **kwargs: object) -> object:
        self.request = kwargs
        return SimpleNamespace(output_text=json.dumps({
            "summary": "The user creation test fails because the returned name does not match [L2] [R1].",
            "likely_root_cause": "The `create_user` return contract and test expectation disagree [R1].",
            "recommendations": ["Inspect the return value in `pkg/users.py` [R1]."],
            "validation_steps": ["Run `pytest tests/test_users.py` after the correction."],
        }))


def indexed_workspace(client: TestClient) -> str:
    response = client.post(
        "/api/v1/repositories/uploads",
        files={"repository": ("ci-fixture.zip", repository_archive(), "application/zip")},
    )
    workspace_id = response.json()["id"]
    assert client.post(f"/api/v1/repositories/{workspace_id}/index").status_code == 200
    return workspace_id


def test_ci_analysis_retrieves_files_and_enhances_explanation(tmp_path: Path) -> None:
    app = create_app(Settings(app_env="test", repository_temp_root=str(tmp_path)))
    fake = FakeResponses()
    app.state.ci_analysis._client = fake

    with TestClient(app) as client:
        workspace_id = indexed_workspace(client)
        response = client.post(
            f"/api/v1/repositories/{workspace_id}/ci-analysis",
            json={"workflow_name": "Tests", "logs": LOGS},
        )

    assert response.status_code == 200
    result = response.json()
    assert result["category"] == "test"
    assert result["ai_enhanced"] is True
    assert "tests/test_users.py" in result["affected_files"]
    assert result["repository_evidence"]
    assert result["log_evidence"]
    assert "super-secret-value" not in str(fake.request["input"])
    assert "[REDACTED]" in str(fake.request["input"])


def test_ci_analysis_has_deterministic_fallback_and_validates_size(tmp_path: Path) -> None:
    app = create_app(Settings(app_env="test", repository_temp_root=str(tmp_path)))

    with TestClient(app) as client:
        workspace_id = indexed_workspace(client)
        response = client.post(
            f"/api/v1/repositories/{workspace_id}/ci-analysis",
            json={"logs": "src/missing.ts:9 error TS2322: Type 'str' is not assignable"},
        )
        too_short = client.post(
            f"/api/v1/repositories/{workspace_id}/ci-analysis",
            json={"logs": "failed"},
        )

    assert response.status_code == 200
    assert response.json()["category"] == "typecheck"
    assert response.json()["ai_enhanced"] is False
    assert too_short.status_code == 422
