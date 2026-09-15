"""Backend test fixtures using an isolated temporary SQLite database."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path, monkeypatch):
    database_path = tmp_path / "test.db"
    from backend.app.main import create_app
    monkeypatch.delenv("VECTORGATE_CLASSIFIER_ENABLED", raising=False)

    with TestClient(create_app(f"sqlite:///{database_path}")) as test_client:
        yield test_client
