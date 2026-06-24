"""Chat endpoint: streams the model response back as Server-Sent Events."""

import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import SessionLocal, get_db
from ..models import AppConfig, Conversation, Message
from ..ollama_client import ollama
from ..schemas import ChatRequest

logger = logging.getLogger("ollapi.chat")
router = APIRouter(prefix="/api", tags=["chat"])


def _sse(obj: dict) -> str:
    return f"data: {json.dumps(obj)}\n\n"


async def _load_config(db: AsyncSession) -> AppConfig:
    cfg = (await db.execute(select(AppConfig).limit(1))).scalar_one_or_none()
    if cfg is None:
        raise HTTPException(status_code=500, detail="App config not initialised")
    return cfg


@router.post("/chat")
async def chat(req: ChatRequest, db: AsyncSession = Depends(get_db)):
    message = req.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="Message must not be empty")

    cfg = await _load_config(db)

    # Resolve / create the conversation.
    if req.conversation_id is not None:
        conv = await db.get(Conversation, req.conversation_id)
        if conv is None:
            raise HTTPException(status_code=404, detail="Conversation not found")
    else:
        conv = Conversation(title=message[:60])
        db.add(conv)
        await db.flush()

    db.add(Message(conversation_id=conv.id, role="user", content=message))
    await db.commit()
    conv_id = conv.id

    # Build the prompt (system prompt + full history) before streaming starts,
    # because the request-scoped session is closed once we return the response.
    history = (
        (
            await db.execute(
                select(Message)
                .where(Message.conversation_id == conv_id)
                .order_by(Message.id)
            )
        )
        .scalars()
        .all()
    )
    messages = [{"role": "system", "content": cfg.system_prompt}]
    messages += [{"role": m.role, "content": m.content} for m in history]

    model = cfg.model
    options = {
        "temperature": cfg.temperature,
        "top_p": cfg.top_p,
        "num_ctx": cfg.num_ctx,
        "num_predict": cfg.num_predict,
    }

    async def generate():
        yield _sse({"type": "meta", "conversation_id": conv_id})
        chunks: list[str] = []
        try:
            async for chunk in ollama.chat_stream(model, messages, options):
                token = chunk.get("message", {}).get("content", "")
                if token:
                    chunks.append(token)
                    yield _sse({"type": "token", "content": token})
                if chunk.get("done"):
                    break
        except Exception as exc:  # noqa: BLE001
            logger.exception("Chat streaming failed")
            yield _sse({"type": "error", "error": str(exc)})

        answer = "".join(chunks)
        if answer:
            # Persist the assistant turn using a fresh session.
            async with SessionLocal() as session:
                session.add(
                    Message(conversation_id=conv_id, role="assistant", content=answer)
                )
                await session.commit()
        yield _sse({"type": "done", "conversation_id": conv_id})

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
