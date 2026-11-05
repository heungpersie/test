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
