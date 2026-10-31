from contextlib import asynccontextmanager
import logging
import os
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from .database import check_database, initialize_database
from .errors import http_error_handler, unexpected_error_handler, validation_error_handler
from .routers.api import router as api_router
from .schemas import HealthResponse, ReadinessResponse
from .settings import settings
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"), format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("legallens")


@asynccontextmanager
async def lifespan(app: FastAPI):
    initialize_database()
    settings.storage_dir.mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(
    title="LegalLens API",
    description="Conversation, document extraction, and Ask, Draft, and Summary workflows API.",
    version="0.2.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "X-Request-ID"],
    expose_headers=["X-Request-ID"],
)


@app.middleware("http")
async def request_context(request: Request, call_next):
    incoming = request.headers.get("X-Request-ID", "")
    request_id = incoming[:100] if incoming and all(char.isalnum() or char in "-_." for char in incoming) else str(uuid4())
    request.state.request_id = request_id
    try:
        response = await call_next(request)
    except Exception as exc:
        logger.error("request_failed request_id=%s exception_type=%s", request_id, type(exc).__name__)
        raise
    response.headers["X-Request-ID"] = request_id
    return response


app.add_exception_handler(StarletteHTTPException, http_error_handler)
app.add_exception_handler(RequestValidationError, validation_error_handler)
app.add_exception_handler(Exception, unexpected_error_handler)
app.include_router(api_router)


@app.get("/health", response_model=HealthResponse, tags=["service"])
def health():
    return {"status": "ok"}


@app.get("/ready", response_model=ReadinessResponse, tags=["service"])
def readiness():
    database_ready = check_database()
    storage_ready = settings.storage_dir.exists() and os.access(settings.storage_dir, os.W_OK)
    dependencies = {"database": "ready" if database_ready else "unavailable", "document_storage": "ready" if storage_ready else "unavailable"}
    ready = database_ready and storage_ready
    if not ready:
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=503, content={"status": "not_ready", "dependencies": dependencies})
    return ReadinessResponse(status="ready", dependencies=dependencies)


@app.get("/", include_in_schema=False)
def root():
    return {"name": "LegalLens API", "version": app.version, "docs": "/docs"}
