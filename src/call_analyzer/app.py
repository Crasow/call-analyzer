import asyncio
import json as _json
import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette_csrf import CSRFMiddleware

from call_analyzer.api import router as api_router
from call_analyzer.config import settings
from call_analyzer.web import router as web_router
from call_analyzer.worker import worker_loop

limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_obj = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info and record.exc_info[1]:
            log_obj["exception"] = self.formatException(record.exc_info)
        return _json.dumps(log_obj, ensure_ascii=False)


def setup_logging() -> None:
    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    handler = logging.StreamHandler(sys.stdout)
    if settings.log_format == "json":
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(logging.Formatter("%(asctime)s %(name)s %(levelname)s %(message)s"))
    logging.basicConfig(level=level, handlers=[handler], force=True)


setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    stop_event = asyncio.Event()
    task = asyncio.create_task(worker_loop(stop_event))
    yield
    stop_event.set()
    await task


def create_app() -> FastAPI:
    application = FastAPI(title="Call Analyzer", lifespan=lifespan, root_path=settings.root_path)

    # Rate limiting
    application.state.limiter = limiter
    application.add_exception_handler(
        RateLimitExceeded,
        lambda request, exc: JSONResponse(status_code=429, content={"detail": "Rate limit exceeded"}),
    )

    # CSRF protection (exempt API routes)
    if settings.csrf_secret:
        application.add_middleware(
            CSRFMiddleware,
            secret=settings.csrf_secret,
            exempt_urls=["/api/"],
        )

    static_dir = Path(__file__).resolve().parents[2] / "static"
    application.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    settings.upload_dir.mkdir(parents=True, exist_ok=True)

    application.include_router(api_router)
    application.include_router(web_router)

    return application
