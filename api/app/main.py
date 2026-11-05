from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request, Response

from app.core.audit import configure_audit_logging
from app.core.config import Settings
from app.db.session import build_engine
from app.routers.health import router


def create_app(settings: Settings | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        configure_audit_logging()
        config = settings if settings is not None else Settings()
        engine = build_engine(config)
        app.state.db_engine = engine
        try:
            yield
        finally:
            engine.dispose()

    application = FastAPI(title="Presentation Coach API", lifespan=lifespan)

    # 서버가 만든 ID를 로그·응답에 연결합니다. 클라이언트 헤더는 신뢰하지 않습니다.
    @application.middleware("http")
    async def request_id(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request.state.request_id = uuid4()
        response = await call_next(request)
        response.headers["X-Request-Id"] = str(request.state.request_id)
        return response

    application.include_router(router)
    return application


app = create_app()
