from app.models.analysis_job import AnalysisJob
from app.models.live_session import LiveSession
from app.models.presentation import Presentation
from app.models.rehearsal import Rehearsal
from app.models.user import User

# 모델을 import하면 Base.metadata에 테이블 정의가 등록됩니다. DB 쿼리는 실행하지 않습니다.
__all__ = ["AnalysisJob", "LiveSession", "Presentation", "Rehearsal", "User"]
