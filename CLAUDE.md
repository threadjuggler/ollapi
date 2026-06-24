# CLAUDE.md

Guidance for Claude Code when working in this repository.

## Agent / model workflow

When carrying out work in this repo, follow this division of labor by model:

1. **Plan with Opus.** The Opus agent is responsible for planning — analyzing the
   task, designing the approach, and breaking work into steps.
2. **Implement with Sonnet.** For the implementation itself, always spawn a
   **Sonnet** agent to write/modify the code. Opus does not implement directly;
   it delegates implementation to a Sonnet subagent.
3. **Verify with Opus.** After implementation, the Opus agent verifies the
   result (reviews the diff, runs/tests the app, confirms it does what was asked).

In short: **Opus plans and verifies; Sonnet implements.**

## Ask when unclear

**Always ask the user for clarification when something is not clear** — an
ambiguous requirement, an unstated assumption, multiple reasonable
interpretations, or a decision with meaningful trade-offs. Prefer a short
clarifying question over guessing; only proceed on an assumption when the choice
is low-risk and easily reversible, and say which assumption you made.

## Project overview

`ollapi` is a self-hosted web app for chatting with a locally-run LLM via
[Ollama](https://ollama.com). Users clone the repo, run `docker compose up`, open
`http://localhost:8000`, and chat with the configured model.

- **Backend:** FastAPI (async), streaming chat responses over Server-Sent Events.
- **Frontend:** Static HTML/CSS/JS single-page app served by FastAPI from `static/`.
- **Database:** Postgres (async SQLAlchemy + asyncpg) stores conversations,
  messages, and the live model configuration.
- **LLM:** Ollama, default model `gemma4:e2b` (configurable via `OLLAMA_MODEL`
  or the in-app Settings panel).

## Layout

- `app/main.py` — FastAPI app, lifespan, model auto-pull on first run
- `app/config.py` — env-driven settings (`pydantic-settings`)
- `app/database.py` — async engine/session factory (`get_db` dependency)
- `app/models.py` — `Conversation`, `Message`, `AppConfig` ORM models
- `app/schemas.py` — Pydantic request/response models
- `app/ollama_client.py` — async Ollama HTTP client (chat/pull/list)
- `app/routers/` — `chat`, `conversations`, `config` route modules
- `static/` — `index.html`, `style.css`, `app.js`
- `migrations/` — Alembic migration scripts (`env.py`, `versions/`)
- `alembic.ini` — Alembic config (`script_location = migrations`; URL set at runtime by `env.py`)
- `entrypoint.sh` — container entrypoint: runs migrations then starts uvicorn

## Conventions & gotchas

- **Postgres host port is 5431** (mapped to container 5432) to avoid clashing
  with other Postgres containers on this machine. Inside the compose network the
  app connects to `db:5432`.
- **Schema is managed by Alembic** — `Base.metadata.create_all` is no longer
  called anywhere. Migration scripts live in `migrations/versions/`. The
  container entrypoint (`entrypoint.sh`) runs `alembic upgrade head` (with
  retry) before starting the server. For local dev, run `alembic upgrade head`
  manually before starting uvicorn.
- After changing a model in `app/models.py`, generate and apply a migration:
  ```bash
  alembic revision --autogenerate -m "describe change"
  alembic upgrade head
  ```
- The chat endpoint builds the prompt and commits the user message *before*
  returning the `StreamingResponse`, then persists the assistant reply from a
  **fresh** `SessionLocal()` inside the generator (the request-scoped session is
  already closed once streaming starts).
- Pydantic schemas that expose a field named `model` set
  `ConfigDict(protected_namespaces=())` to avoid namespace warnings.
- Model config is a single editable row (`app_config`) seeded from env defaults
  on first startup; it can be changed live from the UI.

## Run / verify

```bash
docker compose up --build           # full stack (app + Postgres@5431 + Ollama)
# UI: http://localhost:8000   API docs: http://localhost:8000/docs
```

Lightweight checks without the heavy Ollama model download:

```bash
python -m py_compile app/*.py app/routers/*.py    # syntax
docker compose config --quiet                     # validate compose
# DB + API only (skip Ollama, skip model pull):
docker compose up -d db
AUTO_PULL_MODEL=false docker compose up -d --no-deps app
```

On container start, `entrypoint.sh` runs `alembic upgrade head` (retrying up to
10 times while Postgres starts), then hands off to uvicorn. Migration output
appears in `docker compose logs app`.
