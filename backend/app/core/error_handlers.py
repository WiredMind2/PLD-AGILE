from fastapi import Request, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
import logging

logger = logging.getLogger(__name__)


async def http_exception_handler(request: Request, exc: HTTPException):
    # Preserve status code and return a JSON payload with structured fields
    content = {
        "error": "http_exception",
        "message": exc.detail,
        "status_code": exc.status_code,
    }
    return JSONResponse(status_code=exc.status_code, content=content)


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    # Normalize Pydantic validation errors into a simpler structure
    errors = []
    try:
        for e in exc.errors():
            loc = ".".join([str(x) for x in e.get("loc", [])])
            msg = e.get("msg")
            errors.append({"loc": loc, "msg": msg})
    except Exception:
        errors = str(exc)
    content = {"error": "validation_error", "message": "Invalid request", "details": errors}
    return JSONResponse(status_code=422, content=content)


async def generic_exception_handler(request: Request, exc: Exception):
    # Log the unexpected exception and return a generic 500 response
    logger.exception("Unhandled exception during request processing")
    content = {"error": "internal_server_error", "message": "An unexpected error occurred"}
    return JSONResponse(status_code=500, content=content)
