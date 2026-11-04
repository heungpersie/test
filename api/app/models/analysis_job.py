from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AnalysisJob(Base):
    __tablename__ = "analysis_jobs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('queued', 'running', 'succeeded', 'failed')", name="status_allowed"
        ),
        CheckConstraint("progress BETWEEN 0 AND 100", name="progress_range"),
        CheckConstraint("attempt >= 1", name="attempt_positive"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    rehearsal_id: Mapped[UUID] = mapped_column(
        ForeignKey("rehearsals.id", ondelete="RESTRICT"), index=True
    )
    # 논리 작업 하나의 외부 ID입니다. 재시도별 ID가 필요하면 별도 시도 모델로 확장합니다.
    external_job_id: Mapped[str | None] = mapped_column(Text, unique=True)
    status: Mapped[str] = mapped_column(String(20), default="queued", server_default="queued")
    stage: Mapped[str | None] = mapped_column(String(50))
    progress: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    attempt: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    error_code: Mapped[str | None] = mapped_column(String(100))
    # 저장 전에 서비스에서 비밀번호·토큰 등 민감정보를 제거해야 합니다.
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
