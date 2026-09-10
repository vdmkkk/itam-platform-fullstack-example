# ITAM Board API

The example backend of the **Frontend (ITAM)** course (`frontend-itam`): a small Trello-like
board where everyone in a stream posts **events**, **ideas** and **questions**, votes on each
other's cards and discusses them in comments. Students build a React frontend against it
during the course.

- **Swagger (the students' main reference):** https://courses.salut.uno/example-backend/frontend-itam/docs
- **ReDoc:** https://courses.salut.uno/example-backend/frontend-itam/redoc
- **OpenAPI schema (for codegen):** https://courses.salut.uno/example-backend/frontend-itam/openapi.json

FastAPI + Postgres, deployed beside the courses platform as its own Docker Compose stack.

---

## Гайд для студентов

**Адрес API:** `https://courses.salut.uno/example-backend/frontend-itam`
Все эндпоинты начинаются с `/api`, например `GET /api/cards`.

**Авторизация — один заголовок, без логина и паролей:**

```
X-Course-Token: exb_xxxxxxxxxxxxxxxxxxxxxxxx
```

Где взять токен: страница курса → вкладка **«API проекта»** → кнопка «Копировать».
Если токен утёк или перестал работать — там же нажмите «Сбросить» и вставьте новый.

**Swagger без фронтенда:** откройте [документацию](https://courses.salut.uno/example-backend/frontend-itam/docs),
нажмите **Authorize**, вставьте токен — и отправляйте любые запросы прямо из браузера.

**Примеры на `fetch`:**

```js
const API_URL = "https://courses.salut.uno/example-backend/frontend-itam";
const TOKEN = "exb_..."; // со страницы курса, вкладка «API проекта»

// 1. Вся доска: карточки со счётом, голосами и числом комментариев
const cards = await fetch(`${API_URL}/api/cards`, {
  headers: { "X-Course-Token": TOKEN },
}).then((response) => response.json());

// 2. Новая карточка (обязательны только title и type)
const created = await fetch(`${API_URL}/api/cards`, {
  method: "POST",
  headers: { "X-Course-Token": TOKEN, "Content-Type": "application/json" },
  body: JSON.stringify({ title: "Сходить на хакатон", type: "event", date: "2026-10-01" }),
}).then((response) => response.json());

// 3. Голос за чужую карточку (за свою нельзя — сервер ответит 403)
const someoneElses = cards.find((card) => !card.is_mine);
await fetch(`${API_URL}/api/cards/${someoneElses.id}/vote`, {
  method: "PUT",
  headers: { "X-Course-Token": TOKEN, "Content-Type": "application/json" },
  body: JSON.stringify({ value: "up" }),
});
```

**Типы для TypeScript:**

```sh
npx openapi-typescript https://courses.salut.uno/example-backend/frontend-itam/openapi.json -o src/shared/api/schema.d.ts
```

Полезно знать:

- Ошибки всегда приходят как `{"detail": "понятное сообщение"}`, а ошибки валидации (422) ещё и
  как `errors: [{"field": "title", "message": "..."}]` — удобно подсвечивать поля формы.
- `204 No Content` (удаление) приходит с пустым телом — не вызывайте `response.json()`.
- Лимит — 60 запросов в секунду на токен. `useEffect` без массива зависимостей его быстро найдёт.
- Вы видите только свой поток. У нового потока доска сразу заполнена демо-карточками
  (`author.is_demo: true`), чтобы было что рендерить с первого запроса.

---

## The domain

| Column     | A card is there when…                                  |
| ---------- | ------------------------------------------------------ |
| `event`    | `type == "event"` and votes haven't decided it         |
| `idea`     | `type == "idea"` and votes haven't decided it          |
| `question` | `type == "question"` and votes haven't decided it      |
| `accepted` | `score >= accept_threshold`, whatever its type         |
| `rejected` | `score <= -reject_threshold`, whatever its type        |

- A card has `title` and `type` (required), plus optional `description`, `preview` (an image
  as a string: an http(s) link or a `data:image/...` URI) and `date` (`YYYY-MM-DD`).
- `score = upvotes - downvotes`. Acceptance is computed live, so a card keeps its original
  `type`, `is_accepted` / `is_rejected` are separate flags, and `column` says where to draw it.
- Anyone in the stream can vote (one vote per card, changeable) and comment (flat comments).
  Nobody can vote on their own card. Only authors edit or delete their cards and comments.
- Profiles (`name`, `email`, `avatar_url`, `status`, `bio`, `telegram`) are copied from the
  platform on first contact, then belong to the student. Emails are unique per stream and
  visible only to their owner.

### Endpoints

| Method | Path                            | What                                        |
| ------ | ------------------------------- | ------------------------------------------- |
| GET    | `/api/board`                    | Columns with counts, thresholds, stream     |
| GET    | `/api/cards`                    | All cards (filters: `column`, `type`, `author_id`, `q`, `sort`) |
| POST   | `/api/cards`                    | Create a card                               |
| GET    | `/api/cards/{id}`               | One card with its comments and their authors |
| PATCH  | `/api/cards/{id}`               | Edit your card                              |
| DELETE | `/api/cards/{id}`               | Delete your card                            |
| PUT    | `/api/cards/{id}/vote`          | Vote `up` / `down`                          |
| DELETE | `/api/cards/{id}/vote`          | Remove your vote                            |
| GET    | `/api/cards/{id}/comments`      | Comments on a card                          |
| POST   | `/api/cards/{id}/comments`      | Comment on a card                           |
| PATCH  | `/api/comments/{id}`            | Edit your comment                           |
| DELETE | `/api/comments/{id}`            | Delete your comment                         |
| GET    | `/api/me`                       | Your profile                                |
| PATCH  | `/api/me`                       | Edit your profile (409 if the email is taken) |
| GET    | `/api/users`                    | Members of your stream                      |
| GET    | `/api/users/{id}`               | One member with activity counters           |
| GET    | `/health`                       | Health check, no token                      |

Admin (header `X-Admin-Token`): `GET/PATCH /api/admin/settings` (vote thresholds, shared by
all streams), `GET /api/admin/streams`, and `DELETE /api/admin/cards/{id}` and
`DELETE /api/admin/comments/{id}` for moderation.

```sh
curl -X PATCH https://courses.salut.uno/example-backend/frontend-itam/api/admin/settings \
  -H "X-Admin-Token: $ADMIN_TOKEN" -H "Content-Type: application/json" \
  -d '{"accept_threshold": 3, "reject_threshold": 3}'
```

---

## How it works

- **Identity.** Every request's `X-Course-Token` is exchanged at the platform
  (`POST /api/v1/example-backends/frontend-itam/introspect`) using our service key. Answers
  are cached by token hash for 45 s, and "unknown token" answers for 3 s. Platform `404` becomes
  `401` for the student. Platform `401` (a bad service key) becomes `500` and a loud log line,
  never `401`. Platform down or timing out becomes `503`, unless the identity is still cached.
- **Streams are a hard partition.** Every table carries `stream_id`, and every foreign key
  includes it (`(stream_id, card_id) → cards(stream_id, id)`), so the database refuses rows
  that mix streams. Every lookup filters by the caller's stream, so another stream's id is
  indistinguishable from a missing one (404). Students without a stream share a separate
  partition (the nil UUID) and never see anyone else.
- **Local users** are keyed on `(stream_id, platform user id)`, never on email. A student
  moved to another stream starts fresh there, and their old content stays behind.
- **Seeding.** The first request from a new stream creates it and seeds demo people, cards,
  votes and comments in the same transaction. `INSERT … ON CONFLICT DO NOTHING` ensures only
  one racing request seeds.
- **People list.** `GET /api/users` also pulls the stream roster from the platform (at most
  once a minute per stream), so classmates who haven't called the API yet still appear.
- **Rate limit.** A token bucket of 60 req/s per token returns `429` with `Retry-After`.
- **Errors** are always `{"detail": "sentence"}`. 422 responses add `errors: [{field, message}]`.
  Unhandled exceptions become JSON 500s inside the CORS middleware, so browsers see the real
  error instead of a CORS failure.

## Configuration

| Variable | Purpose |
| --- | --- |
| `BACKEND_SLUG` | Slug registered in the platform (`frontend-itam`) |
| `BACKEND_PORT` | Loopback port (`19100`) |
| `PLATFORM_API_URL` | Platform API base, no trailing slash |
| `PLATFORM_SERVICE_KEY` | Service key from the platform admin (secret) |
| `PUBLIC_BASE_URL` | Absolute public URL, used in the docs and as the OpenAPI server |
| `ROOT_PATH` | Set by compose to `/example-backend/<slug>` |
| `ADMIN_TOKEN` | Token for `/api/admin` (empty disables it) |
| `DEFAULT_ACCEPT_THRESHOLD` / `DEFAULT_REJECT_THRESHOLD` | Initial thresholds (5 / 5) |
| `POSTGRES_DB` / `POSTGRES_USER` / `POSTGRES_PASSWORD` | This stack's own database |

Tunables with defaults: `IDENTITY_CACHE_TTL_SECONDS=45`, `IDENTITY_NEGATIVE_CACHE_TTL_SECONDS=3`,
`ROSTER_CACHE_TTL_SECONDS=60`, `PLATFORM_TIMEOUT_SECONDS=5`, `RATE_LIMIT_PER_SECOND=60`,
`RATE_LIMIT_BURST=60`.

## Development

```sh
cd backend
python -m venv .venv && . .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"

# A local Postgres, and a .env with DATABASE_URL, PLATFORM_* and ADMIN_TOKEN
docker run -d --name board-pg -e POSTGRES_PASSWORD=postgres -p 5432:5432 postgres:17-alpine
alembic upgrade head
uvicorn app.main:create_app --factory --reload
```

Tests need a disposable Postgres, and the database name must contain `test`:

```sh
docker compose -f docker-compose.test.yml run --rm --build tests
docker compose -f docker-compose.test.yml down
```

`tests/test_isolation.py` covers the stream partition: same-stream students interact,
other-stream students can neither see nor mutate anything even with known ids, and the
database itself rejects cross-stream rows.

## Deployment

It runs on the platform host (`root@5.42.110.221`) from `/root/itam-platform-fullstack-example`.
It is published through the platform's example backends gateway by the `exb` host tool (see
`courses-platform/infra/example-backends/README.md`). Nothing here edits nginx.

First time (already done):

```sh
git clone https://github.com/vdmkkk/itam-platform-fullstack-example.git /root/itam-platform-fullstack-example
cd /root/itam-platform-fullstack-example/backend
cp .env.example .env   # set POSTGRES_PASSWORD and ADMIN_TOKEN to long random strings
exb register frontend-itam --course frontend-itam --title "ITAM Board API" --env-file "$PWD/.env"
docker compose --env-file .env up --build -d
exb check frontend-itam --auth-path /api/me
```

Every later deploy:

```sh
ssh root@5.42.110.221 'cd /root/itam-platform-fullstack-example && git pull --ff-only && cd backend && docker compose --env-file .env up --build -d'
```

Useful on the host:

- `exb list`
- `exb check frontend-itam --auth-path /api/me`
- `exb test-students frontend-itam create --count 2`, then `... delete` when done: real
  student tokens for live tests. An admin's own token is always rejected.
- `exb rotate-key frontend-itam --env-file /root/itam-platform-fullstack-example/backend/.env`,
  then `docker compose --env-file .env up -d` right away. Until the restart, every student
  request gets a 500.

Migrations run on container start (`alembic upgrade head`).
