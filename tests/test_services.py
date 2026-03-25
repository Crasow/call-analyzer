import io
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from call_analyzer.services import FileTooLargeError, UnsupportedFormatError, save_uploaded_file


def _make_upload_file(filename: str, data: bytes):
    mock = AsyncMock()
    mock.filename = filename
    mock.read = AsyncMock(return_value=data)
    return mock


@pytest.mark.asyncio
async def test_save_uploaded_file_unsupported_format():
    file = _make_upload_file("test.txt", b"data")
    session = AsyncMock()
    with pytest.raises(UnsupportedFormatError, match="Unsupported format"):
        await save_uploaded_file(file, "api", session)


@pytest.mark.asyncio
async def test_save_uploaded_file_too_large():
    file = _make_upload_file("test.wav", b"x" * 200)
    session = AsyncMock()
    with patch("call_analyzer.services.settings") as mock_settings:
        mock_settings.max_upload_size = 100
        mock_settings.upload_dir = "/tmp/uploads"
        with pytest.raises(FileTooLargeError, match="too large"):
            await save_uploaded_file(file, "api", session)


@pytest.mark.asyncio
async def test_save_uploaded_file_success(tmp_path):
    file = _make_upload_file("test.wav", b"fake audio data")
    session = AsyncMock()
    session.refresh = AsyncMock()

    with patch("call_analyzer.services.settings") as mock_settings, \
         patch("call_analyzer.services.get_storage_client") as mock_storage_factory:
        mock_settings.max_upload_size = 100 * 1024 * 1024
        mock_settings.upload_dir = str(tmp_path)
        mock_storage = AsyncMock()
        mock_storage.upload = AsyncMock(return_value="/stored/path.wav")
        mock_storage_factory.return_value = mock_storage

        call = await save_uploaded_file(file, "api", session)

    assert call.filename == "test.wav"
    assert call.audio_format == "wav"
    assert call.source == "api"
    assert call.status == "pending"
    session.add.assert_called_once()
    assert session.commit.await_count == 2  # once for call, once for path update
    mock_storage.upload.assert_awaited_once()
