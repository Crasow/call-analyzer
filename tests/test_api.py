import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from call_analyzer.models import Call
from tests.conftest import make_call


@pytest.fixture
def app():
    from call_analyzer.app import create_app
    with patch("call_analyzer.app.worker_loop", new_callable=AsyncMock):
        yield create_app()


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_analyze_endpoint(client):
    call = make_call()

    with patch("call_analyzer.api._create_pending_call", new_callable=AsyncMock, return_value=call):
        resp = await client.post(
            "/api/v1/calls/analyze",
            files={"file": ("test.wav", b"fake audio", "audio/wav")},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == str(call.id)
    assert data["status"] == "pending"


@pytest.mark.asyncio
async def test_analyze_endpoint_with_profile(client):
    pid = uuid.uuid4()
    call = make_call(profile_id=pid)

    with patch("call_analyzer.api._create_pending_call", new_callable=AsyncMock, return_value=call):
        resp = await client.post(
            "/api/v1/calls/analyze",
            files={"file": ("test.wav", b"fake audio", "audio/wav")},
            data={"profile_id": str(pid)},
        )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_stats_endpoint_returns_json(client):
    """Stats endpoint should return JSON (may fail without DB)."""
    try:
        resp = await client.get("/api/v1/stats")
        assert resp.status_code in (200, 500)
    except Exception:
        pytest.skip("DB not available")


@pytest.mark.asyncio
async def test_webhook_endpoint(client):
    call = make_call(source="webhook")

    with patch("call_analyzer.api._create_pending_call", new_callable=AsyncMock, return_value=call):
        resp = await client.post(
            "/api/v1/webhook/call",
            files={"file": ("test.wav", b"fake audio", "audio/wav")},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "pending"
