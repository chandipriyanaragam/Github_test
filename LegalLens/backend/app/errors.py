from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


def error_response(request: Request, status_code: int, code: str, message: str, details: list[dict[str, str]] | None = None):
    return JSONResponse(
        status_code=status_code,
        content={"error": {
            "code": code,
            "message": message,
            "request_id": getattr(request.state, "request_id", None),
            "details": details or [],
        }},
    )


async def http_error_handler(request: Request, exc: StarletteHTTPException):
    code_messages = {
        401: ("unauthorized", "Authentication is required."),
        403: ("forbidden", "You do not have access to this resource."),
        404: ("not_found", "The requested resource was not found."),
        400: ("bad_request", "The request could not be processed."),
        422: ("validation_error", str(exc.detail) if isinstance(exc.detail, str) else "The request could not be accepted."),
        413: ("file_too_large", "The uploaded file exceeds the configured size limit."),
        415: ("unsupported_media_type", "Only PDF and DOCX files are accepted."),
        429: ("rate_limited", "Too many requests. Please try again shortly."),
        501: ("capability_not_configured", "This capability is not configured."),
    }
    code, safe_message = code_messages.get(exc.status_code, ("request_error", str(exc.detail) if isinstance(exc.detail, str) else "The request could not be completed."))
    return error_response(request, exc.status_code, code, safe_message)


async def validation_error_handler(request: Request, exc: RequestValidationError):
    details = [{"field": ".".join(str(p) for p in item["loc"] if p != "body"), "message": item["msg"]} for item in exc.errors()]
    return error_response(request, 422, "validation_error", "The request could not be accepted.", details)


async def unexpected_error_handler(request: Request, exc: Exception):
    return error_response(request, 500, "internal_error", "An unexpected error occurred. Please retry or contact support.")
