import asyncio
from unittest.mock import AsyncMock, patch, MagicMock

import httpx
import pytest

from call_analyzer.gemini_client import generate_content


@pytest.mark.asyncio
async def test_retry_on_500():
    """Should retry on 500 status codes."""
    responses = [
        httpx.Response(500, request=httpx.Request("POST", "http://test")),
        httpx.Response(200, json={"candidates": []}, request=httpx.Request("POST", "http://test")),
    ]
    call_count = 0

    async def mock_post(url, **kwargs):
        nonlocal call_count
        resp = responses[call_count]
        call_count += 1
        return resp

    with patch("call_analyzer.gemini_client.settings") as mock_settings, \
         patch("call_analyzer.gemini_client.asyncio.sleep", new_callable=AsyncMock):
        mock_settings.gemini_proxy_url = "http://test"
        mock_settings.gemini_project_id = "proj"
        mock_settings.gemini_location = "us"
        mock_settings.gemini_model = "model"
        mock_settings.gemini_read_timeout = 10
        mock_settings.gemini_max_retries = 3

        with patch("httpx.AsyncClient") as MockClient:
            client_instance = AsyncMock()
            client_instance.post = mock_post
            MockClient.return_value.__aenter__ = AsyncMock(return_value=client_instance)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await generate_content("base64data", "audio/wav", "prompt")

    assert result == {"candidates": []}
    assert call_count == 2


@pytest.mark.asyncio
async def test_no_retry_on_400():
    """Should NOT retry on 400 status codes."""
    resp = httpx.Response(400, text="Bad request", request=httpx.Request("POST", "http://test"))

    with patch("call_analyzer.gemini_client.settings") as mock_settings, \
         patch("call_analyzer.gemini_client.asyncio.sleep", new_callable=AsyncMock):
        mock_settings.gemini_proxy_url = "http://test"
        mock_settings.gemini_project_id = "proj"
        mock_settings.gemini_location = "us"
        mock_settings.gemini_model = "model"
        mock_settings.gemini_read_timeout = 10
        mock_settings.gemini_max_retries = 3

        with patch("httpx.AsyncClient") as MockClient:
            client_instance = AsyncMock()
            client_instance.post = AsyncMock(return_value=resp)
            MockClient.return_value.__aenter__ = AsyncMock(return_value=client_instance)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            with pytest.raises(RuntimeError, match="400"):
                await generate_content("base64data", "audio/wav", "prompt")
