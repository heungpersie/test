from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Double,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Rehearsal(Base):
    __tablename__ = "rehearsals"
    __table_args__ = (
        # 같은 발표 안에서만 회차 번호가 유일합니다.
        UniqueConstraint("presentation_id", "sequence"),
        CheckConstraint("sequence >= 1", name="sequence_positive"),
        CheckConstraint("mode IN ('upload', 'live')", name="mode_allowed"),
        CheckConstraint(
            "status IN ('created', 'live', 'uploaded', 'queued', 'analyzing', 'done', 'failed')",
            name="status_allowed",
        ),
        CheckConstraint("duration_seconds > 0", name="duration_positive"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    presentation_id: Mapped[UUID] = mapped_column(
        ForeignKey("presentations.id", ondelete="RESTRICT")
    )
    # 회차 번호 배정과 동시 생성 제어는 후속 서비스에서 구현합니다.
    sequence: Mapped[int] = mapped_column(Integer)
    mode: Mapped[str] = mapped_column(String(10))
    status: Mapped[str] = mapped_column(String(20), default="created", server_default="created")
    # 영상 본문 대신 객체 저장소의 위치를 저장합니다.
    video_key: Mapped[str | None] = mapped_column(Text)
    video_content_type: Mapped[str | None] = mapped_column(String(100))
    duration_seconds: Mapped[float | None] = mapped_column(Double)
    consented_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    # 보관 기간 확정 전에는 자동 계산하지 않고 생성 처리에서 명시적으로 전달합니다.
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
