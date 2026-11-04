from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Presentation(Base):
    __tablename__ = "presentations"
    __table_args__ = (CheckConstraint("length(trim(title)) > 0", name="title_not_blank"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    # 사용자 한 명이 여러 발표를 소유합니다. 발표가 남아 있으면 사용자 삭제를 막습니다.
    owner_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    # SQLAlchemy를 통한 UPDATE 시 갱신합니다. 직접 SQL로 수정할 때는 별도 지정이 필요합니다.
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
