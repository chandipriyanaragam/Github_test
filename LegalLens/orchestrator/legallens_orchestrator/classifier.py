"""Classify a user message into one of LegalLens' three workflows."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field


PROMPT_PATH = Path(__file__).resolve().parents[1] / "intent-classification.prompt.md"


class IntentClassification(BaseModel):
    """Small, validated result from the intent classifier."""

    intent: Literal["ask", "draft", "summarize"] = Field(
        description="The single best matching LegalLens workflow."
    )
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str = Field(
        min_length=1,
        max_length=240,
        description="Brief explanation grounded in the user's requested action.",
    )


@lru_cache(maxsize=1)
def _classifier_chain():
    # The orchestrator owns its local environment; importing it does not load
    # or initialize the backend.
    load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=False)
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is missing. Add your key to LegalLens/orchestrator/.env."
        )

    model_name = os.getenv("OPENAI_MODEL", "gpt-6-luna").strip()
    prompt = ChatPromptTemplate.from_messages(
        [("system", "{classification_guidance}"), ("human", "{message}")]
    )
    model = init_chat_model(
        model_name,
        model_provider="openai",
        temperature=0,
        api_key=api_key,
    )
    return prompt | model.with_structured_output(IntentClassification)


def classify_intent(message: str) -> IntentClassification:
    """Classify one user message as ask, draft, or summarize.

    Raises ValueError for empty input and RuntimeError when local credentials
    are missing. Provider/network/model errors are surfaced to the caller.
    """
    if not isinstance(message, str) or not message.strip():
        raise ValueError("message must be a non-empty string")
    return _classifier_chain().invoke(
        {"classification_guidance": PROMPT_PATH.read_text(encoding="utf-8"), "message": message.strip()}
    )
