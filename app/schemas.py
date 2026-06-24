"""Pydantic request/response models."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[int] = None


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    role: str
    content: str
    created_at: datetime


class ConversationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    created_at: datetime


class ConversationDetail(ConversationOut):
    messages: list[MessageOut] = []


class ConversationCreate(BaseModel):
    title: str = "New conversation"


class ConversationUpdate(BaseModel):
    title: str


class ConfigOut(BaseModel):
    # protected_namespaces=() lets us use the field name "model" without warnings.
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

    model: str
    system_prompt: str
    temperature: float
    top_p: float
    num_ctx: int
    num_predict: int


class ConfigUpdate(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    model: Optional[str] = None
    system_prompt: Optional[str] = None
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    num_ctx: Optional[int] = None
    num_predict: Optional[int] = None


class PullRequest(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    model: str


class StatusOut(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    ollama_reachable: bool
    model: str
    model_ready: bool
    available_models: list[str] = []
