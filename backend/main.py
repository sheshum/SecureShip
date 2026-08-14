import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.exceptions import SessionExpiredError
from app.dependencies import get_settings
from app.routers import auth, chat, customers, health, packages, sessions, shipments

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="SecureShipBackend",
        description="BFF for SecureShip client application",
        version="1.0.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(SessionExpiredError)
    async def session_expired_handler(_request: Request, _exc: SessionExpiredError) -> JSONResponse:
        resp = JSONResponse(
            status_code=410,
            content={"detail": "Session has expired or no longer exists"},
        )
        resp.delete_cookie("session_id", path="/", samesite="strict")
        return resp

    app.include_router(health.router)
    app.include_router(chat.router)
    app.include_router(auth.router)
    app.include_router(sessions.router)
    app.include_router(packages.router)
    app.include_router(shipments.router)
    app.include_router(customers.router)

    return app


app = create_app()
