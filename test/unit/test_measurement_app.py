"""Annotation server: file-backed, blind, append-only."""

from __future__ import annotations

from fastapi.testclient import TestClient

from src.measurement_extraction.app import create_app


def _client(tmp_path) -> TestClient:
    (tmp_path / "dev.csv").write_text(
        'item_code,item_name\n0012,"קינמון טחון 1 ק""ג"\n', encoding="utf-8"
    )
    return TestClient(create_app(tmp_path / "gold" / "a.jsonl", tmp_path))


def test_items_blind_and_ids_are_strings(tmp_path) -> None:
    item = _client(tmp_path).get("/api/items?split=dev").json()[0]
    assert (
        item["item_code"] == "0012"
        and item["annotation"] is None
        and item["state"] == "unreviewed"
    )
    assert item["item_name"] == 'קינמון טחון 1 ק"ג'


def test_save_appends_and_correction_needs_reason(tmp_path) -> None:
    client = _client(tmp_path)
    body = {"state": "saved", "annotation": {"has_measurement": False}}
    assert client.put("/api/items/0012", json=body).json()["state"] == "saved"
    assert client.put("/api/items/0012", json=body).status_code == 422
    assert (
        client.put("/api/items/0012", json={**body, "reason": "policy"}).json()[
            "revision"
        ]
        == 2
    )
    assert len(client.get("/api/gold.jsonl").text.splitlines()) == 2


def test_undo_restores_previous_revision(tmp_path) -> None:
    client = _client(tmp_path)
    yes = {"has_measurement": True, "measurements": [{"source_text": "1"}]}
    client.put("/api/items/0012", json={"state": "draft", "annotation": yes})
    client.put(
        "/api/items/0012",
        json={"state": "draft", "annotation": {"has_measurement": False}},
    )
    assert (
        client.post("/api/items/0012/undo").json()["annotation"]["has_measurement"]
        is True
    )


def test_invalid_and_unknown(tmp_path) -> None:
    client = _client(tmp_path)
    bad = {
        "state": "saved",
        "annotation": {"has_measurement": True, "measurements": []},
    }
    assert client.put("/api/items/0012", json=bad).status_code == 422
    assert client.put("/api/items/nope", json={"state": "draft"}).status_code == 404
    assert "aliases" in client.get("/units.json").json()
