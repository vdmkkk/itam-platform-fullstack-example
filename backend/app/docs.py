"""Texts for the OpenAPI document: the Swagger intro, tag descriptions and shared error docs.

Students use Swagger as their main reference, so these texts are part of the
product, not an afterthought. They are in Russian, like the course. Error
examples reuse the messages the API really sends, so the docs can't drift
from the responses.
"""

from __future__ import annotations

from typing import Any

from app.config import Settings
from app.deps import ADMIN_DISABLED, ADMIN_MISSING, ADMIN_WRONG
from app.errors import BODY_NOT_JSON, REQUIRED
from app.identity import MISSING_TOKEN, invalid_token, platform_unavailable
from app.ratelimit import rate_limit_detail
from app.schemas import ErrorResponse, ValidationErrorResponse

EMAIL_TAKEN = "Этот email уже занят"
EMAIL_TAKEN_DETAIL = "Этот email уже занят другим участником."

INTRO = """
**ITAM Board** — небольшой API в духе Trello для курса *Frontend (ITAM)*. Это общая доска
**событий**, **идей** и **вопросов** для всех, кто учится вместе с вами: вы публикуете карточки,
голосуете за чужие и обсуждаете их в комментариях. За время курса вы напишете для неё фронтенд
на React.

## 1. Авторизация (30 секунд)

Логина **нет**. Каждый запрос несёт ваш личный токен курса в одном заголовке:

```
X-Course-Token: exb_xxxxxxxxxxxxxxxxxxxxxxxx
```

1. Откройте страницу курса, вкладку **«API проекта»**, и скопируйте токен.
2. Нажмите кнопку **Authorize** на этой странице, вставьте токен в поле `CourseToken` и нажмите
   *Authorize*.
3. Откройте любой эндпоинт и нажмите **Execute**. Для начала подойдут `GET /api/me` и
   `GET /api/cards`.

Swagger запомнит токен в этом браузере, так что сделать это нужно всего один раз.

## 2. Как устроена доска

| Колонка | Карточка здесь, когда… |
| --- | --- |
| `event` | её `type` — `"event"`, а голоса ещё ничего не решили |
| `idea` | её `type` — `"idea"`, а голоса ещё ничего не решили |
| `question` | её `type` — `"question"`, а голоса ещё ничего не решили |
| `accepted` | `score >= accept_threshold`, какой бы ни был тип |
| `rejected` | `score <= -reject_threshold`, какой бы ни был тип |

* Карточку может создать каждый — в одной из первых трёх колонок (`type`: `event`, `idea` или
  `question`). Автор может поменять тип в любой момент.
* `score = upvotes - downvotes`. Пороги задаёт команда курса, узнать их можно в `GET /api/board`.
* Принятая или отклонённая карточка **сохраняет свой `type`**. `is_accepted` и `is_rejected` —
  отдельные флаги, а `column` говорит, в какой колонке рисовать карточку.
* Всё считается на лету: если голоса изменятся, карточка вернётся на место.

## 3. Правила

* Голосовать и комментировать можно любые карточки, но **за свою карточку голосовать нельзя**
  (будет 403).
* Изменить или удалить карточку или комментарий может только автор.
* В профиле сначала стоят ваши имя, email и аватар с платформы курса. Изменения здесь на
  платформу не влияют.

## 4. Соглашения

* JSON с полями в `snake_case`. Id — строки UUID.
* Все даты и время — **числа**: Unix-время в секундах (UTC). Это `date` карточки и все
  `created_at` / `updated_at`. Показать: `new Date(card.created_at * 1000)`. Отправить `date`:
  `Math.floor(date.getTime() / 1000)`.
* Списки — обычные JSON-массивы, без пагинации и объектов-обёрток.
* Ошибка всегда выглядит как `{"detail": "Понятное человеку предложение"}`. В ошибках
  валидации (422) есть ещё `errors: [{"field": "...", "message": "..."}]`, чтобы показать каждое
  сообщение рядом с нужным полем формы.

| Код | Что значит |
| --- | --- |
| `200` | OK |
| `201` | Создано: в теле — новый объект |
| `204` | Готово, тело **пустое**, так что не вызывайте `response.json()` |
| `401` | Токена нет или он недействителен |
| `403` | Так нельзя, например изменить чужую карточку |
| `404` | Не найдено |
| `409` | Конфликт, например email уже занят |
| `422` | Некорректные данные, подробности в `errors` |
| `429` | Слишком много запросов. Лимит — __RATE__ в секунду на токен, и `useEffect` без массива зависимостей быстро в него упрётся |
| `503` | Платформа курса временно недоступна, поэтому токен не проверить. Повторите запрос позже |

## 5. Типы для TypeScript

Машиночитаемая схема лежит здесь: [`__BASE__/openapi.json`](__BASE__/openapi.json).
Сгенерируйте из неё типы:

```sh
npx openapi-typescript __BASE__/openapi.json -o src/shared/api/schema.d.ts
```

Удобнее другой вид? Та же документация есть в [`/redoc`](__BASE__/redoc).
"""


def api_description(settings: Settings) -> str:
    return (
        INTRO.replace("__BASE__", settings.docs_base_url)
        .replace("__RATE__", f"{settings.rate_limit_per_second:g}")
        .strip()
    )


# Tag names stay English: codegen tools turn them into class and file names.
TAGS: list[dict[str, Any]] = [
    {
        "name": "Board",
        "description": "Доска целиком: колонки и пороги голосования. Хороший первый запрос.",
    },
    {
        "name": "Cards",
        "description": "Создание, просмотр, изменение и удаление карточек. `GET /api/cards` за "
        "один запрос отдаёт всё, что нужно для отрисовки доски.",
    },
    {
        "name": "Votes",
        "description": "Голоса «за» и «против» чужих карточек. На карточку — один голос, его "
        "можно поменять или отозвать. За свои карточки голосовать нельзя.",
    },
    {
        "name": "Comments",
        "description": "Плоские комментарии к карточкам, без ответов на комментарии. "
        "Комментировать может каждый, а изменить или удалить комментарий — только автор.",
    },
    {
        "name": "Profile",
        "description": "Ваш профиль. Сначала это копия профиля на платформе курса, дальше вы "
        "редактируете его сами.",
    },
    {"name": "People", "description": "Участники доски: вы и ваши однокурсники."},
    {
        "name": "Admin",
        "description": "Инструменты команды курса, защищены заголовком `X-Admin-Token`. "
        "Студентам они не нужны.",
    },
    {"name": "System", "description": "Служебные эндпоинты. Токен не нужен."},
]


def _error_doc(description: str, examples: dict[str, tuple[str, str]]) -> dict[str, Any]:
    return {
        "model": ErrorResponse,
        "description": description,
        "content": {
            "application/json": {
                "examples": {
                    key: {"summary": summary, "value": {"detail": detail}}
                    for key, (summary, detail) in examples.items()
                }
            }
        },
    }


def not_found(detail: str) -> dict[str, Any]:
    return _error_doc(
        "Не найдено: такого объекта нет или его удалили.", {"not_found": ("Не найдено", detail)}
    )


def forbidden(detail: str) -> dict[str, Any]:
    return _error_doc("Это действие вам недоступно.", {"forbidden": ("Нельзя", detail)})


AUTH_ERRORS: dict[int | str, dict[str, Any]] = {
    401: _error_doc(
        "Заголовка `X-Course-Token` нет или токен недействителен.",
        {
            "missing": ("Токен не передан", MISSING_TOKEN),
            "invalid": ("Токен неверный или сброшен", str(invalid_token().detail)),
        },
    ),
    429: _error_doc(
        "Слишком много запросов с этого токена. Подождите `Retry-After` секунд.",
        {"too_many": ("Лимит запросов", rate_limit_detail(60))},  # 60 is the default limit
    ),
    503: _error_doc(
        "Платформа курса недоступна, поэтому токен не проверить. Повторите запрос чуть позже.",
        {"platform_down": ("Платформа недоступна", str(platform_unavailable().detail))},
    ),
}

ADMIN_ERRORS: dict[int | str, dict[str, Any]] = {
    401: _error_doc("Нет заголовка `X-Admin-Token`.", {"missing": ("Нет токена", ADMIN_MISSING)}),
    403: _error_doc("Неверный админский токен.", {"wrong": ("Неверный токен", ADMIN_WRONG)}),
    503: _error_doc(
        "Админский API не настроен на этом сервере.", {"disabled": ("Выключен", ADMIN_DISABLED)}
    ),
}


def _validation_example(summary: str, errors: list[tuple[str, str]]) -> dict[str, Any]:
    return {
        "summary": summary,
        "value": {
            "detail": "; ".join(f"{field}: {message}" for field, message in errors),
            "errors": [{"field": field, "message": message} for field, message in errors],
        },
    }


VALIDATION_ERROR: dict[str, Any] = {
    "model": ValidationErrorResponse,
    "description": "Некорректные данные. В `errors` перечислены все проблемы, по одной на поле.",
    "content": {
        "application/json": {
            "examples": {
                "missing_field": _validation_example("Нет обязательного поля", [("title", REQUIRED)]),
                "bad_value": _validation_example(
                    "Недопустимое значение",
                    [("type", "Допустимые значения: 'event', 'idea', 'question'")],
                ),
                "no_json": _validation_example(
                    "Тело не JSON (забыли Content-Type?)", [("body", BODY_NOT_JSON)]
                ),
            }
        }
    },
}

EMAIL_CONFLICT: dict[str, Any] = {
    "model": ValidationErrorResponse,
    "description": "Этот email уже использует другой участник.",
    "content": {
        "application/json": {
            "examples": {
                "email_taken": {
                    "summary": "Email уже занят",
                    "value": {
                        "detail": EMAIL_TAKEN_DETAIL,
                        "errors": [{"field": "email", "message": EMAIL_TAKEN}],
                    },
                }
            }
        }
    },
}
