"""파일 역할: 업무 감사 이벤트의 형식을 제한하고 JSON 한 줄로 출력합니다.

흐름: 업무 API에서 인증·처리 결과 확인 → AuditEvent 검증 → record_audit 출력.
입력: 허용된 사건·내부 UUID·결과. 출력: stdout의 JSON 로그.
연결: main.py가 앱 시작 시 logger를 설정하고 요청 ID를 만들어 줍니다.
범위: 업무 API hook·중앙 수집·영구 저장·트랜잭션 연동은 아직 구현하지 않았습니다.
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


# 2. 이벤트 형식: 정의한 필드만 받습니다. 임의 payload·토큰·본문을 추가할 수 없습니다.
# UUID는 내부 식별자이며, 누가 무엇을 했는지는 서버의 인증·업무 코드가 채워야 합니다.
class AuditEvent(BaseModel):
    """업무 코드가 인증·소유권·처리 결과 확인 후 만드는 이벤트입니다."""

    # 입력 규칙: 모르는 필드는 거부하고 생성 뒤 값 변경을 막습니다.
    # Python에서는 snake_case, JSON에서는 alias의 camelCase 이름을 사용합니다.
    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)
    # 사건 식별: eventId는 사건마다, requestId는 같은 요청 안의 사건마다 공유합니다.
    # 시각은 기본 UTC, environment는 local/dev/demo로 제한합니다.
    schema_version: int = Field(default=1, alias="schemaVersion", ge=1, le=1)
    event_id: UUID = Field(default_factory=uuid4, alias="eventId")
    at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    environment: str = Field(pattern=r"^(local|dev|demo)$")
    request_id: UUID = Field(alias="requestId")
    # 행위자·대상·결과: 이름·이메일·URL 대신 내부 ID와 허용된 분류를 기록합니다.
    # 미상 ID는 null을 허용합니다. 사건별 필수 ID 조건은 업무 API 통합 시 보완합니다.
    actor_id: UUID | None = Field(default=None, alias="actorId")
    actor_type: str = Field(alias="actorType", pattern=r"^(user|service|anonymous)$")
    action: AuditAction
    resource_type: str = Field(
        alias="resourceType", pattern=r"^(video|report|analysis|user|consent)$"
    )
    resource_id: UUID | None = Field(default=None, alias="resourceId")
    outcome: AuditOutcome


# 3. 출력 경로: 전용 logger의 root 전파를 끄고 handler 중복을 방지합니다.
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


# 4. 업무 코드가 호출할 진입점입니다. JSON 검증은 AuditEvent 생성 때 수행됩니다.
# stdout 출력만 하므로 DB 커밋과의 원자성·유실 방지·불변 보관은 별도 구현이 필요합니다.
def record_audit(event: AuditEvent) -> None:
    """로그 출력 성공은 업무 트랜잭션과 원자적 기록·영구 보존을 보장하지 않습니다."""
    logger.info(event.model_dump_json(by_alias=True))
