"""파일 역할: 감사 로그 공통 기반의 출력·입력 제한·요청 ID를 검증합니다.

실행: api/에서 uv run --locked pytest tests/test_audit.py.
실제 AWS·사용자 데이터 없이 테스트 이벤트와 로그 버퍼를 사용합니다.
업무 API의 감사 기록이나 영구 저장소 검증을 대신하지 않습니다.
"""

import io
import json
import logging
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr, ValidationError

from app.core.audit import AuditAction, AuditEvent, AuditOutcome, logger, record_audit
from app.core.config import Settings
from app.main import create_app


# 1. 공통 테스트 데이터: 정상 이벤트를 만들고 검사할 필드만 바꿉니다.
# 로그 필드의 validation을 통과하는지 확인하며 실제 사용자 신원을 조회하지 않습니다.
def event(**updates: object) -> AuditEvent:
    values: dict[str, object] = {
        "environment": "dev",
        "requestId": str(uuid4()),
        "actorType": "user",
        "actorId": str(uuid4()),
        "action": AuditAction.REPORT_READ,
        "resourceType": "report",
        "resourceId": str(uuid4()),
        "outcome": AuditOutcome.SUCCESS,
    }
    values.update(updates)
    return AuditEvent.model_validate(values)


# 2. 출력 검증: 실제 logger의 출력을 메모리로 받아 JSON 한 줄·식별자·시각을 검사합니다.
# 임시 handler는 finally에서 제거해 다른 테스트에 중복 출력을 남기지 않습니다.
def test_audit_emits_one_structured_event() -> None:
    output = io.StringIO()
    handler = logging.StreamHandler(output)
    logger.addHandler(handler)
    try:
        record_audit(event())
    finally:
        logger.removeHandler(handler)
    lines = output.getvalue().splitlines()
    assert len(lines) == 1
    data = json.loads(lines[0])
    assert data["action"] == "report.read"
    assert data["outcome"] == "success"
    assert UUID(data["requestId"])
    assert data["at"].endswith(("Z", "+00:00"))


# 3. 민감정보·잘못된 입력 차단: 필드 추가, URL을 ID로 사용, 미지정 사건·환경을 거부합니다.
# 거부된 ValidationError 원문을 운영 로그에 출력하는지는 호출자도 별도로 통제해야 합니다.
@pytest.mark.parametrize("field", ["password", "token", "url", "transcript", "payload"])
def test_arbitrary_sensitive_fields_are_rejected(field: str) -> None:
    with pytest.raises(ValidationError):
        event(**{field: "sensitive-original-content"})


def test_url_cannot_be_used_as_internal_identity() -> None:
    with pytest.raises(ValidationError):
        event(resourceId="https://example.invalid/video?signature=secret")


def test_unknown_actions_and_environments_are_rejected() -> None:
    with pytest.raises(ValidationError):
        event(action="free-text-token")
    with pytest.raises(ValidationError):
        event(environment="unapproved-environment")


# 4. 앱 연결 검증: 두 요청의 ID가 다르고 외부 헤더를 사용하지 않는지 확인합니다.
# healthz는 DB 쿼리를 하지 않으므로 실제 DB·AWS 접속 없이 검사할 수 있습니다.
def test_request_id_is_server_generated_and_returned() -> None:
    settings = Settings(
        _env_file=None,
        db_host="localhost",
        db_name="test",
        db_user="test",
        db_password=SecretStr("test-only"),
    )
    with TestClient(create_app(settings)) as client:
        a = client.get("/healthz", headers={"X-Request-Id": "untrusted-header"})
        b = client.get("/healthz")
    assert UUID(a.headers["X-Request-Id"])
    assert a.headers["X-Request-Id"] != b.headers["X-Request-Id"]
    assert a.status_code == 200
