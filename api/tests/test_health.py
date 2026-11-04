import logging
from collections.abc import Iterator
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr, ValidationError
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.session import get_session
from app.main import create_app


def settings() -> Settings:
    return Settings(
        _env_file=None,
        db_host="localhost",
        db_name="coach",
        db_user="coach_app",
        db_password=SecretStr("test-secret-with-@:/%"),
    )


def test_health_does_not_connect_to_database() -> None:
    app = create_app(settings())

    def forbidden_session() -> Iterator[Session]:
        raise AssertionError("liveness must not access DB")
        yield  # pragma: no cover

    app.dependency_overrides[get_session] = forbidden_session
    with TestClient(app) as client:
        assert client.get("/healthz").json() == {"status": "ok"}


@pytest.mark.parametrize("available", [True, False])
def test_readiness(available: bool, caplog: pytest.LogCaptureFixture) -> None:
    app = create_app(settings())
    session = MagicMock(spec=Session)
    if not available:
        session.execute.side_effect = OperationalError(
            "SELECT 1", {}, Exception("test-secret-with-@:/%")
        )

    def override_session() -> Iterator[Session]:
        yield session

    app.dependency_overrides[get_session] = override_session
    with TestClient(app) as client, caplog.at_level(logging.WARNING):
        response = client.get("/readyz")
    assert response.status_code == (200 if available else 503)
    assert response.json() == (
        {"status": "ready"} if available else {"detail": "Database unavailable"}
    )
    assert "test-secret" not in response.text + caplog.text


def test_url_preserves_special_characters() -> None:
    config = settings()
    assert config.database_url().password == "test-secret-with-@:/%"
    assert "test-secret" not in repr(config)


def test_empty_password_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            db_host="localhost",
            db_name="coach",
            db_user="coach_app",
            db_password=SecretStr(""),
        )
