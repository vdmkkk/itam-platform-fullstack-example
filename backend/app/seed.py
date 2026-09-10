"""Demo content for a brand-new stream.

This way a student's very first `GET /api/cards` returns a board worth
rendering instead of an empty array. The demo cards also show off the rules:
one is already accepted, one is rejected, and one is a single upvote away
from being accepted.
"""

from __future__ import annotations

import base64
import datetime as dt
import uuid
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app import models
from app.enums import CardType


def svg_data_uri(svg: str) -> str:
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode("utf-8")).decode("ascii")


def initials_avatar(initials: str, color: str) -> str:
    return svg_data_uri(
        '<svg xmlns="http://www.w3.org/2000/svg" width="96" height="96" viewBox="0 0 96 96">'
        f'<rect width="96" height="96" rx="48" fill="{color}"/>'
        '<text x="48" y="48" dy=".35em" text-anchor="middle" '
        'font-family="Arial, Helvetica, sans-serif" font-size="36" font-weight="700" '
        f'fill="#ffffff">{initials}</text></svg>'
    )


def evening_in(now: dt.datetime, days: int) -> int:
    """19:00 Moscow time (16:00 UTC), `days` days from now, as Unix seconds."""
    day = (now + dt.timedelta(days=days)).date()
    return int(dt.datetime.combine(day, dt.time(16), tzinfo=dt.UTC).timestamp())


def banner(emoji: str, start: str, end: str) -> str:
    return svg_data_uri(
        '<svg xmlns="http://www.w3.org/2000/svg" width="640" height="360" viewBox="0 0 640 360">'
        '<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">'
        f'<stop offset="0" stop-color="{start}"/><stop offset="1" stop-color="{end}"/>'
        "</linearGradient></defs>"
        '<rect width="640" height="360" fill="url(#g)"/>'
        f'<text x="320" y="180" dy=".35em" text-anchor="middle" font-size="140">{emoji}</text>'
        "</svg>"
    )


@dataclass(frozen=True)
class DemoPerson:
    key: str
    name: str
    initials: str
    color: str
    status: str
    bio: str


@dataclass(frozen=True)
class DemoCard:
    author: str
    type: CardType
    title: str
    hours_ago: int
    description: str | None = None
    date_in_days: int | None = None
    preview: str | None = None
    # voter key -> +1 / -1
    votes: dict[str, int] = field(default_factory=dict)
    # (author key, text), oldest first
    comments: tuple[tuple[str, str], ...] = ()


PEOPLE = (
    DemoPerson(
        "team", "Команда курса", "КК", "#4f46e5", "Отвечаем на вопросы 👋",
        "Преподаватели и менторы курса. Демо-аккаунт: наполняет доску примерами.",
    ),
    DemoPerson(
        "anya", "Аня Петрова", "АП", "#db2777", "Учу React по вечерам",
        "Демо-аккаунт. Люблю аккуратную вёрстку и котиков.",
    ),
    DemoPerson(
        "misha", "Миша Орлов", "МО", "#0891b2", "Ищу команду на хакатон",
        "Демо-аккаунт. Бэкендер, который решил разобраться во фронтенде.",
    ),
    DemoPerson(
        "liza", "Лиза Смирнова", "ЛС", "#16a34a", "Дизайн → фронтенд",
        "Демо-аккаунт. Рисую интерфейсы в Figma и учусь их верстать.",
    ),
    DemoPerson(
        "dima", "Дима Козлов", "ДК", "#ea580c", "TypeScript enjoyer",
        "Демо-аккаунт. Пишу типы раньше, чем код.",
    ),
    DemoPerson(
        "katya", "Катя Волкова", "КВ", "#7c3aed", "Люблю спорить 🙂",
        "Демо-аккаунт. Задаю неудобные вопросы.",
    ),
)

CARDS = (
    DemoCard(
        author="team",
        type=CardType.event,
        title="Знакомство в Zoom",
        hours_ago=70,
        description=(
            "Первый общий созвон: расскажем, как устроен курс, покажем эту доску и "
            "познакомимся друг с другом. Ссылку пришлём в чат курса."
        ),
        date_in_days=3,
        preview=banner("🎉", "#6366f1", "#ec4899"),
        votes={"anya": 1, "misha": 1, "liza": 1},
        comments=(
            ("anya", "Буду! А запись будет?"),
            ("team", "Да, запись выложим на странице курса."),
        ),
    ),
    DemoCard(
        author="misha",
        type=CardType.event,
        title="Хакатон ITAM: собираю команду",
        hours_ago=60,
        description=(
            "Нужны 2–3 человека во фронтенд. Опыт не важен — важно желание довести проект "
            "до конца. Пишите в комментарии!"
        ),
        date_in_days=20,
        preview=banner("💻", "#0ea5e9", "#22c55e"),
        votes={"anya": 1, "dima": 1},
        comments=(
            ("dima", "Я в деле! Могу взять вёрстку."),
            ("misha", "Супер, записал тебя 🙌"),
        ),
    ),
    DemoCard(
        author="liza",
        type=CardType.idea,
        title="Тёмная тема для доски",
        hours_ago=50,
        description="Вечером глаза устают от белого фона. Давайте добавим переключатель темы в шапку!",
        preview=banner("🌙", "#1e293b", "#6366f1"),
        votes={"team": 1, "anya": 1, "misha": 1, "dima": 1, "katya": 1},
        comments=(
            ("dima", "Поддерживаю, это легко сделать через CSS-переменные."),
            ("team", "Набрала нужное число голосов — карточка переехала в «Принято» ✅"),
        ),
    ),
    DemoCard(
        author="dima",
        type=CardType.idea,
        title="Фильтр карточек по автору",
        hours_ago=40,
        description=(
            "Хочу видеть только свои карточки или карточки конкретного человека. "
            "Можно сделать выпадающий список над доской."
        ),
        votes={"anya": 1, "liza": 1, "katya": -1},
        comments=(
            ("katya", "А зачем? Карточек и так немного."),
            ("dima", "Пока немного — через месяц будет сотня 🙂"),
        ),
    ),
    DemoCard(
        author="katya",
        type=CardType.idea,
        title="Убрать колонки и оставить один список",
        hours_ago=30,
        description="Колонки только отвлекают — пусть всё будет одной лентой, как в соцсетях.",
        votes={"team": -1, "anya": -1, "misha": -1, "liza": -1, "dima": -1},
        comments=(
            ("anya", "Тогда потеряется весь смысл доски 🙂"),
            ("katya", "Ладно-ладно, сдаюсь."),
        ),
    ),
    DemoCard(
        author="anya",
        type=CardType.question,
        title="Чем useEffect отличается от useLayoutEffect?",
        hours_ago=20,
        description="Встретила оба хука в чужом коде и не поняла, какой когда использовать.",
        votes={"misha": 1, "katya": 1},
        comments=(
            (
                "team",
                "Коротко: useLayoutEffect срабатывает синхронно, до того как браузер нарисует "
                "кадр, а useEffect — после. Почти всегда нужен useEffect. Подробно разберём на "
                "занятии про хуки.",
            ),
        ),
    ),
    DemoCard(
        author="misha",
        type=CardType.question,
        title="Где взять свой токен для API?",
        hours_ago=10,
        votes={"anya": 1, "liza": 1, "dima": 1, "katya": 1},
        comments=(
            (
                "team",
                "На странице курса, во вкладке «API проекта». Передавайте его в заголовке "
                "X-Course-Token в каждом запросе.",
            ),
        ),
    ),
    DemoCard(
        author="katya",
        type=CardType.question,
        title="Можно ли голосовать за свои карточки?",
        hours_ago=6,
        description="Хочу поднять свою идею повыше 😅",
        comments=(
            ("team", "Нет: сервер ответит 403. За карточку голосуют только другие участники."),
        ),
    ),
)


def seed_stream(db: Session, stream_id: uuid.UUID, now: dt.datetime | None = None) -> None:
    """Fill a new stream with demo people, cards, votes and comments (no commit)."""
    now = now or dt.datetime.now(dt.UTC)
    joined_at = now - dt.timedelta(days=3)

    people: dict[str, models.User] = {}
    for person in PEOPLE:
        user = models.User(
            id=uuid.uuid4(),
            stream_id=stream_id,
            platform_user_id=None,
            is_demo=True,
            name=person.name,
            avatar_url=initials_avatar(person.initials, person.color),
            status=person.status,
            bio=person.bio,
            created_at=joined_at,
            updated_at=joined_at,
        )
        db.add(user)
        people[person.key] = user
    db.flush()

    for demo in CARDS:
        created_at = now - dt.timedelta(hours=demo.hours_ago)
        card = models.Card(
            id=uuid.uuid4(),
            stream_id=stream_id,
            author_id=people[demo.author].id,
            title=demo.title,
            type=demo.type,
            description=demo.description,
            preview=demo.preview,
            date=evening_in(now, demo.date_in_days) if demo.date_in_days is not None else None,
            created_at=created_at,
            updated_at=created_at,
        )
        db.add(card)
        db.flush()

        voted_at = created_at + dt.timedelta(minutes=30)
        for voter, value in demo.votes.items():
            db.add(
                models.Vote(
                    card_id=card.id,
                    user_id=people[voter].id,
                    stream_id=stream_id,
                    value=value,
                    created_at=voted_at,
                    updated_at=voted_at,
                )
            )
        for index, (author, text) in enumerate(demo.comments):
            commented_at = created_at + dt.timedelta(hours=index + 1)
            db.add(
                models.Comment(
                    id=uuid.uuid4(),
                    stream_id=stream_id,
                    card_id=card.id,
                    author_id=people[author].id,
                    text=text,
                    created_at=commented_at,
                    updated_at=commented_at,
                )
            )
        db.flush()
