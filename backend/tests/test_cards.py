"""The board: seeding, cards, votes and thresholds (acceptance criterion 10 included)."""

from __future__ import annotations

from app import seed
from conftest import ADMIN_HEADERS, STREAM_A
from helpers import create_card, me, vote

COLUMNS = ["event", "idea", "question", "accepted", "rejected"]


def test_a_new_stream_starts_with_a_demo_board(client, alice):
    cards = client.get("/api/cards", headers=alice.headers).json()
    assert len(cards) == len(seed.CARDS)
    assert {card["column"] for card in cards} == set(COLUMNS)
    assert all(card["author"]["is_demo"] for card in cards)
    dates = [card["date"] for card in cards if card["date"] is not None]
    assert dates and all(isinstance(date, int) for date in dates)

    board = client.get("/api/board", headers=alice.headers).json()
    assert [column["id"] for column in board["columns"]] == COLUMNS
    assert sum(column["cards_count"] for column in board["columns"]) == board["cards_count"] == len(cards)
    assert (board["accept_threshold"], board["reject_threshold"]) == (5, 5)


def test_the_demo_board_is_seeded_once_per_stream(client, alice, bob):
    me(client, alice)
    assert len(client.get("/api/cards", headers=bob.headers).json()) == len(seed.CARDS)


def test_create_card_returns_the_full_card(client, alice):
    card = create_card(
        client,
        alice,
        title="  Hackathon  ",
        type="event",
        description="",
        date=1790870400,
        preview="https://example.com/p.png",
    )
    assert card["title"] == "Hackathon"
    assert card["description"] is None
    assert (card["type"], card["column"], card["date"]) == ("event", "event", 1790870400)
    assert (card["score"], card["votes_count"], card["comments_count"], card["my_vote"]) == (0, 0, 0, None)
    assert (card["votes_to_accept"], card["votes_to_reject"]) == (5, 5)
    assert card["is_mine"] and card["author"]["is_me"]


def test_card_validation_errors_point_at_fields(client, alice):
    def problems(body):
        response = client.post("/api/cards", json=body, headers=alice.headers)
        assert response.status_code == 422, response.text
        return response.json()

    missing = problems({"type": "idea"})
    assert missing["errors"] == [{"field": "title", "message": "Обязательное поле"}]
    assert missing["detail"] == "title: Обязательное поле"

    assert problems({"title": "x", "type": "accepted"})["errors"] == [
        {"field": "type", "message": "Допустимые значения: 'event', 'idea', 'question'"}
    ]
    assert problems({"title": "   ", "type": "idea"})["errors"] == [
        {"field": "title", "message": "Не может быть пустым"}
    ]
    assert problems({"title": "x" * 121, "type": "idea"})["errors"][0]["message"] == "Максимум 120 символов"
    assert problems({"title": "x", "type": "idea", "preview": "not-a-link"})["errors"][0]["field"] == "preview"
    assert problems({"title": "x", "type": "idea", "date": "tomorrow"})["errors"][0]["field"] == "date"
    assert problems({"title": "x", "type": "idea", "descripton": "typo"})["errors"][0]["field"] == "descripton"


def test_card_dates_are_unix_seconds(client, alice):
    url = f"/api/cards/{create_card(client, alice, date=1790870400)['id']}"

    moved = client.patch(url, json={"date": 1791648000.0}, headers=alice.headers)
    assert (moved.status_code, moved.json()["date"]) == (200, 1791648000)
    assert client.patch(url, json={"date": ""}, headers=alice.headers).json()["date"] is None

    def date_error(value):
        response = client.patch(url, json={"date": value}, headers=alice.headers)
        assert response.status_code == 422, value
        [error] = response.json()["errors"]
        assert error["field"] == "date"
        return error["message"]

    assert "миллисекунды" in date_error(1790870400000)  # Date.now() sent as is
    assert "Math.floor" in date_error(1790870400.5)
    assert "Unix-время" in date_error("2026-10-01")
    assert "1970" in date_error(-1)


def test_non_json_body_gets_a_clear_message(client, alice):
    response = client.post(
        "/api/cards",
        content='{"title": "x", "type": "idea"}',
        headers={**alice.headers, "Content-Type": "text/plain"},
    )
    assert response.status_code == 422
    assert "Content-Type: application/json" in response.json()["detail"]


def test_data_uri_previews_are_accepted(client, alice):
    card = create_card(client, alice, preview="data:image/png;base64,iVBORw0KGgo=")
    assert card["preview"].startswith("data:image/png")


def test_only_the_author_can_edit_or_delete(client, alice, bob):
    url = f"/api/cards/{create_card(client, alice)['id']}"
    assert client.patch(url, json={"title": "Bob was here"}, headers=bob.headers).status_code == 403
    assert client.delete(url, headers=bob.headers).status_code == 403

    edited = client.patch(url, json={"type": "question", "description": "Now a question"}, headers=alice.headers)
    assert edited.status_code == 200
    assert (edited.json()["type"], edited.json()["column"]) == ("question", "question")

    no_title = client.patch(url, json={"title": None}, headers=alice.headers)
    assert (no_title.status_code, no_title.json()["errors"][0]["message"]) == (422, "Не может быть null")
    assert client.patch(url, json={"description": None}, headers=alice.headers).json()["description"] is None

    assert client.delete(url, headers=alice.headers).status_code == 204
    assert client.get(url, headers=alice.headers).status_code == 404


def test_you_cannot_vote_on_your_own_card(client, alice):
    card = create_card(client, alice)
    response = client.put(f"/api/cards/{card['id']}/vote", json={"value": "up"}, headers=alice.headers)
    assert response.status_code == 403


def test_voting_updates_score_and_stance(client, alice, bob):
    card_id = create_card(client, alice)["id"]
    assert vote(client, bob, card_id, "up")["score"] == 1
    assert vote(client, bob, card_id, "up")["score"] == 1  # repeating is harmless

    down = vote(client, bob, card_id, "down")
    assert (down["score"], down["upvotes"], down["downvotes"], down["my_vote"]) == (-1, 0, 1, "down")

    removed = client.delete(f"/api/cards/{card_id}/vote", headers=bob.headers).json()
    assert (removed["score"], removed["my_vote"]) == (0, None)
    assert client.delete(f"/api/cards/{card_id}/vote", headers=bob.headers).status_code == 200


def test_thresholds_move_cards_but_keep_their_type(client, platform, alice, bob):
    dave = platform.add("dave", STREAM_A, code="26F")
    updated = client.patch(
        "/api/admin/settings", json={"accept_threshold": 2, "reject_threshold": 1}, headers=ADMIN_HEADERS
    )
    assert updated.status_code == 200

    card_id = create_card(client, alice, type="question")["id"]
    once = vote(client, bob, card_id, "up")
    assert (once["column"], once["votes_to_accept"]) == ("question", 1)

    accepted = vote(client, dave, card_id, "up")
    assert (accepted["column"], accepted["is_accepted"], accepted["type"]) == ("accepted", True, "question")
    assert accepted["votes_to_accept"] == 0

    retyped = client.patch(f"/api/cards/{card_id}", json={"type": "event"}, headers=alice.headers).json()
    assert (retyped["column"], retyped["type"]) == ("accepted", "event")

    assert vote(client, dave, card_id, "down")["column"] == "event"  # score 0: back to its type
    rejected = vote(client, bob, card_id, "down")
    assert (rejected["column"], rejected["is_rejected"], rejected["score"]) == ("rejected", True, -2)


def test_lowering_a_threshold_reclassifies_existing_cards(client, alice):
    cards = client.get("/api/cards", headers=alice.headers).json()
    token_question = next(c for c in cards if c["title"] == "Где взять свой токен для API?")
    assert (token_question["score"], token_question["column"]) == (4, "question")

    client.patch("/api/admin/settings", json={"accept_threshold": 4}, headers=ADMIN_HEADERS)
    again = client.get(f"/api/cards/{token_question['id']}", headers=alice.headers).json()
    assert again["column"] == "accepted"


def test_card_filters_and_sorting(client, alice, bob):
    mine = create_card(client, alice, title="Unique needle", type="event")
    alice_id = me(client, alice)["id"]

    def listed(query):
        response = client.get(f"/api/cards{query}", headers=bob.headers)
        assert response.status_code == 200, response.text
        return response.json()

    assert [c["id"] for c in listed(f"?author_id={alice_id}")] == [mine["id"]]
    assert [c["id"] for c in listed("?q=NEEDLE")] == [mine["id"]]
    accepted = listed("?column=accepted")
    assert accepted and all(c["column"] == "accepted" for c in accepted)
    scores = [c["score"] for c in listed("?sort=top")]
    assert scores == sorted(scores, reverse=True)
    assert listed("")[0]["id"] == mine["id"]
    assert listed("?sort=old")[-1]["id"] == mine["id"]
    assert client.get("/api/cards?sort=best", headers=bob.headers).status_code == 422
