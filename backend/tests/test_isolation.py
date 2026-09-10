"""Streams are a hard partition (acceptance criteria 4 and 5).

Cross-stream leakage is the one bug that would quietly ruin the exercise, and
it stays invisible until two cohorts overlap, so these tests go at it head-on.
"""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError

from app import seed
from conftest import STREAM_A, STREAM_B
from helpers import comment, create_card, ids, me, names, vote


def test_same_stream_students_see_and_interact(client, alice, bob):
    card = create_card(client, alice, title="Alice's idea")

    assert card["id"] in ids(client.get("/api/cards", headers=bob.headers).json())

    voted = vote(client, bob, card["id"], "up")
    assert (voted["score"], voted["my_vote"], voted["is_mine"]) == (1, "up", False)

    comment(client, bob, card["id"], "Nice!")

    detail = client.get(f"/api/cards/{card['id']}", headers=alice.headers).json()
    assert detail["upvotes"] == 1
    assert detail["my_vote"] is None
    assert [c["text"] for c in detail["comments"]] == ["Nice!"]
    assert detail["comments"][0]["author"]["name"] == "Bob Student"

    assert "Bob Student" in names(client.get("/api/users", headers=alice.headers).json())
    bob_id = me(client, bob)["id"]
    assert client.get(f"/api/users/{bob_id}", headers=alice.headers).status_code == 200


def test_other_stream_cannot_see(client, alice, bob, carol):
    card = create_card(client, alice)
    comment(client, bob, card["id"], "Stream A only")
    alice_id = me(client, alice)["id"]

    carol_board = client.get("/api/cards", headers=carol.headers).json()
    assert card["id"] not in ids(carol_board)
    assert not {"Alice Student", "Bob Student"} & {c["author"]["name"] for c in carol_board}

    assert client.get(f"/api/cards/{card['id']}", headers=carol.headers).status_code == 404
    assert client.get(f"/api/cards/{card['id']}/comments", headers=carol.headers).status_code == 404
    assert client.get(f"/api/users/{alice_id}", headers=carol.headers).status_code == 404
    assert client.get(f"/api/cards?author_id={alice_id}", headers=carol.headers).json() == []

    carol_people = names(client.get("/api/users", headers=carol.headers).json())
    assert not {"Alice Student", "Bob Student"} & carol_people

    board = client.get("/api/board", headers=carol.headers).json()
    assert board["cards_count"] == len(seed.CARDS)
    assert board["members_count"] == 1


def test_other_stream_cannot_mutate_by_known_id(client, alice, bob, carol):
    card = create_card(client, alice, title="Original")
    bobs = comment(client, bob, card["id"], "Original comment")
    card_url = f"/api/cards/{card['id']}"
    comment_url = f"/api/comments/{bobs['id']}"
    h = carol.headers

    assert client.patch(card_url, json={"title": "Hacked"}, headers=h).status_code == 404
    assert client.put(f"{card_url}/vote", json={"value": "down"}, headers=h).status_code == 404
    assert client.delete(f"{card_url}/vote", headers=h).status_code == 404
    assert client.post(f"{card_url}/comments", json={"text": "Hi from B"}, headers=h).status_code == 404
    assert client.patch(comment_url, json={"text": "Hacked"}, headers=h).status_code == 404
    assert client.delete(comment_url, headers=h).status_code == 404
    assert client.delete(card_url, headers=h).status_code == 404

    after = client.get(card_url, headers=alice.headers).json()
    assert after["title"] == "Original"
    assert (after["upvotes"], after["downvotes"]) == (0, 0)
    assert [c["text"] for c in after["comments"]] == ["Original comment"]


def test_students_without_a_stream_are_isolated_too(client, alice, nora):
    alice_card = create_card(client, alice)
    nora_card = create_card(client, nora)

    assert alice_card["id"] not in ids(client.get("/api/cards", headers=nora.headers).json())
    assert nora_card["id"] not in ids(client.get("/api/cards", headers=alice.headers).json())
    assert client.get(f"/api/cards/{alice_card['id']}", headers=nora.headers).status_code == 404
    assert client.get(f"/api/cards/{nora_card['id']}", headers=alice.headers).status_code == 404
    assert me(client, nora)["stream"] == {"id": None, "code": None, "title": None, "name": "Без потока"}


def test_each_stream_gets_its_own_seeded_board(client, alice, carol):
    board_a = client.get("/api/cards", headers=alice.headers).json()
    board_b = client.get("/api/cards", headers=carol.headers).json()
    assert len(board_a) == len(board_b) == len(seed.CARDS)
    assert not ids(board_a) & ids(board_b)


def test_database_refuses_rows_that_cross_streams(client, database_url, alice, carol):
    card = create_card(client, alice)
    alice_id, carol_id = me(client, alice)["id"], me(client, carol)["id"]
    insert_vote = text(
        "INSERT INTO votes (card_id, user_id, stream_id, value) VALUES (:card, :user, :stream, 1)"
    )
    engine = create_engine(database_url)
    try:
        # Stream B's student voting on stream A's card, under either stream id.
        for stream in (STREAM_A, STREAM_B):
            with pytest.raises(IntegrityError), engine.begin() as connection:
                connection.execute(insert_vote, {"card": card["id"], "user": carol_id, "stream": stream})
        # A card in stream B authored by a stream A user.
        with pytest.raises(IntegrityError), engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO cards (id, stream_id, author_id, title, type) "
                    "VALUES (gen_random_uuid(), :stream, :author, 'x', 'idea')"
                ),
                {"stream": STREAM_B, "author": alice_id},
            )
    finally:
        engine.dispose()
