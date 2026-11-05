"""파일 역할: FastAPI 앱과 시작·종료 처리를 구성합니다.

시작: 감사 logger 연결·환경설정 로드·DB engine 준비.
요청: 서버가 request UUID를 만들고 정상 응답의 X-Request-Id에 넣습니다.
종료: DB engine 자원을 정리합니다. 실제 업무 감사 사건은 여기서 자동 생성하지 않습니다.
"""

from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request, Response

from app.core.audit import configure_audit_logging
from app.core.config import Settings
from app.db.session import build_engine
from app.routers.health import router


# 1. 앱 생성 함수: 테스트는 settings를 전달하고 실제 실행은 환경설정을 읽습니다.
def create_app(settings: Settings | None = None) -> FastAPI:
    # 2. 수명주기: yield 이전은 시작 준비, 이후 finally는 종료 정리입니다.
    # engine 생성 자체가 실제 DB 연결·업무 쿼리 성공을 뜻하지는 않습니다.
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

    # 3. 요청 추적: 외부 X-Request-Id를 그대로 신뢰하지 않고 서버에서 UUID를 생성합니다.
    # 업무 API는 request.state.request_id를 감사 로그에 사용합니다.
    # 여기서는 정상 반환 경로에 응답 헤더를 붙이며, 예외 응답 전체의 보장은 별도 보완 대상입니다.
    @application.middleware("http")
    async def request_id(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request.state.request_id = uuid4()
        response = await call_next(request)
        response.headers["X-Request-Id"] = str(request.state.request_id)
        return response

    # 4. 현재 구현된 health/readiness 라우터를 연결합니다. 업무 API hook은 아직 없습니다.
    application.include_router(router)
    return application


# Uvicorn의 app.main:app이 이 인스턴스를 실행합니다.
app = create_app()
