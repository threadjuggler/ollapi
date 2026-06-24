"""CRUD endpoints for conversations and their messages."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models import Conversation
from ..schemas import (
    ConversationCreate,
    ConversationDetail,
    ConversationOut,
    ConversationUpdate,
)

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


@router.get("", response_model=list[ConversationOut])
async def list_conversations(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Conversation).order_by(Conversation.created_at.desc())
    )
    return result.scalars().all()


@router.post("", response_model=ConversationDetail, status_code=201)
async def create_conversation(
    payload: ConversationCreate, db: AsyncSession = Depends(get_db)
):
    conv = Conversation(title=payload.title or "New conversation")
    db.add(conv)
    await db.commit()
    await db.refresh(conv)
    return ConversationDetail(
        id=conv.id, title=conv.title, created_at=conv.created_at, messages=[]
    )


async def _get_or_404(conv_id: int, db: AsyncSession) -> Conversation:
    conv = await db.get(Conversation, conv_id)
    if conv is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conv


@router.get("/{conv_id}", response_model=ConversationDetail)
async def get_conversation(conv_id: int, db: AsyncSession = Depends(get_db)):
    conv = await _get_or_404(conv_id, db)
    await db.refresh(conv, attribute_names=["messages"])
    return conv


@router.patch("/{conv_id}", response_model=ConversationOut)
async def rename_conversation(
    conv_id: int, payload: ConversationUpdate, db: AsyncSession = Depends(get_db)
):
    conv = await _get_or_404(conv_id, db)
    conv.title = payload.title
    await db.commit()
    await db.refresh(conv)
    return conv


@router.delete("/{conv_id}", status_code=204)
async def delete_conversation(conv_id: int, db: AsyncSession = Depends(get_db)):
    conv = await _get_or_404(conv_id, db)
    await db.delete(conv)
    await db.commit()
