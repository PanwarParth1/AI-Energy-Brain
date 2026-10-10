"""Consistent error handling for the API (section 31).

Every error response has the same shape:
    {"error": {"code": "...", "message": "..."}}
regardless of which route or service raised it, and internal stack
traces are never sent to the client.
"""

from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse


class AppError(Exception):
    """Raise this from any service/route to produce a clean, consistent
    JSON error response with the right HTTP status code."""

    def __init__(self, status_code: int, code: str, message: str):
        self.status_code = status_code
        self.code = code
        self.message = message
        super().__init__(message)


def not_found(message: str) -> AppError:
    return AppError(404, "RESOURCE_NOT_FOUND", message)


def bad_request(message: str) -> AppError:
    return AppError(400, "BAD_REQUEST", message)


def server_error(message: str = "An unexpected error occurred.") -> AppError:
    return AppError(500, "INTERNAL_ERROR", message)


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.code, "message": exc.message}},
    )


async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    # Never leak internal details (stack traces, file paths) to the client.
    # A real deployment would log `exc` server-side here.
    return JSONResponse(
        status_code=500,
        content={"error": {"code": "INTERNAL_ERROR", "message": "An unexpected error occurred."}},
    )
