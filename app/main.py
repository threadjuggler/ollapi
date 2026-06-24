"""ollapi FastAPI application entrypoint."""

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select

from .config import settings
from .database import SessionLocal, engine
from .models import AppConfig
from .ollama_client import ollama
from .routers import chat, config as config_router, conversations

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("ollapi")

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


async def _ensure_config() -> None:
    """Make sure exactly one editable config row exists."""
    async with SessionLocal() as session:
        cfg = (await session.execute(select(AppConfig).limit(1))).scalar_one_or_none()
        if cfg is None:
            session.add(
                AppConfig(
                    model=settings.ollama_model,
                    system_prompt=settings.default_system_prompt,
                    temperature=settings.default_temperature,
                    top_p=settings.default_top_p,
                    num_ctx=settings.default_num_ctx,
                    num_predict=settings.default_num_predict,
                )
            )
            await session.commit()
            logger.info("Initialised app config with model %s", settings.ollama_model)


async def _wait_for_ollama(retries: int = 60, delay: float = 3.0) -> bool:
    for _ in range(retries):
        try:
            await ollama.list_models()
            return True
        except Exception:  # noqa: BLE001
            await asyncio.sleep(delay)
    return False


async def _ensure_model() -> None:
    """Background task: pull the configured model on first run if it's missing."""
    if not await _wait_for_ollama():
        logger.warning("Ollama not reachable; skipping automatic model pull.")
        return

    async with SessionLocal() as session:
        cfg = (await session.execute(select(AppConfig).limit(1))).scalar_one_or_none()
    model = cfg.model if cfg else settings.ollama_model

    if await ollama.has_model(model):
        logger.info("Model %s already available.", model)
        return

    logger.info("Pulling model %s (this can take a while on first run)...", model)
    last_status = None
    try:
        async for update in ollama.pull_stream(model):
            status = update.get("status")
            if status and status != last_status:
                logger.info("  ollama pull: %s", status)
                last_status = status
        logger.info("Model %s is ready.", model)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to pull model %s: %s", model, exc)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await _ensure_config()
    if settings.auto_pull_model:
        asyncio.create_task(_ensure_model())
    yield
    await engine.dispose()


app = FastAPI(title="ollapi", version="0.1.0", lifespan=lifespan)

app.include_router(chat.router)
app.include_router(conversations.router)
app.include_router(config_router.router)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)
async def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/healthz", include_in_schema=False)
async def healthz():
    return {"status": "ok"}
