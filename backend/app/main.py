import json
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .config import settings
from .database import engine, get_db, init_db
from .llm import generate_response
from .models import Message
from .schemas import (
    ChatRequest,
    ChatResponse,
    HealthResponse,
    HistoryMessage,
    ResponseMetadata,
    SessionHistoryResponse,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Automatically create the SQLite schema on startup.
    await init_db()
    yield
    await engine.dispose()


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    lifespan=lifespan,
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get(
    "/health",
    response_model=HealthResponse,
)
async def health(
    db: AsyncSession = Depends(get_db),
) -> HealthResponse:
    try:
        await db.execute(select(1))
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail="database unavailable",
        ) from exc

    if len(settings.api_keys) < 2:
        raise HTTPException(
            status_code=503,
            detail="key pool not configured",
        )

    return HealthResponse(
        status="ok",
        keys_configured=len(settings.api_keys),
        cache_enabled=True,
    )


@app.post(
    "/chat",
    response_model=ChatResponse,
)
async def chat(
    payload: ChatRequest,
    db: AsyncSession = Depends(get_db),
    x_simulate_failure: str | None = Header(
        default=None,
        alias="X-Simulate-Failure",
    ),
) -> ChatResponse:
    # Load existing session history from SQLite.
    result = await db.execute(
        select(Message)
        .where(Message.session_id == payload.session_id)
        .order_by(Message.id.asc())
    )

    stored_messages = result.scalars().all()

    # Build the exact message list that will be sent to the LLM.
    messages: list[dict[str, str]] = []

    system_prompt = (
        payload.system_prompt
        if payload.system_prompt is not None
        else settings.default_system_prompt
    )

    if system_prompt:
        messages.append(
            {
                "role": "system",
                "content": system_prompt,
            }
        )

    for stored_message in stored_messages:
        messages.append(
            {
                "role": stored_message.role,
                "content": stored_message.content,
            }
        )

    messages.append(
        {
            "role": "user",
            "content": payload.message,
        }
    )

    # Call LiteLLM before storing anything.
    # Failed requests must never be written to history.
    try:
        llm_result = await generate_response(
            messages=messages,
            simulate_failure_header=x_simulate_failure,
        )

    except RuntimeError as exc:
        if str(exc) == "all providers unavailable":
            raise HTTPException(
                status_code=503,
                detail="all providers unavailable",
            ) from exc

        raise HTTPException(
            status_code=503,
            detail="LLM service unavailable",
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail="LLM service unavailable",
        ) from exc

    metadata = ResponseMetadata(
        resolution_source=llm_result.resolution_source,
        model=llm_result.model,
        latency_ms=llm_result.latency_ms,
        input_tokens=llm_result.input_tokens,
        output_tokens=llm_result.output_tokens,
        key_id=llm_result.key_id,
        fallback_attempts=llm_result.fallback_attempts,
    )

    # Only successful requests are added to SQLite.
    user_message = Message(
        session_id=payload.session_id,
        role="user",
        content=payload.message,
    )

    assistant_message = Message(
        session_id=payload.session_id,
        role="assistant",
        content=llm_result.reply,
        metadata_json=json.dumps(
            metadata.model_dump(),
            ensure_ascii=False,
        ),
    )

    db.add_all(
        [
            user_message,
            assistant_message,
        ]
    )

    try:
        await db.commit()

    except Exception as exc:
        await db.rollback()

        raise HTTPException(
            status_code=503,
            detail="database unavailable",
        ) from exc

    return ChatResponse(
        session_id=payload.session_id,
        reply=llm_result.reply,
        metadata=metadata,
    )


@app.get(
    "/sessions/{session_id}/messages",
    response_model=SessionHistoryResponse,
)
async def get_session_messages(
    session_id: str,
    db: AsyncSession = Depends(get_db),
) -> SessionHistoryResponse:
    result = await db.execute(
        select(Message)
        .where(Message.session_id == session_id)
        .order_by(Message.id.asc())
    )

    stored_messages = result.scalars().all()

    if not stored_messages:
        raise HTTPException(
            status_code=404,
            detail="session not found",
        )

    messages: list[HistoryMessage] = []

    for stored_message in stored_messages:
        metadata = None

        if (
            stored_message.role == "assistant"
            and stored_message.metadata_json
        ):
            try:
                metadata_data = json.loads(
                    stored_message.metadata_json
                )

                metadata = ResponseMetadata(
                    **metadata_data
                )

            except (
                json.JSONDecodeError,
                TypeError,
                ValueError,
            ):
                metadata = None

        messages.append(
            HistoryMessage(
                role=stored_message.role,
                content=stored_message.content,
                metadata=metadata,
            )
        )

    return SessionHistoryResponse(
        session_id=session_id,
        messages=messages,
    )