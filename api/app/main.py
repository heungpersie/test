from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.config import Settings
from app.db.session import build_engine
from app.routers.health import router


def create_app(settings: Settings | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        config = settings if settings is not None else Settings()
        engine = build_engine(config)
        app.state.db_engine = engine
        try:
            yield
        finally:
            engine.dispose()

    application = FastAPI(title="Presentation Coach API", lifespan=lifespan)
    application.include_router(router)
    return application


app = create_app()
