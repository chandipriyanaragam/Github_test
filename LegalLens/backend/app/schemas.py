from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


Workflow = Literal["ask", "draft", "summary"]


class ConversationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str | None = Field(default=None, min_length=1, max_length=200)


class ConversationPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str | None = Field(default=None, min_length=1, max_length=200)
    jurisdiction: str | None = Field(default=None, max_length=120)


class ConversationSummary(BaseModel):
    id: str
    title: str
    jurisdiction: str | None
    created_at: datetime
    updated_at: datetime
    document_ids: list[str]
    message_count: int


class CitationOut(BaseModel):
    id: str
    document_id: str
    filename: str
    page: int | None
    excerpt: str
    source_number: int


class MessageOut(BaseModel):
    id: str
    role: Literal["user", "assistant"]
    content: str
    workflow: Workflow | None
    created_at: datetime
    citations: list[CitationOut] = Field(default_factory=list)


class ConversationDetail(ConversationSummary):
    messages: list[MessageOut]


class ConversationPage(BaseModel):
    items: list[ConversationSummary]
    next_cursor: str | None


class TurnMessageIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    content: str = Field(min_length=1, max_length=20000)
    workflow: Workflow
    jurisdiction: str | None = Field(default=None, max_length=120)
    document_ids: list[str] = Field(default_factory=list, max_length=10)


class TurnCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    conversation_id: str | None = None
    message: TurnMessageIn


class TurnResponse(BaseModel):
    turn_id: str
    conversation_id: str
    user_message: MessageOut
    status: Literal["completed", "failed"]
    assistant_message: MessageOut | None = None


class DocumentOut(BaseModel):
    id: str
    filename: str
    media_type: str
    size_bytes: int
    status: Literal["awaiting_processing", "ready", "failed", "deleted"]
    conversation_id: str | None
    created_at: datetime


class DocumentStatus(DocumentOut):
    detail: str | None = None


class HealthResponse(BaseModel):
    status: str


class ReadinessResponse(BaseModel):
    status: str
    dependencies: dict[str, str]


class ErrorDetail(BaseModel):
    code: str
    message: str
    request_id: str | None = None
    details: list[dict[str, str]] = Field(default_factory=list)


class ErrorResponse(BaseModel):
    error: ErrorDetail
