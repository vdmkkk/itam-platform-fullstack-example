"""Texts for the OpenAPI document: the Swagger intro, tag descriptions and shared error docs.

Students use Swagger as their main reference, so these texts are part of the
product, not an afterthought.
"""

from __future__ import annotations

from typing import Any

from app.config import Settings
from app.schemas import ErrorResponse, ValidationErrorResponse

INTRO = """
The **ITAM Board** is a small Trello-like API for the *Frontend (ITAM)* course. Everyone in your
stream shares one board of **events**, **ideas** and **questions**: you post cards, vote on each
other's cards and discuss them in the comments. During the course you will build a React
frontend for it.

## 1. Authorize (30 seconds)

There is **no login**. Every request carries your personal course token in a single header:

```
X-Course-Token: exb_xxxxxxxxxxxxxxxxxxxxxxxx
```

1. Open the course page, go to the **«API проекта»** tab and copy your token.
2. Click the **Authorize** button on this page, paste the token into `CourseToken` and press
   *Authorize*.
3. Open any endpoint and press **Execute**. Good first calls are `GET /api/me` and
   `GET /api/cards`.

Swagger remembers the token in this browser, so you only have to do this once.

## 2. How the board works

| Column | A card is here when… |
| --- | --- |
| `event` | its `type` is `"event"` and votes haven't decided it yet |
| `idea` | its `type` is `"idea"` and votes haven't decided it yet |
| `question` | its `type` is `"question"` and votes haven't decided it yet |
| `accepted` | `score >= accept_threshold`, whatever its type |
| `rejected` | `score <= -reject_threshold`, whatever its type |

* Anyone can create a card in one of the first three columns (`type` is `event`, `idea` or
  `question`). The author can change the type at any time.
* `score = upvotes - downvotes`. The course team sets the thresholds; you can read them from
  `GET /api/board`.
* An accepted or rejected card **keeps its `type`**. `is_accepted` and `is_rejected` are
  separate flags, and `column` tells you where to draw the card.
* Everything is computed live: if votes change, the card moves back.

## 3. Rules

* You only see your own stream (cohort). Other streams have their own boards, and you can't
  reach them even with a known id: you get 404.
* You can vote on and comment on anyone's cards, but you **can't vote on your own** (that gives 403).
* Only the author can edit or delete a card or a comment.
* Your profile starts with your name, email and avatar from the course platform. Editing it
  here doesn't touch the platform.
* A brand-new board comes with a few demo cards from demo people (`is_demo: true`), so you have
  something to render straight away.

## 4. From code

```js
const API_URL = "__BASE__";
const TOKEN = "exb_..."; // your token from the course page

// Read the whole board
const response = await fetch(`${API_URL}/api/cards`, {
  headers: { "X-Course-Token": TOKEN },
});
if (!response.ok) {
  const error = await response.json(); // { detail: "..." }
  throw new Error(error.detail);
}
const cards = await response.json();

// Create a card
await fetch(`${API_URL}/api/cards`, {
  method: "POST",
  headers: { "X-Course-Token": TOKEN, "Content-Type": "application/json" },
  body: JSON.stringify({ title: "Сходить на хакатон", type: "event", date: "2026-10-01" }),
});

// Upvote someone else's card
await fetch(`${API_URL}/api/cards/${cardId}/vote`, {
  method: "PUT",
  headers: { "X-Course-Token": TOKEN, "Content-Type": "application/json" },
  body: JSON.stringify({ value: "up" }),
});
```

## 5. Conventions

* JSON with `snake_case` fields. Ids are UUID strings.
* Timestamps are ISO-8601 in UTC (`2026-09-10T12:00:00Z`). Dates are `YYYY-MM-DD`.
* Lists are plain JSON arrays, with no pagination and no wrapper object.
* Errors always look like `{"detail": "A human-readable sentence"}`. Invalid data (422) also
  includes `errors: [{"field": "...", "message": "..."}]`, so you can show each message next to
  the right form input.

| Code | Meaning |
| --- | --- |
| `200` | OK |
| `201` | Created: the body is the new object |
| `204` | Done, and the body is **empty**, so don't call `response.json()` |
| `401` | The token is missing or not valid |
| `403` | You're not allowed to do this, such as edit someone else's card |
| `404` | Not found, or it belongs to another stream |
| `409` | Conflict, such as an email that is already in use |
| `422` | The data is invalid; see `errors` |
| `429` | Too many requests. The limit is __RATE__ per second per token, so a `useEffect` without a dependency array will hit it |
| `503` | The course platform is temporarily unavailable, so your token can't be checked. Try again |

## 6. TypeScript types

The machine-readable schema is at [`__BASE__/openapi.json`](__BASE__/openapi.json).
Generate types from it:

```sh
npx openapi-typescript __BASE__/openapi.json -o src/shared/api/schema.d.ts
```

Prefer a different layout? The same docs are at [`/redoc`](__BASE__/redoc).
"""


def api_description(settings: Settings) -> str:
    return (
        INTRO.replace("__BASE__", settings.docs_base_url)
        .replace("__RATE__", f"{settings.rate_limit_per_second:g}")
        .strip()
    )


TAGS: list[dict[str, Any]] = [
    {
        "name": "Board",
        "description": "The board as a whole: columns, vote thresholds and your stream. "
        "A good first request.",
    },
    {
        "name": "Cards",
        "description": "Create, read, edit and delete cards. `GET /api/cards` returns everything "
        "needed to render the board in one request.",
    },
    {
        "name": "Votes",
        "description": "Upvote or downvote other people's cards. You get one vote per card, and "
        "you can change or remove it. You can't vote on your own cards.",
    },
    {
        "name": "Comments",
        "description": "Flat comments on cards, with no replies to comments. Anyone in the stream "
        "can comment. Only the author can edit or delete a comment.",
    },
    {
        "name": "Profile",
        "description": "Your own profile. It starts as a copy of your course platform profile "
        "and is yours to edit.",
    },
    {"name": "People", "description": "The other members of your stream."},
    {
        "name": "Admin",
        "description": "Course-team tools, protected by the `X-Admin-Token` header. Students "
        "don't need them.",
    },
    {"name": "System", "description": "Service endpoints. They need no token."},
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
        "Not found. It doesn't exist, was deleted, or belongs to another stream.",
        {"not_found": ("Not found", detail)},
    )


def forbidden(detail: str) -> dict[str, Any]:
    return _error_doc("You are not allowed to do this.", {"forbidden": ("Not allowed", detail)})


AUTH_ERRORS: dict[int | str, dict[str, Any]] = {
    401: _error_doc(
        "The `X-Course-Token` header is missing or the token is not valid.",
        {
            "missing": (
                "No token sent",
                "Missing X-Course-Token header. Copy your token from the course page "
                "(tab «API проекта»). Send it with every request. In Swagger, click Authorize.",
            ),
            "invalid": (
                "Token is wrong or was reset",
                "Your course token is not valid: it may have been reset, or you no longer have "
                "access to the course. Copy your token from the course page (tab «API проекта»).",
            ),
        },
    ),
    429: _error_doc(
        "Too many requests from this token. Wait `Retry-After` seconds.",
        {
            "too_many": (
                "Rate limit",
                "Too many requests: the limit is 60 per second per token. Is a useEffect "
                "re-running in a loop? Check its dependency array.",
            )
        },
    ),
    503: _error_doc(
        "The course platform can't be reached to check the token. Try again shortly.",
        {
            "platform_down": (
                "Platform unavailable",
                "The course platform is not responding, so we can't check your token right now. "
                "Please try again in a minute.",
            )
        },
    ),
}

ADMIN_ERRORS: dict[int | str, dict[str, Any]] = {
    401: _error_doc("No `X-Admin-Token` header.", {"missing": ("No token", "Missing X-Admin-Token header.")}),
    403: _error_doc("Wrong admin token.", {"wrong": ("Wrong token", "Wrong admin token.")}),
    503: _error_doc(
        "The admin API is not configured on this server.",
        {
            "disabled": (
                "Disabled",
                "The admin API is disabled: ADMIN_TOKEN is not configured on the server.",
            )
        },
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
    "description": "The data is invalid. `errors` lists every problem, one per input.",
    "content": {
        "application/json": {
            "examples": {
                "missing_field": _validation_example(
                    "A required field is missing", [("title", "This field is required")]
                ),
                "bad_value": _validation_example(
                    "A value is not allowed",
                    [("type", "Input should be 'event', 'idea' or 'question'")],
                ),
                "no_json": _validation_example(
                    "Body is not JSON (forgot Content-Type?)",
                    [
                        (
                            "body",
                            "Send the request body as a JSON object, with the header "
                            "Content-Type: application/json",
                        )
                    ],
                ),
            }
        }
    },
}

EMAIL_CONFLICT: dict[str, Any] = {
    "model": ValidationErrorResponse,
    "description": "Another member of your stream already uses this email.",
    "content": {
        "application/json": {
            "examples": {
                "email_taken": _validation_example(
                    "Email already in use", [("email", "This email is already in use")]
                )
            }
        }
    },
}
