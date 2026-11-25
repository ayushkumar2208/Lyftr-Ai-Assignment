from typing import Literal

from pydantic import BaseModel, Field, field_validator


class ChatRequest(BaseModel):
    session_id: str = Field(
        ...,
        min_length=1,
        max_length=128,
    )

    message: str = Field(
        ...,
        min_length=1,
        max_length=4000,
    )

    system_prompt: str | None = None

    @field_validator("session_id", "message")
    @classmethod
    def validate_not_blank(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("must not be empty")

        return value


class ResponseMetadata(BaseModel):
    resolution_source: Literal[
        "LIVE_INFERENCE",
        "LLM_CACHE",
    ]

    model: str
    latency_ms: int = Field(..., ge=0)
    input_tokens: int = Field(..., ge=0)
    output_tokens: int = Field(..., ge=0)

    key_id: str | None = None

    fallback_attempts: int = Field(
        ...,
        ge=0,
    )


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    metadata: ResponseMetadata


class HistoryMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str
    metadata: ResponseMetadata | None = None


class SessionHistoryResponse(BaseModel):
    session_id: str
    messages: list[HistoryMessage]


class HealthResponse(BaseModel):
    status: Literal["ok"]
    keys_configured: int
    cache_enabled: bool