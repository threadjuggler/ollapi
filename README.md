# ollapi

A self-hosted web app for chatting with a **locally-run LLM** through
[Ollama](https://ollama.com). Clone the repo, run one command, open your browser,
and start chatting — **no API keys, no cloud, nothing leaves your machine.**

- 🧠 **Local LLM** via Ollama — default model `gemma4:e2b`, fully configurable
- ⚡ **FastAPI** backend that streams replies token-by-token (Server-Sent Events)
- 💬 **Chat UI** served straight from the app — no separate frontend to build
- 🗄️ **Postgres** keeps your conversations, messages, and live model settings
- 💾 **Save any answer to a file** with one click
- ⚙️ **Configure the model and its environment** from the UI (model, system
  prompt, temperature, top-p, context size, max tokens) and pull new models on demand
- 🐳 **One command** to start everything (app + Postgres + Ollama)

> **About the model:** the default `gemma4:e2b` is the Gemma 4 **E2B** tag on
> Ollama (~7.2 GB, 128K context, text + image input). You can change it any
> time — in `.env` before starting, or live from the in-app Settings panel.

---

## 1. What you need

| Requirement | Notes |
|-------------|-------|
| [Docker](https://docs.docker.com/get-docker/) | Docker Desktop (macOS/Windows) or Docker Engine (Linux) |
| Docker Compose v2 | Bundled with Docker Desktop; on Linux it's the `docker compose` plugin |
| ~8 GB free disk | For the default model download (varies by model) |
| Internet (first run only) | To pull the Docker images and the model. After that it runs offline. |

You do **not** need Python, Postgres, or Ollama installed on your host — they all
run in containers. (A no-Docker path is in [section 7](#7-running-without-docker-advanced).)

---

## 2. Run it (the easy way)

```bash
# 1. Get the code
git clone git@github.com:threadjuggler/ollapi.git
cd ollapi

# 2. (Optional) create your config from the template and edit if you like
cp .env.example .env

# 3. Start everything (app + Postgres + Ollama)
docker compose up --build
```

Then open **<http://localhost:8000>** in your browser.

That's it. Leave the terminal open (or add `-d` to run in the background:
`docker compose up --build -d`).

---

## 3. First run — what to expect

On the very first start the app will:

1. **Start Postgres** (published on host port **5431**) and apply database
   migrations automatically.
2. **Start Ollama** and **download the configured model** in the background.
   This is the slow part — `gemma4:e2b` is several GB, so depending on your
   connection it can take a few minutes.

The **status dot** in the bottom-left of the UI tells you what's happening:

| Dot | Meaning |
|-----|---------|
| 🔴 red | Ollama not reachable yet (still starting) |
| 🟠 amber | Model is downloading — *"Pulling …"* |
| 🟢 green | Model is ready — start chatting! |

Watch the download progress in the logs if you like:

```bash
docker compose logs -f app
```

Once the dot is green, type a message and press **Enter**. The reply streams in
live.

---

## 4. Using the app

- **Chat** — type in the box; **Enter** sends, **Shift+Enter** makes a new line.
- **Conversations** — every chat is saved to Postgres and listed in the left
  sidebar. Click one to reopen it; hover to delete it. Click **+ New** to start
  a fresh conversation.
- **💾 Save an answer** — hover over any assistant reply and click **Save** to
  download it as a Markdown (`.md`) file.
- **⚙️ Settings** — open the Settings panel (bottom-left) to:
  - switch the **model** (pick an installed one or type any Ollama tag),
  - **pull a new model** (e.g. `llama3.2:1b`, `qwen2.5:3b`) with live progress,
  - edit the **system prompt**,
  - tune **temperature**, **top-p**, **context size** (`num_ctx`), and
    **max tokens** (`num_predict`, `-1` = unlimited).

  Settings are stored in Postgres and applied to the next message.

---

## 5. Stopping, restarting, resetting

```bash
docker compose down          # stop containers, KEEP your data (chats + models)
docker compose up            # start again (no rebuild needed)
docker compose down -v       # stop AND erase all data (Postgres + downloaded models)
```

Your conversations live in the `pgdata` volume and downloaded models in the
`ollama` volume; both survive `down` and are only removed by `down -v`.

---

## Ports

| Service  | In container | On your machine | Notes |
|----------|--------------|-----------------|-------|
| app (web UI + API) | 8000 | **8000** | Change with `APP_PORT` in `.env` |
| Postgres | 5432 | **5431** | Deliberately **5431** to avoid clashing with other Postgres containers |
| Ollama   | 11434 | **11434** | Ollama's HTTP API |

Inside the Compose network the app talks to Postgres at `db:5432` and Ollama at
`ollama:11434`. The `5431` host mapping is only for connecting to the DB *from
your machine* (e.g. with `psql -h localhost -p 5431 -U ollapi`).

---

## 6. Configuration

Everything has sensible defaults. To override, copy `.env.example` to `.env` and
edit:

| Variable            | Default        | Description |
|---------------------|----------------|-------------|
| `OLLAMA_MODEL`      | `gemma4:e2b`  | Model tag to use and auto-download |
| `AUTO_PULL_MODEL`   | `true`         | Download the model automatically on first start |
| `APP_PORT`          | `8000`         | Host port for the web UI |
| `POSTGRES_USER`     | `ollapi`       | Database user |
| `POSTGRES_PASSWORD` | `REDACTED`       | Database password |
| `POSTGRES_DB`       | `ollapi`       | Database name |

Model behaviour (system prompt, temperature, top-p, context size, max tokens)
and the active model can also be changed **live in the UI** — see
[section 4](#4-using-the-app).

### GPU acceleration (optional)

Ollama runs CPU-only by default, which works everywhere but is slower. To use an
NVIDIA GPU, install the
[NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html)
and uncomment the `deploy:` block under the `ollama` service in
`docker-compose.yml`, then `docker compose up --build` again.

---

## 7. Running without Docker (advanced)

You'll need **Python 3.12+**, a running **Postgres**, and a running **Ollama**
on your host.

```bash
# 1. Install dependencies
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 2. Point the app at your services
export DATABASE_URL="postgresql+asyncpg://ollapi:REDACTED@localhost:5431/ollapi"
export OLLAMA_BASE_URL="http://localhost:11434"
export OLLAMA_MODEL="gemma4:e2b"

# 3. Create the database schema
alembic upgrade head

# 4. Make sure the model is available
ollama pull gemma4:e2b

# 5. Start the server
uvicorn app.main:app --reload
```

Open <http://localhost:8000>.

### Database migrations

The schema is managed by [Alembic](https://alembic.sqlalchemy.org/).

- **With Docker:** migrations run automatically on container start
  (`entrypoint.sh` runs `alembic upgrade head`, retrying while Postgres boots) —
  nothing to do.
- **Without Docker:** run `alembic upgrade head` before starting the server.
- **After changing a model** in `app/models.py`, create and apply a migration:
  ```bash
  alembic revision --autogenerate -m "describe your change"
  alembic upgrade head
  ```

Migration scripts live in `migrations/versions/`.

---

## 8. API reference

The backend exposes a small JSON/SSE API. Interactive docs are at
**<http://localhost:8000/docs>**.

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/chat` | Send a message; streams the reply (SSE) |
| `GET` | `/api/conversations` | List conversations |
| `POST` | `/api/conversations` | Create a conversation |
| `GET` | `/api/conversations/{id}` | Get a conversation with its messages |
| `PATCH` | `/api/conversations/{id}` | Rename a conversation |
| `DELETE` | `/api/conversations/{id}` | Delete a conversation |
| `GET` | `/api/config` | Get the current model configuration |
| `PUT` | `/api/config` | Update the model configuration |
| `GET` | `/api/models` | List models available in Ollama |
| `POST` | `/api/models/pull` | Pull a model (streams progress) |
| `GET` | `/api/status` | Ollama reachability + whether the model is ready |

---

## 9. Troubleshooting

**Port 8000 is already in use** — something else is bound to 8000. Set a
different host port in `.env`:
```bash
echo "APP_PORT=18080" >> .env
docker compose up
# then browse to http://localhost:18080
```

**Port 5431 is already in use** — another service grabbed it. Change the host
side of the mapping in `docker-compose.yml` (`"5431:5432"` → e.g. `"5433:5432"`).
The app itself is unaffected (it uses `db:5432` internally).

**The status dot stays amber for a long time** — the model is still downloading.
Check progress with `docker compose logs -f app`. Large models simply take a
while the first time; it's cached afterwards.

**The status dot is red / "Ollama offline"** — give the Ollama container a moment
to finish starting (`docker compose logs -f ollama`). If it persists, restart
with `docker compose restart ollama`.

**I want to start completely fresh** — wipe the database and downloaded models:
```bash
docker compose down -v
docker compose up --build
```

**Use a smaller / faster model** — set `OLLAMA_MODEL` in `.env` (e.g.
`llama3.2:1b` or `qwen2.5:0.5b`) before the first start, or pull and switch
models live from the Settings panel.

---

## Project layout

```
ollapi/
├── app/
│   ├── main.py            # FastAPI app, lifespan, automatic model pull
│   ├── config.py          # Settings (environment-driven)
│   ├── database.py        # Async SQLAlchemy engine / session factory
│   ├── models.py          # Conversation / Message / AppConfig ORM models
│   ├── schemas.py         # Pydantic request/response models
│   ├── ollama_client.py   # Async Ollama HTTP client
│   └── routers/           # chat, conversations, config endpoints
├── static/                # HTML/CSS/JS single-page chat UI
├── migrations/            # Alembic migrations (env.py, versions/)
├── alembic.ini            # Alembic config
├── entrypoint.sh          # Container start: run migrations, then the server
├── Dockerfile
├── docker-compose.yml     # app + Postgres (host 5431) + Ollama
└── requirements.txt
```

## License

MIT
