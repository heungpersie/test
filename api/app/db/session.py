from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session

from app.core.config import Settings


def build_engine(settings: Settings) -> Engine:
    return create_engine(
        settings.database_url(),
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=0,
        pool_timeout=3,
        connect_args={"connect_timeout": 3, "options": "-c statement_timeout=3000"},
        hide_parameters=True,
    )


def get_session(request: Request) -> Iterator[Session]:
    # No implicit commit: each business operation owns its transaction.
    with Session(request.app.state.db_engine) as session:
        yield session


DatabaseSession = Annotated[Session, Depends(get_session)]
