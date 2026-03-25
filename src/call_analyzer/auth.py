from fastapi import Depends, HTTPException, Security
from fastapi.security import APIKeyHeader

from call_analyzer.config import settings

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(api_key: str | None = Security(_api_key_header)) -> None:
    """Verify API key if configured. Empty api_key setting disables auth."""
    if not settings.api_key:
        return
    if api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
