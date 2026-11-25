import pytest
from httpx import ASGITransport, AsyncClient

from backend.app.main import app


@pytest.mark.asyncio
async def test_health_endpoint():
    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.get("/health")

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "ok"
    assert data["keys_configured"] >= 2
    assert data["cache_enabled"] is True


@pytest.mark.asyncio
async def test_chat_rejects_empty_message():
    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/chat",
            json={
                "session_id": "test-session",
                "message": "",
            },
        )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_chat_rejects_blank_message():
    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/chat",
            json={
                "session_id": "test-session",
                "message": "     ",
            },
        )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_chat_rejects_missing_session_id():
    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/chat",
            json={
                "message": "Hello",
            },
        )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_chat_rejects_message_over_4000_characters():
    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/chat",
            json={
                "session_id": "test-session",
                "message": "a" * 4001,
            },
        )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_unknown_session_returns_404():
    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.get(
            "/sessions/session-that-does-not-exist/messages"
        )

    assert response.status_code == 404
    assert response.json() == {
        "detail": "session not found"
    }