"""Who is calling: exchanging a student's course token for their identity.

Students never log in. Their frontend sends a personal token in the
`X-Course-Token` header, and we ask the course platform whose it is. Two
failure modes must stay distinct:

- the platform does not know the *token* (404): the student's problem, so 401;
- the platform refuses *our service key* (401): our problem, so 500.

If they were collapsed, a rotated service key would look to every student as
if their own token had expired.
"""

from __future__ import annotations

import hashlib
import logging
import threading
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import httpx
from fastapi import HTTPException, status

logger = logging.getLogger(__name__)

TOKEN_HEADER = "X-Course-Token"
TOKEN_PREFIX = "exb_"
TOKEN_MAX_LENGTH = 200
TOKEN_PAGE_HINT = "Copy your token from the course page (tab «API проекта»)."


@dataclass(frozen=True)
class PlatformStream:
    id: uuid.UUID | None
    code: str | None
    title: str | None


@dataclass(frozen=True)
class PlatformUser:
    id: uuid.UUID
    email: str | None
    display_name: str | None
    name: str | None
    surname: str | None
    avatar_url: str | None

    @property
    def full_name(self) -> str:
        """The best display name the platform gave us."""
        joined = " ".join(part for part in (self.name, self.surname) if part)
        local_part = (self.email or "").split("@")[0]
        return (self.display_name or joined or local_part or "Student").strip()


@dataclass(frozen=True)
class Identity:
    user: PlatformUser
    stream: PlatformStream


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def invalid_token() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=(
            "Your course token is not valid: it may have been reset, or you no longer have "
            f"access to the course. {TOKEN_PAGE_HINT}"
        ),
    )


def platform_unavailable() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=(
            "The course platform is not responding, so we can't check your token right now. "
            "Please try again in a minute."
        ),
    )


def platform_misconfigured() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=(
            "The board API is misconfigured on the server: the course platform rejected its "
            "service key. Your token is fine; please tell the course team."
        ),
    )


class TokenRejected(Exception):
    """The platform does not know this token (unknown, rotated or access revoked)."""


def _parse_user(data: dict[str, Any]) -> PlatformUser:
    return PlatformUser(
        id=uuid.UUID(str(data["id"])),
        email=data.get("email"),
        display_name=data.get("display_name"),
        name=data.get("name"),
        surname=data.get("surname"),
        avatar_url=data.get("avatar_url"),
    )


def _parse_stream(data: dict[str, Any] | None) -> PlatformStream:
    data = data or {}
    raw_id = data.get("id")
    return PlatformStream(
        id=uuid.UUID(str(raw_id)) if raw_id else None,
        code=data.get("code"),
        title=data.get("title"),
    )


class PlatformClient:
    """Talks to the course platform's service API using our service key."""

    def __init__(
        self,
        *,
        base_url: str,
        service_key: str,
        backend_slug: str,
        timeout: float,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._slug = backend_slug
        self._prefix = f"/api/v1/example-backends/{backend_slug}"
        self._http = httpx.Client(
            base_url=base_url.rstrip("/"),
            headers={"Authorization": f"Bearer {service_key}"},
            timeout=timeout,
            transport=transport,
        )

    def close(self) -> None:
        self._http.close()

    def introspect(self, token: str) -> Identity:
        response = self._request("POST", "/introspect", json={"token": token})
        # 404 is the platform's "no such token"; 400/422 means it can't even be one.
        if response.status_code in (400, 404, 422):
            raise TokenRejected
        self._check(response)
        payload = response.json()
        return Identity(user=_parse_user(payload["user"]), stream=_parse_stream(payload.get("stream")))

    def stream_members(self, stream_id: uuid.UUID) -> list[PlatformUser]:
        response = self._request("GET", f"/streams/{stream_id}/members")
        self._check(response)
        return [_parse_user(member) for member in response.json().get("members", [])]

    def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        try:
            return self._http.request(method, self._prefix + path, **kwargs)
        except httpx.HTTPError as exc:  # timeouts, DNS failures, refused connections
            logger.warning("Course platform unreachable (%s %s): %r", method, path, exc)
            raise platform_unavailable() from exc

    def _check(self, response: httpx.Response) -> None:
        code = response.status_code
        if code == 200:
            return
        if code in (401, 403):
            logger.error(
                "The course platform REJECTED OUR SERVICE KEY (HTTP %s) for backend %r. Every "
                "student request fails with 500 until PLATFORM_SERVICE_KEY is fixed. Was the key "
                "rotated, or the backend disabled in the admin app?",
                code,
                self._slug,
            )
            raise platform_misconfigured()
        if code == 429 or code >= 500:
            logger.warning("Course platform answered HTTP %s", code)
            raise platform_unavailable()
        logger.error("Unexpected course platform response HTTP %s: %s", code, response.text[:500])
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="The course platform gave an unexpected answer. Please tell the course team.",
        )


class IdentityResolver:
    """Resolves tokens through the platform and remembers the answers briefly.

    A known token is cached for `ttl` seconds and an unknown one for only
    `negative_ttl`. The positive cache is short so a reset or revoked token
    stops working quickly. The negative cache is even shorter so a student
    who has just reset their token isn't locked out.
    """

    MAX_ENTRIES = 10_000

    def __init__(
        self,
        client: PlatformClient,
        *,
        ttl: float,
        negative_ttl: float,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.client = client
        self.ttl = ttl
        self.negative_ttl = negative_ttl
        self.clock = clock
        self._entries: dict[str, tuple[float, Identity | None]] = {}
        self._lock = threading.Lock()

    def resolve(self, token: str) -> Identity:
        key = hash_token(token)
        with self._lock:
            entry = self._entries.get(key)
        if entry is not None and entry[0] > self.clock():
            if entry[1] is None:
                raise invalid_token()
            return entry[1]

        try:
            identity = self.client.introspect(token)
        except TokenRejected:
            self._remember(key, None, self.negative_ttl)
            raise invalid_token() from None
        self._remember(key, identity, self.ttl)
        return identity

    def forget_all(self) -> None:
        with self._lock:
            self._entries.clear()

    def _remember(self, key: str, identity: Identity | None, ttl: float) -> None:
        now = self.clock()
        with self._lock:
            if len(self._entries) >= self.MAX_ENTRIES:
                self._entries = {k: v for k, v in self._entries.items() if v[0] > now}
            self._entries[key] = (now + ttl, identity)


class RosterThrottle:
    """Decides when a stream's member list is due for another sync with the platform."""

    def __init__(self, ttl: float, clock: Callable[[], float] = time.monotonic) -> None:
        self.ttl = ttl
        self.clock = clock
        self._synced_at: dict[uuid.UUID, float] = {}
        self._lock = threading.Lock()

    def due(self, stream_id: uuid.UUID) -> bool:
        now = self.clock()
        with self._lock:
            last = self._synced_at.get(stream_id)
            if last is not None and now - last < self.ttl:
                return False
            self._synced_at[stream_id] = now
            return True
