"""FastAPI application entry point for AI Energy Brain.

Responsibilities are deliberately narrow: create the app, apply CORS,
mount routers. No business logic and no ML code belongs in this file.
"""

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.app.core.config import settings
from backend.app.core.errors import AppError, app_error_handler, unhandled_error_handler
from backend.app.routes import alerts, dashboard, energy, health, machines, recommendations

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description=settings.DESCRIPTION,
)

# Browsers block cross-origin requests by default. The React dev server
# runs on a different port than this API, so it must be allowed explicitly.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
    allow_headers=["*"],
)

@app.on_event("startup")
def _warm_caches() -> None:
    """Load sensors + score once at startup (a few seconds) so the first
    page load is not slow. Failure here must not stop the API."""
    try:
        from backend.app.services import energy_service, machine_service
        machine_service.warm_up()
        energy_service.get_summary()
    except Exception as exc:  # noqa: BLE001
        print(f"[startup] cache warm-up skipped: {exc}")


# Consistent error shape across every route (section 31): every error
# response is {"error": {"code": "...", "message": "..."}}, never a
# raw stack trace.
app.add_exception_handler(AppError, app_error_handler)
app.add_exception_handler(Exception, unhandled_error_handler)


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request, exc: RequestValidationError) -> JSONResponse:
    # Pydantic/FastAPI request validation failures (422) get the same
    # consistent error envelope as AppError, instead of FastAPI's default shape.
    return JSONResponse(
        status_code=422,
        content={"error": {"code": "VALIDATION_ERROR", "message": str(exc.errors())}},
    )


# All application routes live under /api
app.include_router(health.router, prefix="/api")
app.include_router(energy.router, prefix="/api")
app.include_router(machines.router, prefix="/api")
app.include_router(recommendations.router, prefix="/api")
app.include_router(alerts.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")


@app.get("/", tags=["system"])
def root() -> dict:
    """Small landing payload so hitting the bare URL is not a 404."""
    return {
        "service": settings.APP_NAME,
        "version": settings.VERSION,
        "docs": "/docs",
        "health": "/api/health",
    }
