from alembic.runtime.environment import NameFilterParentNames, NameFilterType

from app import models  # noqa: F401 -- 모든 모델을 metadata에 등록합니다.
from app.db.base import Base

target_metadata = Base.metadata


def include_name(
    name: str | None, type_: NameFilterType, parent_names: NameFilterParentNames
) -> bool:
    # autogenerate가 관리 외 테이블을 DROP 후보로 만들지 않도록 모델의 표만 비교합니다.
    # 모델을 제거해 테이블도 삭제하려면 수동 마이그레이션과 리뷰가 필요합니다.
    if type_ == "table":
        table_key = parent_names.get("schema_qualified_table_name") or name
        return table_key in target_metadata.tables
    return True
