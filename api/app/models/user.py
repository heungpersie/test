from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, validates

from app.db.base import Base


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("role IN ('presenter', 'expert')", name="role_allowed"),
        CheckConstraint(
            "email = lower(trim(email)) AND length(email) > 0", name="email_normalized"
        ),
    )

    # UUID는 INSERT 시 애플리케이션에서 생성합니다.
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(String(320), unique=True)
    # 이 필드에는 해시 결과만 저장합니다. 해싱과 인증은 후속 서비스에서 구현합니다.
    password_hash: Mapped[str] = mapped_column(Text)
    role: Mapped[str] = mapped_column(String(20), default="presenter", server_default="presenter")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    @validates("email")
    def normalize_email(self, _key: str, value: str) -> str:
        return value.strip().lower()
