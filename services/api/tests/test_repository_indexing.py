import io
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.domain.indexing import IndexStats, RepositoryIndex
from app.indexing.embeddings import FeatureHashEmbedder, VectorEntry
from app.indexing.store import RepositoryIndexStore
from app.main import create_app


def make_index_fixture() -> bytes:
    files = {
        "pkg/__init__.py": b"",
        "pkg/auth.py": b"def verify(token: str) -> bool:\n    return bool(token)\n",
        "pkg/service.py": b"import os, sys\nfrom pkg.auth import verify\n\ndef authenticate(token: str) -> bool:\n    return verify(token)\n",
        "web/client.ts": b"export function client(path: string) { return path; }\n",
        "web/app.ts": b"import { client } from './client';\nexport function load() { return client('/api'); }\n",
    }
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for path, content in files.items():
            archive.writestr(path, content)
    return buffer.getvalue()


def test_index_builds_graph_chunks_and_cached_result(tmp_path: Path) -> None:
    app = create_app(Settings(app_env="test", repository_temp_root=str(tmp_path)))

    with TestClient(app) as client:
        ingestion = client.post(
            "/api/v1/repositories/uploads",
            files={"repository": ("index-fixture.zip", make_index_fixture(), "application/zip")},
        )
        workspace_id = ingestion.json()["id"]
        assert client.get(f"/api/v1/repositories/{workspace_id}/index").status_code == 404

        response = client.post(f"/api/v1/repositories/{workspace_id}/index")
        cached = client.get(f"/api/v1/repositories/{workspace_id}/index")
        rebuilt = client.post(f"/api/v1/repositories/{workspace_id}/index")
        search = client.post(
            f"/api/v1/repositories/{workspace_id}/search",
            json={"query": "Where is authentication token verification handled?", "limit": 3},
        )
        internal_index = app.state.repository_indexing.get(workspace_id)
        internal_has_import_chunk = any("from pkg.auth import verify" in chunk.content for chunk in internal_index.chunks)
        deleted = client.delete(f"/api/v1/repositories/{workspace_id}")
        missing_after_delete = client.get(f"/api/v1/repositories/{workspace_id}/index")

    assert response.status_code == 200
    assert cached.status_code == 200
    assert search.status_code == 200
    result = response.json()
    assert result["stats"]["file_count"] == 5
    assert result["stats"]["symbol_count"] == 4
    assert result["stats"]["chunk_count"] == result["stats"]["embedded_chunk_count"]
    assert result["stats"]["languages"] == {"python": 3, "typescript": 2}

    nodes = {node["id"]: node for node in result["nodes"]}
    edges = result["edges"]
    assert any(edge["type"] == "imports" and nodes[edge["target_id"]].get("path") == "pkg/auth.py" for edge in edges)
    assert any(edge["type"] == "imports" and nodes[edge["target_id"]].get("path") == "web/client.ts" for edge in edges)
    assert any(node["type"] == "external_module" and node["label"] == "os" for node in nodes.values())
    assert any(node["type"] == "external_module" and node["label"] == "sys" for node in nodes.values())
    assert any(edge["type"] == "calls" and edge["label"] == "verify" for edge in edges)
    assert any(edge["type"] == "calls" and edge["label"] == "client" for edge in edges)
    assert all(chunk["content_hash"] and "content" not in chunk for chunk in result["chunks"])
    assert cached.json() == result
    assert [chunk["id"] for chunk in rebuilt.json()["chunks"]] == [chunk["id"] for chunk in result["chunks"]]
    assert internal_has_import_chunk
    search_result = search.json()
    assert search_result["query"] == "Where is authentication token verification handled?"
    assert len(search_result["results"]) == 3
    assert search_result["results"][0]["path"] in {"pkg/auth.py", "pkg/service.py"}
    assert search_result["results"][0]["symbol"] in {"verify", "authenticate"}
    assert "token" in search_result["results"][0]["excerpt"]
    assert 0 <= search_result["results"][0]["score"] <= 1
    assert deleted.status_code == 204
    assert missing_after_delete.status_code == 404


def test_vector_store_ranks_related_chunks() -> None:
    embedder = FeatureHashEmbedder(dimensions=64)
    store = RepositoryIndexStore()
    index = RepositoryIndex(
        workspace_id="workspace",
        indexed_at=datetime.now(timezone.utc),
        files=[],
        symbols=[],
        nodes=[],
        edges=[],
        chunks=[],
        stats=IndexStats(
            file_count=0,
            symbol_count=0,
            edge_count=0,
            chunk_count=0,
            embedded_chunk_count=2,
            languages={},
        ),
    )
    store.put(
        "workspace",
        index,
        datetime.now(timezone.utc) + timedelta(minutes=1),
        [
            VectorEntry("authentication", embedder.embed("authentication token password")),
            VectorEntry("database", embedder.embed("database migration schema")),
        ],
    )

    matches = store.search("workspace", embedder.embed("password authentication"), limit=2)

    assert matches[0][0] == "authentication"
