"""The course-team API behind X-Admin-Token."""

from __future__ import annotations

from app import seed
from conftest import ADMIN_HEADERS
from helpers import comment, create_card, me


def test_admin_endpoints_need_the_admin_token(client, alice):
    assert client.get("/api/admin/settings").status_code == 401
    assert client.get("/api/admin/settings", headers=alice.headers).status_code == 401
    assert client.get("/api/admin/settings", headers={"X-Admin-Token": "nope"}).status_code == 403
    assert client.get("/api/admin/settings", headers=ADMIN_HEADERS).status_code == 200


def test_admin_api_is_off_without_a_configured_token(make_client):
    disabled = make_client(admin_token="")
    assert disabled.get("/api/admin/settings", headers=ADMIN_HEADERS).status_code == 503


def test_thresholds_are_validated(client):
    for bad in ({"accept_threshold": 0}, {"reject_threshold": -1}, {"accept_threshold": None}):
        assert client.patch("/api/admin/settings", json=bad, headers=ADMIN_HEADERS).status_code == 422

    response = client.patch("/api/admin/settings", json={"reject_threshold": 7}, headers=ADMIN_HEADERS)
    assert (response.json()["accept_threshold"], response.json()["reject_threshold"]) == (5, 7)


def test_streams_overview(client, alice, bob, carol, nora):
    for student in (alice, bob, carol, nora):
        me(client, student)

    streams = {s["code"]: s for s in client.get("/api/admin/streams", headers=ADMIN_HEADERS).json()}
    assert streams["26F"]["members_count"] == 2
    assert streams["27S"]["members_count"] == 1
    assert (streams[None]["id"], streams[None]["name"]) == (None, "Без потока")
    assert all(s["cards_count"] == len(seed.CARDS) for s in streams.values())


def test_admin_can_moderate_any_stream(client, alice, bob):
    card_id = create_card(client, alice)["id"]
    comment_id = comment(client, bob, card_id, "spam")["id"]

    assert client.delete(f"/api/admin/comments/{comment_id}", headers=ADMIN_HEADERS).status_code == 204
    assert client.delete(f"/api/admin/cards/{card_id}", headers=ADMIN_HEADERS).status_code == 204
    assert client.get(f"/api/cards/{card_id}", headers=alice.headers).status_code == 404
    assert client.delete(f"/api/admin/cards/{card_id}", headers=ADMIN_HEADERS).status_code == 404
