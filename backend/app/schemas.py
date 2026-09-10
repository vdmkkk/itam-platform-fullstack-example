"""Request and response bodies.

Every field is documented. Students read these descriptions in Swagger, and
codegen turns them into comments on their TypeScript types, so the texts
(class docstrings included) are in Russian.

Conventions:

- Response models have no defaults, so every field is *required* in the
  schema. It is always present in the JSON, possibly as `null`.
- Update models give non-nullable fields `Field(default=None)`. Such a field
  may be omitted, but an explicit `null` is rejected.
"""

from __future__ import annotations

import datetime as dt
import re
import uuid
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
from pydantic_core import PydanticCustomError

from app.enums import CardColumn, CardType, VoteValue

PREVIEW_MAX_LENGTH = 300_000
AVATAR_MAX_LENGTH = 150_000
IMAGE_PREFIXES = ("http://", "https://", "data:image/")
TELEGRAM_RE = re.compile(r"^[A-Za-z0-9_]{5,32}$")

# Card dates are Unix time in seconds, from 1970-01-01 to 2099-12-31 (UTC).
UNIX_TIME_MAX = 4_102_444_799

EXAMPLE_UUID = "3f8e9c1a-5b2d-4e7f-9a61-2c4b8d0e1f23"
EXAMPLE_TIME = "2026-09-10T12:00:00Z"
EXAMPLE_UNIX_TIME = 1_791_648_000  # 2026-10-10 19:00 Moscow time


def _thousands(value: int) -> str:
    """300000 -> '300 000'."""
    return f"{value:_}".replace("_", " ")


def _no_default(schema: dict[str, Any]) -> None:
    """Hide `default: null` for fields that may be omitted but can't be null."""
    schema.pop("default", None)


def _empty_to_none(value: str | None) -> str | None:
    return value or None


def _check_image(value: str | None) -> str | None:
    if not value:
        return None
    if not value.startswith(IMAGE_PREFIXES):
        raise PydanticCustomError(
            "image_string",
            "Нужна ссылка на картинку (http:// или https://) или data:image/... URI",
        )
    return value


def _check_telegram(value: str | None) -> str | None:
    if not value:
        return None
    username = value.removeprefix("@")
    if not TELEGRAM_RE.fullmatch(username):
        raise PydanticCustomError(
            "telegram",
            "Имя пользователя в Telegram — 5-32 латинских буквы, цифры или подчёркивания "
            "(@ в начале необязателен)",
        )
    return username


def _check_unix_time(value: Any) -> Any:
    """Catch the usual Unix time mistakes before the int check, with a hint for each."""
    if isinstance(value, str) and not value.strip():
        return None
    if isinstance(value, (str, bool)):
        raise PydanticCustomError(
            "unix_time_type", f"Нужно число: Unix-время в секундах, например {EXAMPLE_UNIX_TIME}"
        )
    if isinstance(value, (int, float)):
        if UNIX_TIME_MAX < value <= UNIX_TIME_MAX * 1000:
            raise PydanticCustomError(
                "unix_time_milliseconds",
                "Похоже, это миллисекунды, а нужны секунды: Math.floor(ms / 1000)",
            )
        if isinstance(value, float) and not value.is_integer():
            raise PydanticCustomError(
                "unix_time_fraction", "Нужно целое число секунд: Math.floor(Date.now() / 1000)"
            )
        if not 0 <= value <= UNIX_TIME_MAX:
            raise PydanticCustomError("unix_time_range", "Дата должна быть между 1970 и 2099 годом")
    return value


class RequestBody(BaseModel):
    """Base for request bodies: trims strings and rejects unknown (misspelled) fields."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class ErrorResponse(BaseModel):
    """Так выглядит любой ответ с ошибкой."""

    detail: str = Field(
        description="Что пошло не так — предложение, которое можно показать человеку.",
        examples=["Карточка не найдена. Возможно, её удалили."],
    )


class FieldError(BaseModel):
    """Проблема с одним конкретным полем."""

    field: str = Field(
        description=(
            "К чему относится проблема: к полю тела запроса (`title`, `email`; вложенные поля "
            "пишутся через точку, например `items.0.name`), к query- или path-параметру или к "
            "телу запроса целиком (`body`)."
        ),
        examples=["title"],
    )
    message: str = Field(
        description="Что не так. Покажите это рядом с соответствующим полем формы.",
        examples=["Обязательное поле"],
    )


class ValidationErrorResponse(BaseModel):
    """Приходит с 422 (некорректные данные) и некоторыми 409 (например, когда email уже занят).

    `detail` собирает все проблемы в одно предложение, а `errors` перечисляет
    их по одной, чтобы форма могла подсветить нужные поля.
    """

    detail: str = Field(
        description="Все проблемы одним читаемым предложением.",
        examples=["title: Обязательное поле; type: Допустимые значения: 'event', 'idea', 'question'"],
    )
    errors: list[FieldError] = Field(description="Те же проблемы, по одной на поле.")


# ---------------------------------------------------------------------------
# People
# ---------------------------------------------------------------------------


class Stream(BaseModel):
    """Поток курса, в котором вы учитесь."""

    id: uuid.UUID | None = Field(
        description="Id потока на платформе курса. `null`, если вы записаны на курс без потока.",
        examples=["7c2a41e0-93d4-4b8e-8f0c-5a1d2e3f4b5c"],
    )
    code: str | None = Field(description="Короткий код потока.", examples=["26F"])
    title: str | None = Field(
        description="Название от команды курса. Часто `null`, поэтому для показа берите `name`.",
        examples=["Осенний поток 2026"],
    )
    name: str = Field(
        description="Готовое для показа название: `title`, а если его нет — `code`.",
        examples=["Осенний поток 2026"],
    )


class User(BaseModel):
    """Участник, каким его видят остальные.

    Используется как автор карточек и комментариев и в списке участников.
    Email — личные данные: он есть только в вашем собственном `Profile`.
    """

    id: uuid.UUID = Field(
        description=(
            "Id пользователя в этом API. Используйте его в `GET /api/users/{user_id}` и "
            "`GET /api/cards?author_id=...`."
        ),
        examples=[EXAMPLE_UUID],
    )
    name: str = Field(description="Отображаемое имя.", examples=["Аня Петрова"])
    avatar_url: str | None = Field(
        description=(
            "Аватар в виде строки, которую можно сразу подставить в `<img src>`: ссылка http(s) "
            "или `data:image/...` URI. `null` — аватара нет, покажите инициалы."
        ),
        examples=["https://courses.salut.uno/api/v1/media/avatars/anya.png"],
    )
    status: str | None = Field(
        description="Короткий статус, как в мессенджере.", examples=["Ищу команду на хакатон"]
    )
    bio: str | None = Field(description="Пара слов о себе.", examples=["Учу React по вечерам."])
    telegram: str | None = Field(
        description="Имя пользователя в Telegram без `@`.", examples=["anya_codes"]
    )
    is_demo: bool = Field(
        description=(
            "`true` у демо-пользователей, которые наполняют каждую новую доску примерами. Это не "
            "настоящие однокурсники."
        ),
        examples=[False],
    )
    is_me: bool = Field(description="`true`, если это вы.", examples=[False])
    created_at: dt.datetime = Field(
        description="Когда пользователь впервые появился в этом API (ISO-8601, UTC).",
        examples=[EXAMPLE_TIME],
    )


class UserDetail(User):
    """Участник со счётчиками активности."""

    cards_count: int = Field(description="Сколько карточек опубликовал.", examples=[4])
    comments_count: int = Field(description="Сколько комментариев написал.", examples=[11])
    total_score: int = Field(description="Сумма счёта всех его карточек.", examples=[7])


class Profile(BaseModel):
    """Ваш профиль.

    Изначально в нём имя, email и аватар с платформы курса. Дальше он
    принадлежит вам: изменения здесь не затрагивают платформу, а изменения на
    платформе не перезаписывают его.
    """

    id: uuid.UUID = Field(description="Ваш id в этом API.", examples=[EXAMPLE_UUID])
    name: str = Field(description="Отображаемое имя.", examples=["Аня Петрова"])
    email: str | None = Field(
        description="Ваш email. Его видите только вы. Он не должен совпадать с email другого участника.",
        examples=["anya@example.com"],
    )
    avatar_url: str | None = Field(
        description="Аватар: ссылка на картинку http(s) или `data:image/...` URI.",
        examples=["https://courses.salut.uno/api/v1/media/avatars/anya.png"],
    )
    status: str | None = Field(description="Короткий статус.", examples=["Ищу команду на хакатон"])
    bio: str | None = Field(description="О себе.", examples=["Учу React по вечерам."])
    telegram: str | None = Field(description="Имя пользователя в Telegram без `@`.", examples=["anya_codes"])
    stream: Stream = Field(description="Поток, в котором вы учитесь.")
    created_at: dt.datetime = Field(
        description="Когда вы впервые обратились к этому API (ISO-8601, UTC).", examples=[EXAMPLE_TIME]
    )
    updated_at: dt.datetime = Field(
        description="Когда профиль последний раз меняли (ISO-8601, UTC).", examples=[EXAMPLE_TIME]
    )


class ProfileUpdate(RequestBody):
    """Изменение профиля. Отправляйте только поля, которые хотите поменять.

    - Пропущенные поля остаются как есть.
    - `null` (или пустая строка) очищает необязательное поле.
    - `name` можно изменить, но нельзя очистить.
    """

    name: str = Field(
        default=None,
        min_length=1,
        max_length=80,
        description="Отображаемое имя, 1-80 символов.",
        examples=["Аня Петрова"],
        json_schema_extra=_no_default,
    )
    email: EmailStr | None = Field(
        default=None,
        description=(
            "Корректный email, не занятый другим участником. Если он уже занят, придёт 409 "
            "`Этот email уже занят`."
        ),
        examples=["anya@example.com"],
    )
    avatar_url: str | None = Field(
        default=None,
        max_length=AVATAR_MAX_LENGTH,
        description=(
            f"Ссылка на картинку http(s) или `data:image/...;base64,...` URI, до "
            f"{_thousands(AVATAR_MAX_LENGTH)} символов. Аватар показывается на каждой вашей "
            "карточке и в каждом комментарии, так что пусть он будет небольшим."
        ),
        examples=["https://i.pravatar.cc/150?img=5"],
    )
    status: str | None = Field(
        default=None, max_length=100, description="Короткий статус, до 100 символов.",
        examples=["Ищу команду на хакатон"],
    )
    bio: str | None = Field(
        default=None, max_length=1000, description="О себе, до 1000 символов.",
        examples=["Учу React по вечерам."],
    )
    telegram: str | None = Field(
        default=None,
        max_length=33,
        description=(
            "Имя пользователя в Telegram: 5-32 латинских буквы, цифры или подчёркивания. `@` в "
            "начале необязателен и отбрасывается."
        ),
        examples=["@anya_codes"],
    )

    _empty_texts = field_validator("status", "bio")(_empty_to_none)
    _avatar = field_validator("avatar_url")(_check_image)
    _telegram = field_validator("telegram")(_check_telegram)

    @field_validator("email", mode="before")
    @classmethod
    def _empty_email(cls, value: Any) -> Any:
        return None if isinstance(value, str) and not value.strip() else value


# ---------------------------------------------------------------------------
# Comments
# ---------------------------------------------------------------------------


class Comment(BaseModel):
    """Комментарий к карточке. Комментарии плоские: ответить на комментарий нельзя."""

    id: uuid.UUID = Field(description="Id комментария.", examples=[EXAMPLE_UUID])
    card_id: uuid.UUID = Field(description="Карточка, к которой он относится.", examples=[EXAMPLE_UUID])
    text: str = Field(description="Текст комментария.", examples=["Буду! А запись будет?"])
    author: User = Field(description="Кто написал.")
    is_mine: bool = Field(
        description="`true`, если его написали вы, — значит, вы можете его изменить или удалить.",
        examples=[False],
    )
    created_at: dt.datetime = Field(description="Когда опубликован (ISO-8601, UTC).", examples=[EXAMPLE_TIME])
    updated_at: dt.datetime = Field(
        description=(
            "Когда последний раз изменён (ISO-8601, UTC). Равен `created_at`, если комментарий "
            "не редактировали."
        ),
        examples=[EXAMPLE_TIME],
    )


class CommentCreate(RequestBody):
    """Новый комментарий."""

    text: str = Field(
        min_length=1, max_length=2000, description="Текст комментария, 1-2000 символов.",
        examples=["Классная идея, я за!"],
    )


class CommentUpdate(RequestBody):
    """Новый текст вашего комментария."""

    text: str = Field(
        min_length=1, max_length=2000, description="Текст комментария, 1-2000 символов.",
        examples=["Классная идея, я за! (upd: уже проголосовал)"],
    )


# ---------------------------------------------------------------------------
# Cards
# ---------------------------------------------------------------------------

_PREVIEW_DESCRIPTION = (
    "Картинка для карточки в виде строки: ссылка на изображение `https://...` или "
    "`data:image/...;base64,...` URI (например, из `FileReader.readAsDataURL`). "
    f"До {_thousands(PREVIEW_MAX_LENGTH)} символов, так что для больших картинок используйте "
    "ссылки. Пустая строка считается `null`."
)

_DATE_DESCRIPTION = (
    "Необязательная дата: **Unix-время в секундах** (целое число, UTC). Удобно для событий. "
    "Из `<input type=\"datetime-local\">` или `<input type=\"date\">`: "
    "`Math.floor(new Date(input.value).getTime() / 1000)`. Миллисекунды (`Date.now()`, "
    "`getTime()`) не подойдут: сначала разделите их на 1000. Пустая строка считается `null`."
)


class Card(BaseModel):
    """Карточка на доске со всем, что нужно для отрисовки.

    **В какой колонке?** Смотрите на `column`:

    - `accepted`, когда `score >= accept_threshold`;
    - `rejected`, когда `score <= -reject_threshold`;
    - иначе — `type` карточки (`event`, `idea` или `question`).

    Это считается заново при каждом запросе: если голоса изменятся, карточка переедет.
    """

    id: uuid.UUID = Field(description="Id карточки.", examples=[EXAMPLE_UUID])
    title: str = Field(description="Заголовок карточки.", examples=["Тёмная тема для доски"])
    type: CardType = Field(
        description=(
            "Тип карточки, который выбрал автор. Не меняется, когда карточку принимают или "
            "отклоняют."
        ),
        examples=[CardType.idea],
    )
    description: str | None = Field(
        description="Подробный текст или `null`.",
        examples=["Вечером глаза устают от белого фона. Давайте добавим переключатель темы!"],
    )
    preview: str | None = Field(
        description="Картинка, которую можно сразу подставить в `<img src>`, или `null`.",
        examples=["https://picsum.photos/seed/itam/640/360"],
    )
    date: int | None = Field(
        description=(
            "Дата карточки: Unix-время в секундах (UTC) или `null`. Для показа: "
            "`new Date(card.date * 1000).toLocaleString(\"ru-RU\")`."
        ),
        examples=[EXAMPLE_UNIX_TIME],
    )
    column: CardColumn = Field(
        description="Колонка, в которой рисовать карточку (правила выше).",
        examples=[CardColumn.accepted],
    )
    is_accepted: bool = Field(
        description="`true`, когда счёт достиг порога принятия.", examples=[True]
    )
    is_rejected: bool = Field(
        description="`true`, когда счёт опустился до минус порога отклонения.", examples=[False]
    )
    upvotes: int = Field(description="Сколько человек проголосовали `up`.", examples=[6])
    downvotes: int = Field(description="Сколько человек проголосовали `down`.", examples=[1])
    votes_count: int = Field(description="Всего голосов: `upvotes + downvotes`.", examples=[7])
    score: int = Field(description="Счёт: `upvotes - downvotes`.", examples=[5])
    votes_to_accept: int = Field(
        description=(
            "Сколько ещё голосов «за» (с учётом голосов «против») нужно для принятия: "
            "`max(0, accept_threshold - score)`. `0`, когда карточка принята."
        ),
        examples=[0],
    )
    votes_to_reject: int = Field(
        description=(
            "Сколько ещё голосов «против» (с учётом голосов «за») приведут к отклонению: "
            "`max(0, score + reject_threshold)`. `0`, когда карточка отклонена."
        ),
        examples=[10],
    )
    comments_count: int = Field(description="Сколько у неё комментариев.", examples=[2])
    my_vote: VoteValue | None = Field(
        description=(
            "Как проголосовали *вы*: `up`, `down` или `null`, если не голосовали. На ваших "
            "карточках всегда `null`: за них голосовать нельзя."
        ),
        examples=[VoteValue.up],
    )
    is_mine: bool = Field(
        description=(
            "`true`, если автор — вы. Изменять и удалять карточку может только автор, и никто не "
            "может голосовать за свои карточки."
        ),
        examples=[False],
    )
    author: User = Field(description="Кто опубликовал карточку.")
    created_at: dt.datetime = Field(description="Когда опубликована (ISO-8601, UTC).", examples=[EXAMPLE_TIME])
    updated_at: dt.datetime = Field(
        description=(
            "Когда последний раз меняли её содержимое (ISO-8601, UTC). Голоса и комментарии его "
            "не меняют."
        ),
        examples=[EXAMPLE_TIME],
    )


class CardDetail(Card):
    """Карточка с комментариями: все поля `Card` плюс `comments`."""

    comments: list[Comment] = Field(description="Все комментарии, от старых к новым.")


class CardCreate(RequestBody):
    """Новая карточка. Обязательны только `title` и `type`."""

    title: str = Field(
        min_length=1,
        max_length=120,
        description="Заголовок, 1-120 символов. Пробелы в начале и в конце обрезаются.",
        examples=["Сходить на хакатон ITAM"],
    )
    type: CardType = Field(
        description=(
            "В какой колонке карточка появится: `event`, `idea` или `question`. Создать карточку "
            "сразу в `accepted` или `rejected` нельзя: туда её переносят только голоса."
        ),
        examples=[CardType.idea],
    )
    description: str | None = Field(
        default=None,
        max_length=5000,
        description="Подробный текст, до 5000 символов. Пустая строка считается `null`.",
        examples=["Собираем команду из 3-4 человек, опыт не важен."],
    )
    preview: str | None = Field(
        default=None, max_length=PREVIEW_MAX_LENGTH, description=_PREVIEW_DESCRIPTION,
        examples=["https://picsum.photos/seed/itam/640/360"],
    )
    date: int | None = Field(
        default=None, ge=0, le=UNIX_TIME_MAX, description=_DATE_DESCRIPTION,
        examples=[EXAMPLE_UNIX_TIME],
    )

    _empty_description = field_validator("description")(_empty_to_none)
    _preview = field_validator("preview")(_check_image)
    _date = field_validator("date", mode="before")(_check_unix_time)


class CardUpdate(RequestBody):
    """Изменение вашей карточки. Отправляйте только поля, которые хотите поменять.

    - Пропущенные поля остаются как есть.
    - `null` очищает `description`, `preview` или `date`.
    - `title` и `type` можно изменить, но нельзя очистить.

    Смена `type` переносит карточку между колонками `event`, `idea` и
    `question`. На голоса это не влияет, так что принятая карточка остаётся
    принятой.
    """

    title: str = Field(
        default=None,
        min_length=1,
        max_length=120,
        description="Заголовок, 1-120 символов.",
        examples=["Сходить на хакатон ITAM всей командой"],
        json_schema_extra=_no_default,
    )
    type: CardType = Field(
        default=None,
        description="Новый тип: `event`, `idea` или `question`.",
        examples=[CardType.event],
        json_schema_extra=_no_default,
    )
    description: str | None = Field(
        default=None, max_length=5000,
        description="Подробный текст, до 5000 символов, или `null`, чтобы его очистить.",
    )
    preview: str | None = Field(
        default=None, max_length=PREVIEW_MAX_LENGTH, description=_PREVIEW_DESCRIPTION
    )
    date: int | None = Field(
        default=None, ge=0, le=UNIX_TIME_MAX, description=_DATE_DESCRIPTION,
        examples=[EXAMPLE_UNIX_TIME],
    )

    _empty_description = field_validator("description")(_empty_to_none)
    _preview = field_validator("preview")(_check_image)
    _date = field_validator("date", mode="before")(_check_unix_time)


class VoteRequest(RequestBody):
    """Ваш голос. Если отправить его ещё раз с другим значением, голос поменяется."""

    value: VoteValue = Field(description="`up` или `down`.", examples=[VoteValue.up])


# ---------------------------------------------------------------------------
# Board
# ---------------------------------------------------------------------------


class BoardColumn(BaseModel):
    """Одна колонка доски."""

    id: CardColumn = Field(
        description="Id колонки — то же значение, что в `Card.column`.", examples=[CardColumn.idea]
    )
    title: str = Field(description="Название для показа.", examples=["Идеи"])
    description: str = Field(
        description="Что попадает в эту колонку.",
        examples=["Предложения, за которые голосуют участники."],
    )
    cards_count: int = Field(description="Сколько карточек в ней прямо сейчас.", examples=[3])


class Board(BaseModel):
    """Доска целиком: колонки, пороги голосования и ваш поток."""

    stream: Stream = Field(description="Поток, которому принадлежит доска (ваш).")
    accept_threshold: int = Field(
        description="Карточка принята, когда `score >= accept_threshold`.", examples=[5]
    )
    reject_threshold: int = Field(
        description="Карточка отклонена, когда `score <= -reject_threshold`.", examples=[5]
    )
    columns: list[BoardColumn] = Field(
        description="Все пять колонок в порядке отображения: event, idea, question, accepted, rejected."
    )
    cards_count: int = Field(description="Всего карточек на доске.", examples=[8])
    members_count: int = Field(
        description="Сколько реальных участников знает этот API (без демо-пользователей).",
        examples=[17],
    )


# ---------------------------------------------------------------------------
# Admin and system
# ---------------------------------------------------------------------------


class BoardSettings(BaseModel):
    """Пороги голосования, общие для всех потоков."""

    accept_threshold: int = Field(description="`score >= accept_threshold` — карточка принята.", examples=[5])
    reject_threshold: int = Field(description="`score <= -reject_threshold` — карточка отклонена.", examples=[5])
    updated_at: dt.datetime = Field(description="Когда их последний раз меняли.", examples=[EXAMPLE_TIME])


class BoardSettingsUpdate(RequestBody):
    """Новые пороги. Отправьте один или оба. Они сразу применяются ко всем карточкам во всех потоках."""

    accept_threshold: int = Field(
        default=None, ge=1, le=1000, description="Целое положительное число.", examples=[3],
        json_schema_extra=_no_default,
    )
    reject_threshold: int = Field(
        default=None, ge=1, le=1000, description="Целое положительное число.", examples=[3],
        json_schema_extra=_no_default,
    )


class AdminStream(BaseModel):
    """Поток, который обращался к этому API, со счётчиками активности."""

    id: uuid.UUID | None = Field(description="Id потока на платформе или `null` для студентов без потока.")
    code: str | None = Field(description="Код потока.", examples=["26F"])
    title: str | None = Field(description="Название потока.", examples=["Осенний поток 2026"])
    name: str = Field(description="`title` или `code`.", examples=["Осенний поток 2026"])
    members_count: int = Field(description="Реальные люди (без демо-пользователей).", examples=[17])
    cards_count: int = Field(description="Карточки, включая демо.", examples=[42])
    comments_count: int = Field(description="Комментарии.", examples=[120])
    votes_count: int = Field(description="Голоса.", examples=[300])
    first_seen_at: dt.datetime = Field(description="Когда появился первый студент потока.")


class Health(BaseModel):
    """Состояние сервиса."""

    status: str = Field(description="`ok`, когда API и его база данных работают.", examples=["ok"])
