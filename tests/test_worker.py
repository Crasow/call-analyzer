import asyncio
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from call_analyzer.worker import process_call


@pytest.mark.asyncio
async def test_process_call_success():
    call_id = uuid.uuid4()
    semaphore = asyncio.Semaphore(1)

    mock_call = MagicMock()
    mock_call.profile = None

    mock_result = MagicMock()
    mock_result.is_fraud = False

    mock_session = AsyncMock()
    execute_result = MagicMock()
    execute_result.scalar_one = MagicMock(return_value=mock_call)
    mock_session.execute = AsyncMock(return_value=execute_result)

    with patch("call_analyzer.worker.async_session") as mock_as, \
         patch("call_analyzer.worker.analyze_call", new_callable=AsyncMock, return_value=mock_result):
        mock_as.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_as.return_value.__aexit__ = AsyncMock(return_value=False)

        await process_call(call_id, semaphore)

    # Should have committed twice: once for processing status, once for done status
    assert mock_session.commit.await_count == 2


@pytest.mark.asyncio
async def test_process_call_fraud_sends_alert():
    call_id = uuid.uuid4()
    semaphore = asyncio.Semaphore(1)

    mock_call = MagicMock()
    mock_call.profile = None

    mock_result = MagicMock()
    mock_result.is_fraud = True

    mock_session = AsyncMock()
    execute_result = MagicMock()
    execute_result.scalar_one = MagicMock(return_value=mock_call)
    mock_session.execute = AsyncMock(return_value=execute_result)

    with patch("call_analyzer.worker.async_session") as mock_as, \
         patch("call_analyzer.worker.analyze_call", new_callable=AsyncMock, return_value=mock_result), \
         patch("call_analyzer.worker.send_fraud_alert", new_callable=AsyncMock) as mock_alert:
        mock_as.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_as.return_value.__aexit__ = AsyncMock(return_value=False)

        await process_call(call_id, semaphore)

    mock_alert.assert_awaited_once_with(mock_call, mock_result)


@pytest.mark.asyncio
async def test_process_call_error_sets_error_status():
    call_id = uuid.uuid4()
    semaphore = asyncio.Semaphore(1)

    mock_call = MagicMock()
    mock_session = AsyncMock()
    execute_result = MagicMock()
    execute_result.scalar_one = MagicMock(return_value=mock_call)
    mock_session.execute = AsyncMock(return_value=execute_result)

    with patch("call_analyzer.worker.async_session") as mock_as, \
         patch("call_analyzer.worker.analyze_call", new_callable=AsyncMock, side_effect=RuntimeError("fail")):
        mock_as.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_as.return_value.__aexit__ = AsyncMock(return_value=False)

        await process_call(call_id, semaphore)

    # Should rollback and then commit error status
    mock_session.rollback.assert_awaited_once()
