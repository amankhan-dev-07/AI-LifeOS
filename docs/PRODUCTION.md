# AI-LifeOS — Production Deployment Guide

This document reflects the actual code in this repository. It is written for
deploying the backend and frontend as real, multi-user services.

Nothing here is provider-specific. Pick a host, then apply these settings.

---

## 1. Configuration files

There are **two** `.env` files in this repository, and they serve different
processes. Do not conflate them.

| File | Read by | `DATABASE_URL` host |
|---|---|---|
| `/.env` (root) | **Docker Compose**, for the `db`, `backend`, `migrate` containers | `db` (Compose service name) |
| `/backend/.env` | The backend **only** when you run `uvicorn` directly on your machine | `localhost` |

Compose resolves `${VARIABLE}` from the environment and from a `.env` in the
**repository root**. This is Compose's own behaviour — it does not read
`backend/.env` — which is why the root file exists. Start from the templates:

```bash
cp .env.example .env                  # for Docker Compose
cp backend/.env.example backend/.env  # for running uvicorn directly
```

Both are gitignored. Neither should ever be committed.

### Root `.env` — used by Docker Compose

Template: `.env.example`. These feed the containers.

| Variable | Required | Notes |
|---|---|---|
| `POSTGRES_USER` | No | Defaults to `postgres`. |
| `POSTGRES_PASSWORD` | **Yes** | **No default.** Compose fails with an explanatory error if unset. Must be a strong unique value in production. |
| `POSTGRES_DB` | No | Defaults to `ai_lifeos`. |
| `SECRET_KEY` | **Yes** | Compose reads the value from `.env`. The template ships the backend's placeholder (`change-this-secret-key`), which the backend **rejects at startup** while `DEBUG=false`. You must generate a real key before `docker compose up`. |
| `CORS_ORIGINS` | **Yes** (unless same-origin) | Comma-separated browser origins, no spaces: `https://app.example.com`. |
| `DEBUG` | No | Must be `false` in production. Defaults to `false`. |
| `DATABASE_URL` | No | **Overrides the DSN below.** See below. |

**Default behaviour.** With `DATABASE_URL` unset, Compose assembles the DSN from
the `POSTGRES_*` values so the backend and the database cannot drift apart:

```
postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@db:5432/${POSTGRES_DB}
```

**When to set `DATABASE_URL` explicitly.** Compose splices the password straight
into that URL, so a password containing `@`, `:` or `/` cannot survive it — the
character is read as URL syntax. If your password contains those characters,
set `DATABASE_URL` in the root `.env` with the password URL-encoded:

```
DATABASE_URL=postgresql://postgres:p%40ssw0rd@db:5432/ai_lifeos
```

When set, that value is used **verbatim** and `POSTGRES_USER` /
`POSTGRES_PASSWORD` no longer shape the connection string. Keep the host as
`db`.

Two things that do **not** change when you override it:

- `POSTGRES_PASSWORD` is still **required**. It configures the `db` service
  itself and is how the backend authenticates, independent of how the DSN is
  spelled. The value must match what you URL-encoded above.
- `SECRET_KEY` remains required and unrelated to the database.

The host is `db`, the Compose service name — **not `localhost`**. Inside a
container, `localhost` refers to that container itself, so a URL using it could
never reach the database.

### Backend `.env` — used when running uvicorn directly

Template: `backend/.env.example`. Read by `app/config/settings.py`.

| Variable | Required in production | Notes |
|---|---|---|
| `DATABASE_URL` | **Yes** | PostgreSQL DSN. URL-encode special characters in the password (`@` → `%40`). Use `localhost` when running against a local database. |
| `SECRET_KEY` | **Yes** | Signs JWTs. The placeholder is **rejected at startup** unless `DEBUG=true`. |
| `CORS_ORIGINS` | **Yes** (unless same-origin) | Comma-separated browser origins. |
| `DEBUG` | No | Must be `false` in production. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | Defaults to `30`. |
| `ALGORITHM` | No | Defaults to `HS256`. |
| `APP_NAME` / `APP_VERSION` | No | Cosmetic. |

The application **refuses to start** if `SECRET_KEY` is still the placeholder
and `DEBUG` is false. This is deliberate: the placeholder makes every JWT
forgeable, so anyone could authenticate as any user.

### Frontend

Read by Vite and inlined at **build** time. Changing one requires a rebuild.

| Variable | Required | Notes |
|---|---|---|
| `VITE_API_BASE_URL` | No | Defaults to `/api/v1` (relative). Leave as-is when the frontend and API share an origin. |

Only `VITE_`-prefixed variables reach the browser. **Never put a secret in the
frontend environment** — everything there ships to every visitor.

---

## 2. Commands

Run backend commands from `backend/` with the virtualenv activated.

```bash
# Install dependencies
pip install -r requirements.txt

# Apply migrations (run once, before starting the app)
alembic upgrade head

# Verify a single migration head
alembic heads

# Start the API
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Run frontend commands from `frontend/`.

```bash
npm ci          # install
npm run lint    # typecheck (tsc --noEmit)
npm run build   # production build into dist/
npm run preview # serve dist/ locally to sanity-check
```

### Docker Compose

Run from the **repository root**, where the root `.env` lives.

```bash
cp .env.example .env
# generate SECRET_KEY (required — the template value is rejected):
python -c "import secrets; print(secrets.token_urlsafe(64))"
# then edit .env: set the generated SECRET_KEY and a strong POSTGRES_PASSWORD
docker compose config         # validate and see the resolved configuration
docker compose build
docker compose up -d

# Apply migrations — a separate, explicit step (not run by `up`)
docker compose run --rm migrate

docker compose ps             # check health status
docker compose down           # stop; add -v to also delete the database volume
```

The `migrate` service is a one-shot runner behind the `migrate` profile. It is
deliberately not wired into the backend's `depends_on`: with more than one
backend replica, concurrent `alembic upgrade head` calls race on the same
schema and can corrupt it. Run migrations once, deliberately, before scaling.

---

## 3. Health checks

| Endpoint | Purpose |
|---|---|
| `GET /api/v1/health` | Liveness **plus a real `SELECT 1` against the database.** Returns `"degraded"` with `"database": "unavailable"` if the DB cannot be reached. |
| `GET /api/v1/health/live` | Process liveness only; does not touch the database. |

Use `/health/live` as a container restart trigger and `/health` as a readiness
gate. Pointing both at `/health` would restart a healthy process whenever the
database blips.

---

## 4. Production checklist

Configuration (root `.env`, used by Compose):

- [ ] `POSTGRES_PASSWORD` is a strong unique value — **not** the `postgres`
      literal from `.env.example`.
- [ ] `SECRET_KEY` is a freshly generated random value, not the placeholder.
- [ ] `CORS_ORIGINS` lists the real frontend origin.
- [ ] `DEBUG=false`.
- [ ] If `POSTGRES_PASSWORD` contains `@`, `:` or `/`, `DATABASE_URL` is set in
      the root `.env` with that password URL-encoded and the host still `db`.
      Otherwise confirm the default constructed DSN is being used and that the
      password contains no URL-significant characters.

Networking:

- [ ] **PostgreSQL is not published to the host or the internet.** Delete the
      `ports: - "5432:5432"` block from the `db` service in
      `docker-compose.yml`. As written it publishes the database on the host's
      port 5432, which is intended for local development only. Leaving it in
      place on a reachable host exposes the database directly, bypassing the
      API entirely.
- [ ] `POSTGRES_PASSWORD` is not the value from `.env.example`.
- [ ] HTTPS is terminated in front of the frontend.

Schema and data:

- [ ] `docker compose run --rm migrate` has been run (equivalent to
      `alembic upgrade head`). It is deliberately **not** run by `up`, so the
      schema change is an explicit, ordered step.
- [ ] `alembic heads` reports exactly one head.
- [ ] Database backups are configured and a restore has been tested.

Serving:

- [ ] The frontend is built and served, with `index.html` not cached.

---

## 5. Behaviour worth knowing before deploying

**Scheduler.** `app/services/reminder_scheduler.py` runs an asyncio task on the
FastAPI lifespan: it ticks every 60s, delivers at most 50 due reminders per
tick, and gives up after 20s so a stuck query cannot take the loop down. State
lives entirely in the `reminders` table, so overdue reminders survive a restart.

It starts one task **per process**. If you run multiple Uvicorn workers or
multiple replicas, you get one scheduler per process. That is safe for
correctness — each reminder is stamped `notified_at` in the same transaction as
its notification, so no reminder is delivered twice — but it multiplies
background query load. For a low-end instance, run a single worker.

**Multi-worker caution.** `--reload` and multiple workers are fine for
development. In production prefer one worker per container and scale with
containers, which keeps the scheduler count predictable and keeps the
connection pool small (see below).

**Connection pool.** `app/db/database.py` configures `pool_size=5`,
`max_overflow=5` (10 max per process), `pool_pre_ping=True` and
`pool_recycle=1800`. `pool_pre_ping` is what prevents the "first request after
an idle period fails" class of bug. Keep total connections across all workers
well under PostgreSQL's `max_connections`.

**No migrations at startup.** The container runs `alembic upgrade head` only
when you invoke the `migrate` service explicitly. Concurrent replicas racing
on migrations is a real failure mode; keep it a deliberate, ordered step.

**AI brain.** `app/services/ai_brain_service.py` calls a local Ollama instance
at `http://localhost:11434` with a 120s timeout, and degrades gracefully with a
clear message when it is offline. Deterministic LifeOS commands (create, list,
complete tasks/goals/habits, daily plan) do **not** require Ollama. If you deploy
without Ollama, general chat falls back to a verified-data snapshot rather than
inventing answers.

**Token storage.** The JWT is kept in `localStorage`. This is the existing
architecture and was not changed in this phase. It is readable by any script
running on the page, so it relies on there being no XSS in the app. Moving to an
`httpOnly` cookie would be a real improvement but is an architectural change,
deliberately out of scope here.

**Interactive API docs.** `/docs`, `/redoc` and `/openapi.json` are disabled
when `DEBUG=false`, so the route surface is not advertised in production.

**Error responses.** Unhandled exceptions are logged server-side with a
timestamp and return a generic `{"detail": "An unexpected error occurred."}`.
This body is identical in DEBUG and production, so toggling `DEBUG` cannot start
leaking stack traces to clients.

---

## 6. Known limitations

- **No refresh tokens or revocation.** Tokens are stateless until they expire
  (30 minutes by default). Logout clears the client copy; it cannot invalidate
  an already-issued token server-side.
- **No rate limiting** on `/auth/login` or `/auth/register`. Login returns a
  uniform "Invalid email or password." so it does not reveal whether an account
  exists, but there is no throttling. Put a rate limiter at the proxy if the
  instance is publicly reachable.
- **No email verification or password reset.**
- **No CSRF tokens** — not needed while auth is a bearer header rather than a
  cookie.
- **The scheduler runs in-process.** There is no separate worker, so reminders
  are not delivered while the backend is down. They are delivered on restart.
- **Single database assumption.** Migrations and the app both target one
  PostgreSQL instance; there is no read-replica or sharding support.
