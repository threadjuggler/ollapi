# ollapi

A self-hosted web app for chatting with a **locally-run LLM** via [Ollama](https://ollama.com).
Clone the repo, run one command, open your browser, and start chatting — no data
leaves your machine.

- 🧠 **Local LLM** through Ollama (default model: `gemma3n:e2b`, fully configurable)
- ⚡ **FastAPI** backend with streaming responses (Server-Sent Events)
- 💬 **Chat UI** served straight from the app — no separate frontend build
- 🗄️ **Postgres** stores your conversations and live model configuration
- 💾 **Save answers to a file** with one click
- ⚙️ **Configure the model and its environment** from the UI (model, system
  prompt, temperature, top-p, context size, max tokens) and pull new models on demand
- 🐳 **One-command Docker setup** (app + Postgres + Ollama)

> The default model `gemma3n:e2b` is the Gemma 3n **E2B** tag on Ollama (this is
> what was meant by "gemma:e2b"). Change it any time in `.env` or the Settings panel.

---

## Quick start

Requirements: [Docker](https://docs.docker.com/get-docker/) and Docker Compose.

```bash
git clone https://github.com/<your-user>/ollapi.git
cd ollapi
cp .env.example .env        # optional: tweak the model, ports, credentials
docker compose up --build
```

Then open **http://localhost:8000**.

On first launch the app waits for Ollama and automatically pulls the configured
model. This can take a few minutes depending on model size and your connection —
the status dot in the bottom-left of the UI turns **green** once the model is
ready. (Watch progress with `docker compose logs -f app`.)

To stop:

```bash
docker compose down          # keeps your data
docker compose down -v       # also wipes the Postgres + Ollama volumes
```

---

## Ports

| Service  | Container | Host        | Notes                                            |
|----------|-----------|-------------|--------------------------------------------------|
| app      | 8000      | `8000`      | Web UI + API (`APP_PORT` to change)              |
| Postgres | 5432      | **`5431`**  | Published on **5431** to avoid clashing with other Postgres containers on this machine |
| Ollama   | 11434     | `11434`     | Ollama HTTP API                                  |

Inside the Compose network the app reaches Postgres at `db:5432` and Ollama at
`ollama:11434`; the `5431` mapping is only for connecting from the host.

---

## Configuration

All settings have sensible defaults; override them in `.env` (see `.env.example`):

| Variable           | Default        | Description                                       |
|--------------------|----------------|---------------------------------------------------|
| `OLLAMA_MODEL`     | `gemma3n:e2b`  | Model tag to use / auto-pull                       |
| `AUTO_PULL_MODEL`  | `true`         | Pull the model automatically on first startup      |
| `APP_PORT`         | `8000`         | Host port for the web UI                           |
| `POSTGRES_USER`    | `ollapi`       | Database user                                      |
| `POSTGRES_PASSWORD`| `REDACTED`       | Database password                                  |
| `POSTGRES_DB`      | `ollapi`       | Database name                                      |

Generation parameters (system prompt, temperature, top-p, context size, max
tokens) and the active model can also be changed **live from the Settings panel**
in the UI — they are stored in Postgres.

### GPU acceleration

Ollama runs CPU-only by default. To use an NVIDIA GPU, install the
[NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html)
and uncomment the `deploy:` block under the `ollama` service in
`docker-compose.yml`.

---

## API

The backend exposes a small JSON/SSE API (interactive docs at
`http://localhost:8000/docs`):

| Method   | Path                          | Description                                  |
|----------|-------------------------------|----------------------------------------------|
| `POST`   | `/api/chat`                   | Send a message; streams the reply (SSE)      |
| `GET`    | `/api/conversations`          | List conversations                           |
| `POST`   | `/api/conversations`          | Create a conversation                        |
| `GET`    | `/api/conversations/{id}`     | Get a conversation with its messages         |
| `PATCH`  | `/api/conversations/{id}`     | Rename a conversation                        |
| `DELETE` | `/api/conversations/{id}`     | Delete a conversation                        |
| `GET`    | `/api/config`                 | Get the current model configuration          |
| `PUT`    | `/api/config`                 | Update the model configuration               |
| `GET`    | `/api/models`                 | List models available in Ollama              |
| `POST`   | `/api/models/pull`            | Pull a model (streams progress)              |
| `GET`    | `/api/status`                 | Ollama reachability + whether model is ready |

---

## Local development (without Docker)

You'll need Python 3.12+, a running Postgres, and a running Ollama.

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

export DATABASE_URL="postgresql+asyncpg://ollapi:REDACTED@localhost:5431/ollapi"
export OLLAMA_BASE_URL="http://localhost:11434"
export OLLAMA_MODEL="gemma3n:e2b"

uvicorn app.main:app --reload
```

### Database migrations

Schema is managed by [Alembic](https://alembic.sqlalchemy.org/). Migrations run
automatically on container start via `entrypoint.sh` (with retry logic while
Postgres finishes starting up), so no manual step is needed when using Docker.

For local development, apply migrations before starting the server:

```bash
alembic upgrade head
```

After changing a model in `app/models.py`, generate a new migration and apply it:

```bash
alembic revision --autogenerate -m "describe change"
alembic upgrade head
```

Migration scripts live in `migrations/versions/`.

---

## Project layout

```
ollapi/
├── app/
│   ├── main.py            # FastAPI app, lifespan, model auto-pull
│   ├── config.py          # Settings (env-driven)
│   ├── database.py        # Async SQLAlchemy engine/session
│   ├── models.py          # Conversation / Message / AppConfig
│   ├── schemas.py         # Pydantic request/response models
│   ├── ollama_client.py   # Async Ollama HTTP client
│   └── routers/           # chat, conversations, config endpoints
├── static/                # HTML/CSS/JS single-page chat UI
├── Dockerfile
├── docker-compose.yml     # app + Postgres (host 5431) + Ollama
└── requirements.txt
```

## License

MIT