import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from call_analyzer.app import create_app
from call_analyzer.models import AnalysisResult, Call, ProfileResult


@pytest.fixture
def app():
    with patch("call_analyzer.app.worker_loop", new_callable=AsyncMock):
        yield create_app()


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


def make_call(**kwargs) -> Call:
    defaults = {
        "id": uuid.uuid4(),
        "filename": "test.wav",
        "audio_format": "wav",
        "source": "api",
        "status": "pending",
        "created_at": datetime.now(UTC).replace(tzinfo=None),
    }
    defaults.update(kwargs)
    return Call(**defaults)


def make_analysis_result(call_id: uuid.UUID, **kwargs) -> AnalysisResult:
    defaults = {
        "id": uuid.uuid4(),
        "call_id": call_id,
        "transcript": "Test transcript",
        "is_fraud": False,
        "fraud_score": 0.1,
        "fraud_categories": [],
        "reasons": [],
        "raw_response": {},
        "analyzed_at": datetime.now(UTC).replace(tzinfo=None),
    }
    defaults.update(kwargs)
    return AnalysisResult(**defaults)


def make_gemini_response(text: str) -> dict:
    return {
        "candidates": [
            {
                "content": {
                    "parts": [{"text": text}]
                }
            }
        ]
    }
