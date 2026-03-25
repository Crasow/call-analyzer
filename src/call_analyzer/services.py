import uuid
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from call_analyzer.audio import SUPPORTED_EXTENSIONS, get_audio_format
from call_analyzer.config import settings
from call_analyzer.external_storage import get_storage_client
from call_analyzer.models import Call


class FileTooLargeError(Exception):
    pass


class UnsupportedFormatError(Exception):
    pass


async def save_uploaded_file(
    file: UploadFile,
    source: str,
    session: AsyncSession,
    profile_id: uuid.UUID | None = None,
) -> Call:
    """Validate, save file, and create a pending Call record.

    DB commit happens BEFORE writing the file so that a DB failure
    doesn't leave orphan files on disk.
    """
    ext = Path(file.filename or "").suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise UnsupportedFormatError(f"Unsupported format: {ext}. Supported: {SUPPORTED_EXTENSIONS}")

    data = await file.read()
    if len(data) > settings.max_upload_size:
        raise FileTooLargeError(
            f"File too large: {len(data)} bytes. Max: {settings.max_upload_size} bytes"
        )

    file_key = f"{uuid.uuid4()}{ext}"

    call = Call(
        id=uuid.uuid4(),
        filename=file.filename or "unknown",
        audio_format=get_audio_format(file.filename or "unknown"),
        source=source,
        file_path=file_key,  # Will be updated after storage upload
        status="pending",
        profile_id=profile_id,
    )
    session.add(call)
    await session.commit()
    await session.refresh(call)

    # Write file AFTER successful DB commit
    storage = get_storage_client()
    stored_path = await storage.upload(data, file_key)
    call.file_path = stored_path
    await session.commit()

    return call
