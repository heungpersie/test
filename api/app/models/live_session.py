from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class LiveSession(Base):
    __tablename__ = "live_sessions"
    __table_args__ = (
        CheckConstraint(
            "status IN ('prepared', 'active', 'ended', 'expired')", name="status_allowed"
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    # 회차당 논리 세션 하나입니다. live 모드 여부는 서비스에서 별도로 확인합니다.
    rehearsal_id: Mapped[UUID] = mapped_column(
        ForeignKey("rehearsals.id", ondelete="RESTRICT"), unique=True
    )
    status: Mapped[str] = mapped_column(String(20), default="prepared", server_default="prepared")
    # 원문 토큰은 저장하지 않습니다. 발급·검증 및 해싱은 후속 기능입니다.
    token_hash: Mapped[str | None] = mapped_column(Text)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
