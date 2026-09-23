"""
Explicit catch-all exception handler, guarantees no internal error
detail ever leaks to a client.
"""
import logging
from fastapi import Request
from fastapi.responses import JSONResponse

logger = logging.getLogger("fraudlens")


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred. Please try again."},
    )
