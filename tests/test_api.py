"""API contract and input-validation tests (no database or provider access required)."""
import pytest
from fastapi.testclient import TestClient

from backend.api.main import app

client = TestClient(app)


def test_health_reports_status_and_version():
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "healthy"
    assert "version" in body


def test_upload_rejects_unsupported_extension():
    response = client.post(
        "/api/contracts/upload",
        files={"file": ("payload.exe", b"binary", "application/octet-stream")},
    )
    assert response.status_code == 400


def test_upload_rejects_oversized_file(monkeypatch):
    from backend.core.config import settings

    monkeypatch.setattr(settings, "max_upload_mb", 0)
    response = client.post(
        "/api/contracts/upload",
        files={"file": ("big.txt", b"x" * 10, "text/plain")},
    )
    assert response.status_code == 413


@pytest.mark.parametrize("bad_id", ["not-a-uuid", '" or contract_id != "', "1; DROP TABLE contracts"])
def test_search_rejects_non_uuid_contract_filter(bad_id):
    response = client.post("/api/contracts/search", json={"query": "termination", "contract_id": bad_id})
    assert response.status_code == 422


def test_review_rejects_non_uuid_contract_id():
    response = client.post("/api/contracts/review", json={"contract_id": "abc"})
    assert response.status_code == 422


def test_path_parameter_must_be_uuid():
    response = client.get("/api/contracts/not-a-uuid/reviews")
    assert response.status_code == 400


def test_contract_filter_rejects_expression_injection():
    from backend.db.milvus_client import contract_filter

    valid = "3f2b8c1e-9a4d-4e7b-8f10-2d5c6a7b8c9d"
    assert contract_filter(valid) == f'contract_id == "{valid}"'
    with pytest.raises(ValueError):
        contract_filter('x" or contract_id != "')
