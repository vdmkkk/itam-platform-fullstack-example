"""Test fixtures: a real Postgres database and a fake course platform.

Point TEST_DATABASE_URL at a disposable database whose name contains "test".
Every run wipes it.
"""

from __future__ import annotations

import json
import os
import uuid
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path

import httpx
import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from app.config import Settings
from app.main import create_app

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+psycopg://postgres:postgres@localhost:55432/board_test"
)
BACKEND_DIR = Path(__file__).resolve().parents[1]
SLUG = "frontend-itam"
SERVICE_KEY = "exbk_test_service_key"
ADMIN_TOKEN = "admin-test-token"
ADMIN_HEADERS = {"X-Admin-Token": ADMIN_TOKEN}

STREAM_A = uuid.UUID("aaaaaaaa-0000-4000-8000-000000000001")
STREAM_B = uuid.UUID("bbbbbbbb-0000-4000-8000-000000000002")


@dataclass
class Student:
    name: str
    token: str
    user_id: uuid.UUID
    email: str
    display_name: str
    stream_id: uuid.UUID | None
    stream_code: str | None
    avatar_url: str | None

    @property
    def headers(self) -> dict[str, str]:
        return {"X-Course-Token": self.token}

    def user_json(self) -> dict[str, object]:
        first, _, last = self.display_name.partition(" ")
        return {
            "id": str(self.user_id),
            "email": self.email,
            "display_name": self.display_name,
            "name": first,
            "surname": last or None,
            "avatar_url": self.avatar_url,
        }


class FakePlatform:
    """Stands in for the course platform's service API (introspection and rosters)."""

    def __init__(self) -> None:
        self.students: dict[str, Student] = {}
        self.service_key = SERVICE_KEY
        self.down = False
        self.raise_error: Exception | None = None
        self.introspect_calls = 0

    def add(self, name: str, stream_id: uuid.UUID | None, code: str | None = None) -> Student:
        student = Student(
            name=name,
            token=f"exb_{name}_{uuid.uuid4().hex}",
            user_id=uuid.uuid4(),
            email=f"{name}@example.com",
            display_name=f"{name.capitalize()} Student",
            stream_id=stream_id,
            stream_code=code,
            avatar_url=f"https://example.com/avatars/{name}.png",
        )
        self.students[student.token] = student
        return student

    def revoke(self, student: Student) -> None:
        self.students.pop(student.token, None)

    def handler(self, request: httpx.Request) -> httpx.Response:
        if self.raise_error is not None:
            raise self.raise_error
        if self.down:
            return httpx.Response(502, text="Bad Gateway")
        if request.headers.get("Authorization") != f"Bearer {self.service_key}":
            return httpx.Response(401, json={"detail": "Invalid example backend service key"})

        prefix = f"/api/v1/example-backends/{SLUG}"
        path = request.url.path
        if request.method == "POST" and path == f"{prefix}/introspect":
            self.introspect_calls += 1
            student = self.students.get(json.loads(request.content)["token"])
            if student is None:
                return httpx.Response(404, json={"detail": "Unknown or inactive student token"})
            stream = {
                "id": str(student.stream_id) if student.stream_id else None,
                "code": student.stream_code,
                "title": None,
                "starts_on": None,
                "ends_on": None,
            }
            return httpx.Response(
                200,
                json={
                    "user": student.user_json(),
                    "stream": stream,
                    "course_id": str(uuid.uuid4()),
                    "course_slug": SLUG,
                    "course_title": "Frontend (ITAM)",
                    "backend_slug": SLUG,
                },
            )
        if request.method == "GET" and path.startswith(f"{prefix}/streams/") and path.endswith("/members"):
            stream_id = path.split("/")[-2]
            members = [s for s in self.students.values() if str(s.stream_id) == stream_id]
            return httpx.Response(
                200,
                json={
                    "stream": {"id": stream_id, "code": None, "title": None},
                    "members": [member.user_json() for member in members],
                },
            )
        return httpx.Response(404, json={"detail": "Not Found"})


class FakeClock:
    def __init__(self) -> None:
        self.now = 1_000.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


@pytest.fixture(scope="session")
def database_url() -> str:
    url = make_url(TEST_DATABASE_URL)
    if "test" not in (url.database or ""):
        raise RuntimeError(f"Refusing to wipe {url.database!r}: the test database name must contain 'test'.")

    engine = create_engine(TEST_DATABASE_URL)
    with engine.begin() as connection:
        connection.execute(text("DROP SCHEMA public CASCADE"))
        connection.execute(text("CREATE SCHEMA public"))
    engine.dispose()

    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    config.set_main_option("sqlalchemy.url", TEST_DATABASE_URL.replace("%", "%%"))
    command.upgrade(config, "head")
    return TEST_DATABASE_URL


@pytest.fixture(autouse=True)
def clean_tables(database_url: str) -> None:
    engine = create_engine(database_url)
    with engine.begin() as connection:
        connection.execute(text("TRUNCATE streams, users, cards, votes, comments, board_settings CASCADE"))
    engine.dispose()


@pytest.fixture
def platform() -> FakePlatform:
    return FakePlatform()


def make_settings(database_url: str, **overrides: object) -> Settings:
    values: dict[str, object] = {
        "_env_file": None,
        "database_url": database_url,
        "platform_api_url": "http://platform.test",
        "platform_service_key": SERVICE_KEY,
        "backend_slug": SLUG,
        "admin_token": ADMIN_TOKEN,
        "rate_limit_per_second": 1000,
        "rate_limit_burst": 1000,
    }
    values.update(overrides)
    return Settings(**values)  # type: ignore[arg-type]


@pytest.fixture
def make_client(database_url: str, platform: FakePlatform) -> Iterator[Callable[..., TestClient]]:
    clients: list[TestClient] = []

    def factory(**overrides: object) -> TestClient:
        app = create_app(
            make_settings(database_url, **overrides),
            platform_transport=httpx.MockTransport(platform.handler),
        )
        client = TestClient(app)
        client.__enter__()
        clients.append(client)
        return client

    yield factory
    for client in clients:
        client.__exit__(None, None, None)


@pytest.fixture
def client(make_client: Callable[..., TestClient]) -> TestClient:
    return make_client()


@pytest.fixture
def alice(platform: FakePlatform) -> Student:
    return platform.add("alice", STREAM_A, code="26F")


@pytest.fixture
def bob(platform: FakePlatform) -> Student:
    return platform.add("bob", STREAM_A, code="26F")


@pytest.fixture
def carol(platform: FakePlatform) -> Student:
    return platform.add("carol", STREAM_B, code="27S")


@pytest.fixture
def nora(platform: FakePlatform) -> Student:
    """A student enrolled without a stream."""
    return platform.add("nora", None)
