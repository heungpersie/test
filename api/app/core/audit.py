"""감사 로그 공통 출력 기반입니다. 업무 이벤트 수집·영구 저장소는 아직 연결하지 않았습니다.

허용된 사건·내부 UUID·결과만 JSON 한 줄로 stdout에 출력합니다.
요청/응답 본문, 토큰, URL, 전사 등 자유 입력을 담을 필드는 제공하지 않습니다.
"""

import logging
import sys
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


# 1. 감사할 사건과 결과의 허용 목록입니다. 일반 HTTP access log와 구분합니다.
class AuditAction(StrEnum):
    VIDEO_URL_ISSUED = "video.url_issued"
    REPORT_READ = "report.read"
    DELETE_REQUESTED = "data.delete_requested"
    DELETE_COMPLETED = "data.delete_completed"
    CONSENT_CHANGED = "consent.changed"
    ROLE_CHANGED = "user.role_changed"
    ANALYSIS_RETRIED = "analysis.retried"
    ACCESS_DENIED = "access.denied"


class AuditOutcome(StrEnum):
    SUCCESS = "success"
    DENIED = "denied"
    FAILED = "failed"


class AuditEvent(BaseModel):
    """업무 코드가 인증·소유권·처리 결과 확인 후 만드는 이벤트입니다."""

    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)
    schema_version: int = Field(default=1, alias="schemaVersion", ge=1, le=1)
    event_id: UUID = Field(default_factory=uuid4, alias="eventId")
    at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    environment: str = Field(pattern=r"^(local|dev|demo)$")
    request_id: UUID = Field(alias="requestId")
    actor_id: UUID | None = Field(default=None, alias="actorId")
    actor_type: str = Field(alias="actorType", pattern=r"^(user|service|anonymous)$")
    action: AuditAction
    resource_type: str = Field(
        alias="resourceType", pattern=r"^(video|report|analysis|user|consent)$"
    )
    resource_id: UUID | None = Field(default=None, alias="resourceId")
    outcome: AuditOutcome


# 2. 전용 logger의 root 전파를 끄고 handler 중복을 방지합니다.
# 메시지는 이미 스키마 검증된 JSON입니다. exception·stack·extra payload를 붙이지 않습니다.
logger = logging.getLogger("presentation.audit")
logger.setLevel(logging.INFO)
logger.propagate = False


def configure_audit_logging() -> None:
    """앱 수명주기에서 한 번 연결합니다. 반복 생성 시 handler를 중복하지 않습니다."""
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(handler)


def record_audit(event: AuditEvent) -> None:
    """로그 출력 성공은 업무 트랜잭션과 원자적 기록·영구 보존을 보장하지 않습니다."""
    logger.info(event.model_dump_json(by_alias=True))
