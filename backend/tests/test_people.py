"""Comments, profiles and the people list."""

from __future__ import annotations

from sqlalchemy import create_engine, text

from conftest import STREAM_A
from helpers import comment, create_card, me, vote


def test_comment_lifecycle_and_permissions(client, alice, bob):
    card_id = create_card(client, alice)["id"]
    first = comment(client, bob, card_id, "First!")
    assert first["is_mine"] and first["author"]["name"] == "Bob Student"

    url = f"/api/comments/{first['id']}"
    assert client.patch(url, json={"text": "Alice edits"}, headers=alice.headers).status_code == 403
    assert client.delete(url, headers=alice.headers).status_code == 403

    edited = client.patch(url, json={"text": "First! (edited)"}, headers=bob.headers).json()
    assert edited["text"] == "First! (edited)"
    assert edited["updated_at"] >= edited["created_at"]

    blank = client.post(f"/api/cards/{card_id}/comments", json={"text": "  "}, headers=bob.headers)
    assert blank.status_code == 422

    listed = client.get(f"/api/cards/{card_id}/comments", headers=alice.headers).json()
    assert [c["text"] for c in listed] == ["First! (edited)"]
    assert listed[0]["is_mine"] is False
    assert client.get(f"/api/cards/{card_id}", headers=alice.headers).json()["comments_count"] == 1

    assert client.delete(url, headers=bob.headers).status_code == 204
    assert client.get(f"/api/cards/{card_id}/comments", headers=alice.headers).json() == []


def test_deleting_a_card_removes_its_votes_and_comments(client, database_url, alice, bob):
    card_id = create_card(client, alice)["id"]
    vote(client, bob, card_id, "up")
    comment(client, bob, card_id, "bye")
    assert client.delete(f"/api/cards/{card_id}", headers=alice.headers).status_code == 204

    engine = create_engine(database_url)
    try:
        with engine.connect() as connection:
            left = connection.execute(
                text(
                    "SELECT (SELECT count(*) FROM votes WHERE card_id = :id)"
                    " + (SELECT count(*) FROM comments WHERE card_id = :id)"
                ),
                {"id": card_id},
            ).scalar()
    finally:
        engine.dispose()
    assert left == 0


def test_profile_update_and_validation(client, alice):
    updated = client.patch(
        "/api/me", json={"status": "Busy", "telegram": "@alice_dev", "bio": ""}, headers=alice.headers
    )
    assert updated.status_code == 200
    body = updated.json()
    assert (body["status"], body["telegram"], body["bio"]) == ("Busy", "alice_dev", None)

    for bad in (
        {"telegram": "@ab"},
        {"email": "nope"},
        {"name": None},
        {"name": ""},
        {"avatar_url": "ftp://example.com/a.png"},
        {"status": "x" * 101},
    ):
        response = client.patch("/api/me", json=bad, headers=alice.headers)
        assert response.status_code == 422, bad
        assert response.json()["errors"][0]["field"] == next(iter(bad))

    def message(body):
        return client.patch("/api/me", json=body, headers=alice.headers).json()["errors"][0]["message"]

    assert message({"email": "nope"}) == "Некорректный email"
    assert message({"telegram": "a" * 34}) == "Максимум 33 символа"


def test_email_must_be_unique_within_the_stream(client, alice, bob, carol):
    bob_email = me(client, bob)["email"]

    taken = client.patch("/api/me", json={"email": bob_email.upper()}, headers=alice.headers)
    assert taken.status_code == 409
    assert taken.json()["errors"] == [{"field": "email", "message": "Этот email уже занят"}]

    assert client.patch("/api/me", json={"email": "alice@example.com"}, headers=alice.headers).status_code == 200
    # Uniqueness is per stream: another stream may use the same address.
    assert client.patch("/api/me", json={"email": bob_email}, headers=carol.headers).status_code == 200


def test_people_list_includes_classmates_who_never_called(client, platform, alice):
    quiet = platform.add("quiet", STREAM_A, code="26F")

    people = client.get("/api/users", headers=alice.headers).json()
    assert [p["name"] for p in people] == ["Alice Student", "Quiet Student"]  # by name
    assert "email" not in people[1]
    found = client.get("/api/users?q=qui", headers=alice.headers).json()
    assert [p["name"] for p in found] == ["Quiet Student"]

    assert me(client, quiet)["id"] == people[1]["id"]  # the provisioned row is reused


def test_user_detail_has_activity_counters(client, alice, bob):
    card_id = create_card(client, alice)["id"]
    vote(client, bob, card_id, "up")
    comment(client, bob, card_id, "Hi")

    detail = client.get(f"/api/users/{me(client, alice)['id']}", headers=bob.headers).json()
    counters = (detail["cards_count"], detail["comments_count"], detail["total_score"], detail["is_me"])
    assert counters == (1, 0, 1, False)
    assert "email" not in detail
