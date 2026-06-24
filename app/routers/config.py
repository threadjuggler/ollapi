"""Endpoints for reading/updating the model config and managing Ollama models."""

import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models import AppConfig
from ..ollama_client import ollama
from ..schemas import ConfigOut, ConfigUpdate, PullRequest, StatusOut

router = APIRouter(prefix="/api", tags=["config"])


async def _get_config(db: AsyncSession) -> AppConfig:
    cfg = (await db.execute(select(AppConfig).limit(1))).scalar_one_or_none()
    if cfg is None:
        raise HTTPException(status_code=500, detail="App config not initialised")
    return cfg


@router.get("/config", response_model=ConfigOut)
async def get_config(db: AsyncSession = Depends(get_db)):
    return await _get_config(db)


@router.put("/config", response_model=ConfigOut)
async def update_config(payload: ConfigUpdate, db: AsyncSession = Depends(get_db)):
    cfg = await _get_config(db)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(cfg, field, value)
    await db.commit()
    await db.refresh(cfg)
    return cfg


@router.get("/models")
async def list_models(db: AsyncSession = Depends(get_db)):
    cfg = await _get_config(db)
    try:
        available = await ollama.list_models()
        reachable = True
    except Exception:  # noqa: BLE001
        available = []
        reachable = False
    return {
        "current": cfg.model,
        "available": available,
        "ollama_reachable": reachable,
    }


@router.get("/status", response_model=StatusOut)
async def status(db: AsyncSession = Depends(get_db)):
    cfg = await _get_config(db)
    try:
        available = await ollama.list_models()
        reachable = True
    except Exception:  # noqa: BLE001
        available = []
        reachable = False
    wanted = cfg.model if ":" in cfg.model else f"{cfg.model}:latest"
    return StatusOut(
        ollama_reachable=reachable,
        model=cfg.model,
        model_ready=(wanted in available or cfg.model in available),
        available_models=available,
    )


@router.post("/models/pull")
async def pull_model(payload: PullRequest):
    model = payload.model.strip()
    if not model:
        raise HTTPException(status_code=400, detail="Model name required")

    async def generate():
        try:
            async for status_obj in ollama.pull_stream(model):
                yield f"data: {json.dumps(status_obj)}\n\n"
        except Exception as exc:  # noqa: BLE001
            yield f"data: {json.dumps({'error': str(exc)})}\n\n"
        yield f"data: {json.dumps({'status': 'success', 'done': True})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
