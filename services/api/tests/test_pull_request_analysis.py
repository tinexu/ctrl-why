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
            "pkg/auth.py",
            "def verify_token(token: str) -> bool:\n    return token.startswith('valid-')\n",
        )
        archive.writestr(
            "pkg/service.py",
            "from pkg.auth import verify_token\n\ndef authenticate(token: str) -> bool:\n    return verify_token(token)\n",
        )
    return buffer.getvalue()


DIFF = """diff --git a/pkg/auth.py b/pkg/auth.py
index 1111111..2222222 100644
--- a/pkg/auth.py
+++ b/pkg/auth.py
@@ -1,2 +1,3 @@
 def verify_token(token: str) -> bool:
-    return token.startswith('valid-')
+    secret = "do-not-commit"
+    return eval(token)
"""


class FakeResponses:
    def create(self, **_: object) -> object:
        return SimpleNamespace(output_text=json.dumps({
            "summary": "Token verification behavior changes and affects its authentication caller [1].",
            "suggested_tests": ["Test that malformed tokens are rejected without executing them."],
        }))


def indexed_workspace(client: TestClient) -> str:
    response = client.post(
        "/api/v1/repositories/uploads",
        files={"repository": ("pr-fixture.zip", repository_archive(), "application/zip")},
    )
    workspace_id = response.json()["id"]
    assert client.post(f"/api/v1/repositories/{workspace_id}/index").status_code == 200
    return workspace_id


def test_analyzes_diff_with_graph_impact_security_and_ai(tmp_path: Path) -> None:
    app = create_app(Settings(app_env="test", repository_temp_root=str(tmp_path)))
    app.state.pull_request_analysis._client = FakeResponses()

    with TestClient(app) as client:
        workspace_id = indexed_workspace(client)
        response = client.post(
            f"/api/v1/repositories/{workspace_id}/pull-request-analysis",
            json={"title": "Change token verification", "diff": DIFF},
        )

    assert response.status_code == 200
    result = response.json()
    assert result["ai_enhanced"] is True
    assert result["changed_files"][0]["path"] == "pkg/auth.py"
    assert result["changed_files"][0]["changed_symbols"] == ["verify_token"]
    assert result["affected_files"][0]["path"] == "pkg/service.py"
    assert result["risk_score"] >= 35
    assert any(finding["title"] == "Dynamic code execution added" for finding in result["security_concerns"])
    assert any("malformed tokens" in suggestion for suggestion in result["suggested_tests"])
    assert result["evidence"][0]["path"] == "pkg/auth.py"


def test_analysis_works_without_openai_key_and_rejects_invalid_diff(tmp_path: Path) -> None:
    app = create_app(
        Settings(app_env="test", repository_temp_root=str(tmp_path), _env_file=None)
    )

    with TestClient(app) as client:
        workspace_id = indexed_workspace(client)
        response = client.post(
            f"/api/v1/repositories/{workspace_id}/pull-request-analysis",
            json={"diff": DIFF},
        )
        invalid = client.post(
            f"/api/v1/repositories/{workspace_id}/pull-request-analysis",
            json={"diff": "this is not a unified git diff"},
        )

    assert response.status_code == 200
    assert response.json()["ai_enhanced"] is False
    assert invalid.status_code == 400
    assert "unified Git diff" in invalid.json()["detail"]
