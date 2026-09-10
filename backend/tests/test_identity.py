"""Identity: tokens, the platform contract, caching, limits, CORS and docs.

Covers acceptance criteria 1-3 and 6-9.
"""

from __future__ import annotations

import json

import httpx

from conftest import FakeClock
from helpers import me


def test_missing_token_is_401_with_a_hint(client):
    response = client.get("/api/cards")
    assert response.status_code == 401
    assert "Нет заголовка X-Course-Token" in response.json()["detail"]


def test_token_sent_as_authorization_gets_a_specific_hint(client, alice):
    response = client.get("/api/cards", headers={"Authorization": f"Bearer {alice.token}"})
    assert response.status_code == 401
    assert "а не в Authorization" in response.json()["detail"]


def test_garbage_tokens_are_401_not_500(client, platform):
    assert client.get("/api/cards", headers={"X-Course-Token": "hello"}).status_code == 401
    assert client.get("/api/cards", headers={"X-Course-Token": "exb_" + "x" * 500}).status_code == 401
    assert platform.introspect_calls == 0  # rejected without bothering the platform

    assert client.get("/api/cards", headers={"X-Course-Token": "exb_unknown"}).status_code == 401
    assert platform.introspect_calls == 1


def test_pasted_quotes_and_bearer_prefix_are_forgiven(client, alice):
    for value in (f'"{alice.token}"', f"Bearer {alice.token}", f"  {alice.token}  "):
        assert client.get("/api/me", headers={"X-Course-Token": value}).status_code == 200


def test_first_contact_provisions_the_profile_from_the_platform(client, alice):
    profile = me(client, alice)
    assert profile["name"] == "Alice Student"
    assert profile["email"] == "alice@example.com"
    assert profile["avatar_url"] == "https://example.com/avatars/alice.png"
    assert profile["stream"] == {"id": str(alice.stream_id), "code": "26F", "title": None, "name": "26F"}


def test_platform_changes_never_overwrite_local_edits(client, alice):
    assert client.patch("/api/me", json={"name": "Alice Local"}, headers=alice.headers).status_code == 200
    alice.display_name = "Alice Renamed Upstream"
    alice.avatar_url = "https://example.com/new.png"
    client.app.state.identity.forget_all()

    profile = me(client, alice)
    assert profile["name"] == "Alice Local"
    assert profile["avatar_url"] == "https://example.com/avatars/alice.png"


def test_revoked_token_stops_working_within_the_cache_ttl(client, platform, alice):
    clock = FakeClock()
    client.app.state.identity.clock = clock
    assert client.get("/api/me", headers=alice.headers).status_code == 200

    platform.revoke(alice)
    assert client.get("/api/me", headers=alice.headers).status_code == 200  # still cached

    clock.advance(client.app.state.settings.identity_cache_ttl_seconds + 1)
    assert client.get("/api/me", headers=alice.headers).status_code == 401


def test_identity_is_cached_between_requests(client, platform, alice):
    for _ in range(5):
        me(client, alice)
    assert platform.introspect_calls == 1


def test_wrong_service_key_is_500_never_401(client, platform, alice):
    platform.service_key = "exbk_rotated_elsewhere"
    response = client.get("/api/cards", headers=alice.headers)
    assert response.status_code == 500
    assert "сервисный ключ" in response.json()["detail"]


def test_platform_outage_is_503(client, platform, alice):
    platform.down = True
    assert client.get("/api/cards", headers=alice.headers).status_code == 503


def test_platform_timeout_is_503(client, platform, alice):
    platform.raise_error = httpx.ConnectTimeout("timed out")
    assert client.get("/api/cards", headers=alice.headers).status_code == 503


def test_fresh_cached_identity_survives_an_outage(client, platform, alice):
    me(client, alice)
    platform.down = True
    assert client.get("/api/me", headers=alice.headers).status_code == 200


def test_health_needs_no_token(client):
    response = client.get("/health")
    assert (response.status_code, response.json()) == (200, {"status": "ok"})


def test_docs_work_behind_the_path_prefix(make_client):
    prefix = "/example-backend/frontend-itam"
    public = f"https://courses.example{prefix}"
    proxied = make_client(root_path=prefix, public_base_url=public)

    # The edge proxy has already stripped the prefix by the time requests arrive.
    docs = proxied.get("/docs")
    assert docs.status_code == 200
    assert f"{prefix}/openapi.json" in docs.text
    assert proxied.get("/openapi.json").json()["servers"] == [{"url": public, "description": "Публичный API"}]
    assert proxied.get("/health").status_code == 200

    without_public_url = make_client(root_path=prefix)
    assert without_public_url.get("/openapi.json").json()["servers"] == [{"url": prefix}]


def test_openapi_documents_a_single_error_shape(client):
    spec = client.get("/openapi.json").json()
    assert "HTTPValidationError" not in json.dumps(spec)
    assert "ValidationErrorResponse" in spec["components"]["schemas"]


def test_openapi_is_russian_and_card_dates_are_integers(client):
    spec = client.get("/openapi.json").json()
    assert "Successful Response" not in json.dumps(spec)
    assert "## 3. Правила" in spec["info"]["description"]
    schemas = spec["components"]["schemas"]
    assert {"type": "integer", "minimum": 0, "maximum": 4102444799} in schemas["CardCreate"]["properties"]["date"]["anyOf"]
    assert {"type": "integer"} in schemas["Card"]["properties"]["date"]["anyOf"]


def test_rate_limit_is_429_with_retry_after(make_client, alice):
    limited = make_client(rate_limit_per_second=0.01, rate_limit_burst=3)
    codes = [limited.get("/api/me", headers=alice.headers).status_code for _ in range(4)]
    assert codes == [200, 200, 200, 429]

    response = limited.get("/api/me", headers=alice.headers)
    assert int(response.headers["Retry-After"]) >= 1
    assert "useEffect" in response.json()["detail"]


def test_cors_preflight_is_open_and_cheap(client):
    response = client.options(
        "/api/cards",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "x-course-token,content-type",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "*"
    assert "x-course-token" in response.headers["access-control-allow-headers"].lower()
    assert response.headers["access-control-max-age"] == "86400"


def test_errors_carry_cors_headers(client):
    response = client.get("/api/cards", headers={"Origin": "http://localhost:5173"})
    assert response.status_code == 401
    assert response.headers["access-control-allow-origin"] == "*"


def test_unknown_endpoint_explains_itself(client):
    response = client.get("/cards")
    assert response.status_code == 404
    assert "/api" in response.json()["detail"]
