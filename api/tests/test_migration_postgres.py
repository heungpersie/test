"""임시 PostgreSQL 전용 통합 검사. 일반 pytest에서는 실행하지 않습니다."""

import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, delete, inspect, select, text
from sqlalchemy.exc import IntegrityError

from app.core.config import Settings
from app.models import AnalysisJob, LiveSession, Presentation, Rehearsal, User


@pytest.mark.skipif(os.getenv("COACH_MIGRATION_TEST") != "1", reason="별도 임시 DB에서만 실행")
def test_initial_migration_on_temporary_postgres() -> None:
    settings = Settings()
    # 기존 coach DB에 잘못 실행하지 않도록 대상도 제한합니다.
    assert settings.db_name == "coach_check"
    assert settings.db_host == "127.0.0.1"
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    engine = create_engine(settings.database_url())
    expected = {"users", "presentations", "rehearsals", "analysis_jobs", "live_sessions"}
    try:
        assert set(inspect(engine).get_table_names()) <= {"infra_test", "alembic_version"}
        with engine.connect() as connection:
            if "alembic_version" in inspect(engine).get_table_names():
                assert (
                    connection.execute(text("SELECT count(*) FROM alembic_version")).scalar_one()
                    == 0
                )
        command.upgrade(config, "head")
        assert set(inspect(engine).get_table_names()) == expected | {
            "infra_test",
            "alembic_version",
        }
        command.check(config)
        with engine.connect() as connection:
            transaction = connection.begin()
            user_id, presentation_id, rehearsal_id = uuid4(), uuid4(), uuid4()
            connection.execute(
                User.__table__.insert().values(
                    id=user_id, email="person@example.com", password_hash="test-only-hash"
                )
            )
            connection.execute(
                Presentation.__table__.insert().values(
                    id=presentation_id, owner_id=user_id, title="연습 발표"
                )
            )
            rehearsal = {
                "id": rehearsal_id,
                "presentation_id": presentation_id,
                "sequence": 1,
                "mode": "live",
                "consented_at": datetime.now(UTC),
                "expires_at": datetime.now(UTC) + timedelta(days=30),
            }
            connection.execute(Rehearsal.__table__.insert().values(**rehearsal))
            connection.execute(AnalysisJob.__table__.insert().values(rehearsal_id=rehearsal_id))
            connection.execute(
                LiveSession.__table__.insert().values(
                    rehearsal_id=rehearsal_id, expires_at=rehearsal["expires_at"]
                )
            )
            assert connection.execute(select(User.__table__.c.role)).scalar_one() == "presenter"
            assert connection.execute(select(AnalysisJob.__table__.c.progress)).scalar_one() == 0
            invalid = [
                User.__table__.insert().values(email="person@example.com", password_hash="hash"),
                Presentation.__table__.insert().values(owner_id=uuid4(), title="없는 사용자"),
                Presentation.__table__.insert().values(owner_id=user_id, title="  "),
                Rehearsal.__table__.insert().values(**(rehearsal | {"id": uuid4()})),
                Rehearsal.__table__.insert().values(
                    **(rehearsal | {"id": uuid4(), "sequence": 2, "mode": "invalid"})
                ),
                AnalysisJob.__table__.insert().values(rehearsal_id=rehearsal_id, progress=101),
                AnalysisJob.__table__.insert().values(rehearsal_id=rehearsal_id, attempt=0),
                AnalysisJob.__table__.insert().values(rehearsal_id=rehearsal_id, status="invalid"),
                LiveSession.__table__.insert().values(
                    rehearsal_id=rehearsal_id, expires_at=rehearsal["expires_at"]
                ),
                delete(User.__table__).where(User.__table__.c.id == user_id),
            ]
            for statement in invalid:
                with pytest.raises(IntegrityError), connection.begin_nested():
                    connection.execute(statement)
            assert (
                connection.execute(text("SELECT note FROM infra_test WHERE id=1")).scalar_one()
                == "preserve"
            )
            transaction.rollback()
        command.downgrade(config, "base")
        assert set(inspect(engine).get_table_names()) == {"infra_test", "alembic_version"}
        command.upgrade(config, "head")
        command.check(config)
        with engine.connect() as connection:
            assert (
                connection.execute(text("SELECT note FROM infra_test WHERE id=1")).scalar_one()
                == "preserve"
            )
    finally:
        engine.dispose()
