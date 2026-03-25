import asyncio
import logging

import httpx

from call_analyzer.config import settings

logger = logging.getLogger(__name__)

MAX_RETRIES = 3


async def send_webhook(call, result) -> None:
    """Send webhook notification after call analysis. Retries up to 3 times."""
    if not settings.webhook_url:
        return

    payload = {
        "event": "call.analyzed",
        "call_id": str(call.id),
        "filename": call.filename,
        "status": call.status,
    }

    if hasattr(result, "is_fraud"):
        payload["is_fraud"] = result.is_fraud
        payload["fraud_score"] = result.fraud_score
    else:
        payload["profile_result"] = True

    timeout = httpx.Timeout(settings.webhook_timeout)

    for attempt in range(MAX_RETRIES):
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.post(settings.webhook_url, json=payload)
                resp.raise_for_status()
                logger.info("Webhook sent for call %s (status %s)", call.id, resp.status_code)
                return
        except Exception:
            if attempt < MAX_RETRIES - 1:
                backoff = 2 ** attempt
                logger.warning("Webhook attempt %d failed, retrying in %ds", attempt + 1, backoff)
                await asyncio.sleep(backoff)
            else:
                logger.error("Webhook failed after %d attempts for call %s", MAX_RETRIES, call.id)
