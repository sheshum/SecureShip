from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.dependencies import get_settings
from app.routers import chat, health, sessions


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

    app.include_router(health.router)
    app.include_router(sessions.router)
    app.include_router(chat.router)

    return app


app = create_app()
