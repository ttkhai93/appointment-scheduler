from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api import appointments, availability, catalog, health
from app.config import settings
from app.exceptions import (
    BookingConflictError,
    DomainValidationError,
    NotFoundError,
)
from app.observability import BOOKING_CONFLICTS, configure_logging, install


def create_app() -> FastAPI:
    configure_logging()
    app = FastAPI(title=settings.app_name)

    @app.exception_handler(BookingConflictError)
    async def handle_conflict(_: Request, exc: BookingConflictError):
        BOOKING_CONFLICTS.inc()
        return JSONResponse(
            status_code=409,
            content={"detail": exc.message, "code": exc.code},
        )

    @app.exception_handler(DomainValidationError)
    async def handle_validation(_: Request, exc: DomainValidationError):
        return JSONResponse(status_code=422, content={"detail": str(exc)})

    @app.exception_handler(NotFoundError)
    async def handle_not_found(_: Request, exc: NotFoundError):
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    install(app)
    app.include_router(health.router)
    app.include_router(catalog.router)
    app.include_router(availability.router)
    app.include_router(appointments.router)
    return app
