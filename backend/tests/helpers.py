from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from conftest import Student


def create_card(client: TestClient, student: Student, **fields: Any) -> dict[str, Any]:
    body = {"title": "Test card", "type": "idea", **fields}
    response = client.post("/api/cards", json=body, headers=student.headers)
    assert response.status_code == 201, response.text
    return response.json()


def comment(client: TestClient, student: Student, card_id: str, text: str) -> dict[str, Any]:
    response = client.post(f"/api/cards/{card_id}/comments", json={"text": text}, headers=student.headers)
    assert response.status_code == 201, response.text
    return response.json()


def vote(client: TestClient, student: Student, card_id: str, value: str) -> dict[str, Any]:
    response = client.put(f"/api/cards/{card_id}/vote", json={"value": value}, headers=student.headers)
    assert response.status_code == 200, response.text
    return response.json()


def me(client: TestClient, student: Student) -> dict[str, Any]:
    response = client.get("/api/me", headers=student.headers)
    assert response.status_code == 200, response.text
    return response.json()


def ids(items: list[dict[str, Any]]) -> set[str]:
    return {item["id"] for item in items}


def names(items: list[dict[str, Any]]) -> set[str]:
    return {item["name"] for item in items}
