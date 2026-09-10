# Master Prompt — Build a Course Example Backend

Paste everything below the line into a fresh chat. Fill the four bracketed
values in **Your assignment** first; the rest is self-contained and needs no
access to the courses-platform repository.

---

You are building an **example backend**: a small public API that students of an
online course build a frontend against while they learn React. It is a teaching
tool, not a product. Your job is the API and its deployment, nothing else.

## Your assignment

- **Course topic / domain model:** `[e.g. a Trello clone: boards, lists, cards, comments]`
- **Course slug:** `[e.g. react-crash]`: the platform course whose students use it
- **Backend slug:** `[e.g. react-crash]`: the URL segment, and the identifier the platform knows the backend by
- **Public base URL:** `[e.g. https://courses.salut.uno/example-backend/react-crash]`
- **Platform API URL:** `[e.g. https://courses.salut.uno]`

## The one idea that shapes everything

Students must write **zero authentication code**. No login window, no cookies,
no refresh tokens. A student copies a personal token from their course page and
hardcodes it into a single request header:

```
X-Course-Token: exb_xxxxxxxxxxxxxxxxxxxxxxxx
```

That is deliberately insecure and it is correct here. The token unlocks only
this teaching API. Do not add a login flow, do not add password fields, do not
"improve" this by moving the token into a cookie. If you find yourself building
auth UI affordances, you have misread the assignment.

You never see a platform password. You hold one secret — a **service key** — and
you exchange student tokens for identities against the platform.

## Identity: the platform contract

You are given two environment values:

```
PLATFORM_API_URL      # e.g. https://courses.salut.uno
PLATFORM_SERVICE_KEY  # exbk_... — secret, server-side only, never sent to a browser
BACKEND_SLUG          # e.g. react-crash
```

### Resolving a request

On every request, read `X-Course-Token` and exchange it:

```
POST {PLATFORM_API_URL}/api/v1/example-backends/{BACKEND_SLUG}/introspect
Authorization: Bearer {PLATFORM_SERVICE_KEY}
Content-Type: application/json

{"token": "exb_..."}
```

Success (200):

```json
{
  "user": {
    "id": "0b1f…",
    "email": "student@example.com",
    "display_name": "Аня Смирнова",
    "name": "Аня",
    "surname": "Смирнова",
    "avatar_url": "https://…/avatar.png"
  },
  "stream": {
    "id": "7c2a…",
    "code": "26F",
    "title": "Осенний поток",
    "starts_on": null,
    "ends_on": null
  },
  "course_id": "…",
  "course_slug": "react-crash",
  "course_title": "React Crash Course",
  "backend_slug": "react-crash"
}
```

Failures, and how to translate them — **do not collapse these two**:

| Platform says | Cause                                                              | You return                          |
| ------------- | ------------------------------------------------------------------ | ----------------------------------- |
| 401           | Your service key is wrong/rotated, or the backend was disabled      | **500** + log loudly. Your problem.  |
| 404           | Unknown/rotated token, revoked enrollment, unpublished course        | **401** with a clear message. Theirs.|
| 5xx / timeout | Platform down                                                       | **503**                             |

Getting this backwards is the single most confusing failure mode: a rotated
service key would tell every student their own token expired.

### Caching

Cache introspection results keyed by a hash of the token for **30–60 seconds**.
Not longer — rotation is a student's remedy for a leaked token and must take
effect quickly. Cache negative results for a few seconds at most.

### Local user records

Key your local user rows on `user.id` (a UUID, stable forever). Never key on
email — students can change it.

Copy `display_name` / `name` / `surname` / `avatar_url` **the first time** you
see a user, as defaults for their profile in your app. After that they are the
student's to edit locally. A student renaming themselves in your Trello clone
must not rename themselves on the platform, and a platform rename must not
clobber a local edit. The accounts stay linked through `user.id`.

## Streams are a hard partition — this is the important part

`stream` is the **work group**: everyone who started the course in the same
period. It is not a label. It is a tenancy boundary.

Rules, without exception:

1. Every row you create stores the acting user's `stream_id`.
2. Every read filters by the requesting user's `stream_id`.
3. No mutation may touch a row from another stream — including by guessing an
   id. Check ownership on the way in, not just in list queries.
4. Foreign keys never cross a stream.

So the autumn 2026 intake shares a board space, sees each other, assigns cards
to each other; the spring 2027 intake gets a clean, empty world. Two students in
different streams must be unable to observe each other's existence.

`stream.id` can be `null` in rare legacy cases. Treat null as its own isolated
group — never as "sees everything".

`stream.title` is frequently `null` (auto-created streams are unnamed until an
admin names one). Display `title || code`, and never require a title.

### Listing the work group

For "assign to teammate" pickers:

```
GET {PLATFORM_API_URL}/api/v1/example-backends/{BACKEND_SLUG}/streams/{stream_id}/members
Authorization: Bearer {PLATFORM_SERVICE_KEY}
```

```json
{
  "stream": { "id": "…", "code": "26F", "title": "Осенний поток" },
  "members": [{ "id": "…", "email": "…", "display_name": "…", "avatar_url": "…" }]
}
```

Only ever request the stream of the calling student. Cache it briefly.

## What to build

A REST API for the domain model in your assignment. It should:

- be **FastAPI + Postgres**, matching the platform's stack, unless told otherwise;
- expose full CRUD over the domain, with sensible validation and 4xx errors;
- ship **Swagger at `/docs`**, because students are given that link directly and
  will use it as their primary reference;
- have a `GET /health` returning 200 with no auth (used by deploy checks);
- **seed demo data per stream on first contact**, so a student's very first
  `GET` returns something interesting instead of an empty array. An empty screen
  is a bad first lesson.

### API design for learners

This API is read by beginners. Optimise for legibility:

- plain, predictable resource paths: `/boards`, `/boards/{id}/lists`, `/cards/{id}`;
- `snake_case` JSON, ISO-8601 UTC timestamps, UUID string ids;
- errors as `{"detail": "human readable sentence"}` — never a bare code;
- a consistent list shape; if you paginate, paginate everywhere the same way;
- no HATEOAS, no envelopes, no RPC-style verbs in paths.

### CORS

Students call this from `localhost:5173`, from deployed static hosts, and from
CodeSandbox. Allow all origins, allow the `X-Course-Token` header, and make
preflight cheap. There are no cookies, so permissive CORS costs nothing here.

### Rate limiting

Apply a light per-user cap (say 60 req/s) so one runaway `useEffect` loop cannot
take the API down for a whole cohort. Return 429 with a plain-language `detail`.

## Deployment shape

Your stack runs beside the platform on the same host, isolated:

- its own Docker Compose project, its own Postgres, its own volume;
- the API binds to **loopback only**: `127.0.0.1:${BACKEND_PORT}:8000`;
- the platform publishes it at `{origin}/example-backend/{slug}/` through the
  example backends gateway. You never write or edit any nginx config.

**The path-prefix gotcha.** The gateway's `proxy_pass` ends with a trailing
slash, so it strips `/example-backend/{slug}` before your app sees the request.
Your app must therefore set FastAPI's `root_path="/example-backend/{slug}"`,
read from a `ROOT_PATH` env var, so that Swagger and the OpenAPI `servers` block
re-advertise the prefix. Strip in the proxy, re-advertise in the app. If only
one of the two is set, Swagger renders but every "Try it out" call 404s.

Your compose file reads the platform wiring from `.env`, and the platform's
`exb` tool writes it for you: `BACKEND_SLUG`, `BACKEND_PORT`,
`PLATFORM_API_URL`, `PLATFORM_SERVICE_KEY`, `PUBLIC_BASE_URL`. Set
`ROOT_PATH: /example-backend/${BACKEND_SLUG}` in the compose file itself.

Deliver:

- `Dockerfile`;
- `docker-compose.yml` (postgres + api, `127.0.0.1:${BACKEND_PORT}:8000`,
  `ROOT_PATH`, `restart: unless-stopped`, a healthcheck on `/health`);
- `.env.example` documenting every variable;
- automated tests (see the acceptance criteria);
- a `README.md` with deploy steps and a **"Guide for students"** section: the
  base URL, the header name, how to get the token from the course page, and two
  or three copy-pasteable `fetch` examples.

Never commit real secrets. `PLATFORM_SERVICE_KEY` lives only in the deployment's
environment.

## Hosting it on the platform

If you have shell access to the platform host, you deploy it yourself, and you
can do so safely. Everything goes through one tool, `exb`. It only touches the
example backends gateway and the platform's example-backend records, never the
live platform's configuration:

```sh
git clone <your repo> /root/<repo> && cd /root/<repo>
cp .env.example .env    # fill in your own secrets, e.g. POSTGRES_PASSWORD
exb register <backend-slug> --course <course-slug> --env-file /root/<repo>/.env
docker compose --env-file .env up --build -d
exb check <backend-slug> --auth-path <an endpoint that needs a token>
```

`exb register` allocates the port, publishes the route, registers the backend
(students see it on the course page straight away) and writes the platform
variables into `.env`. Redeploy after a change with
`git pull && docker compose --env-file .env up --build -d`.

For end-to-end tests with real tokens, use test students. The platform only
accepts **student** tokens, so an admin's own token from the course page always
gets 401:

```sh
exb test-students <backend-slug> create --count 2     # the same stream
exb test-students <backend-slug> create --no-stream   # a second, isolated partition
exb test-students <backend-slug> delete               # always clean up
```

Your backend treats test students as ordinary users. Test students in a real
stream appear in that cohort's data until you delete their local rows (their
emails end in `@example.invalid`), so clean those up after a live run.

Never edit `/root/courses-edge-nginx.conf`, the platform's compose files or
another backend's stack. If `exb` refuses something, fix the input rather than
working around the tool. `exb --help` and `exb list` show everything else.

## Acceptance criteria

Before you call it done, verify:

1. A request with no `X-Course-Token` gets 401 with a helpful message.
2. A request with a garbage token gets 401 — not 500.
3. A valid token returns data, and the user is auto-provisioned on first sight
   with their platform name and avatar as defaults.
4. Two tokens from the **same** stream see and can interact with each other's data.
5. Two tokens from **different** streams cannot see each other's data, and cannot
   mutate it even when passing a known id from the other stream directly.
6. A rotated token stops working within the cache TTL.
7. A wrong service key surfaces as 500 to the student, never as 401.
8. `/docs` renders behind the path prefix and its "Try it out" calls succeed.
9. `/health` returns 200 without auth.
10. A brand-new student in a brand-new stream sees seeded demo data, not an
    empty list.
11. Once deployed, `exb check <backend-slug> --auth-path <endpoint>` passes on
    the host, and a live run with test students confirms 3-6 through the public
    URL. Delete the test students afterwards.

Write automated tests for 4 and 5 specifically. Cross-stream leakage is the one
bug that would quietly ruin the exercise, and it is invisible until two cohorts
overlap.

## Ask before you assume

If the domain model is underspecified, propose a concrete schema and continue —
do not stall. But stop and ask if you find yourself wanting to change the
identity contract, weaken the stream partition, or add a real login. Those are
platform-level decisions and are not yours to make here.
