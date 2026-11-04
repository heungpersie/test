# 발표 코칭 API

실제 서비스의 실행 기반입니다. Python 3.13.15, uv 0.12.15, FastAPI, SQLAlchemy 2, Psycopg 3을 사용합니다. 정확한 패키지 버전은 uv.lock에 있습니다.

현재 구현: 설정 검증, 요청별 동기 DB 세션, 생존·DB 준비 상태 API. 다섯 ORM 모델과 Alembic 설치·설정까지 작성했습니다. 업무 API·인증·기존 coach DB의 실제 서비스 테이블은 아직 없습니다. 최초 revision 0001은 생성하고 별도 임시 PostgreSQL에서 검증했습니다.

## Compose로 실행

프로젝트 루트에서 실행합니다. 기존 infra/.env를 덮어쓰지 마세요. 새 팀원은 infra/.env.example을 복사한 뒤 두 비밀번호를 설정합니다.

```sh
cd infra
docker compose config --quiet
docker compose up -d --build --wait
docker compose ps
curl -f http://127.0.0.1:8000/healthz
curl -f http://127.0.0.1:8000/readyz
```

포트 충돌 시 infra/.env에 API_HOST_PORT를 설정하고 그 포트로 접속합니다. DB의 앱 비밀번호가 DB_PASSWORD로 api에 전달됩니다. 관리자 비밀번호는 api에 전달하지 않습니다.

- /healthz: DB에 접속하지 않는 생존 상태, 200.
- /readyz: 앱에서 SELECT 1 성공 시 200, DB 연결·쿼리 실패 시 503.
- /docs: 자동 API 문서.

Compose healthcheck는 /readyz를 사용합니다. unhealthy 표시만으로 컨테이너가 자동 재시작되지는 않습니다. restart 정책은 프로세스 종료 시 동작합니다.

## PC에서 직접 실행

uv 0.12.15를 준비한 다음 api/에서 실행합니다. uv는 .python-version의 Python을 사용하며 없으면 다운로드할 수 있습니다.

```sh
cp -n .env.example .env
# .env의 DB_PASSWORD를 개인 infra/.env의 APP_DB_PASSWORD와 맞춤
# DB_PORT도 POSTGRES_HOST_PORT와 맞춤
uv sync --locked
uv run --locked uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Compose api가 8000을 쓰고 있다면 PC 서버 포트를 변경하거나 infra/에서 docker compose stop api로 앱만 정지합니다. DB는 유지합니다. 컨테이너는 postgres:5432, PC는 localhost:15432를 사용합니다.

## 검사

api/에서 실행합니다. 단위 테스트는 실제 coach DB를 사용하거나 변경하지 않습니다.

```sh
uv run --locked ruff check .
uv run --locked ruff format --check .
uv run --locked mypy app
uv run --locked pytest -q
```

세션 의존성은 app/db/session.py의 get_session입니다. 업무 API는 이 세션을 주입받되 트랜잭션의 commit/rollback 범위를 기능별로 명시해야 합니다. 의존성은 요청 종료 시 세션을 닫으며 자동 commit하지 않습니다.

DB 연결은 3초 접속 제한·쿼리 제한과 제한된 풀을 사용합니다. 장애 시 준비 상태 응답에 연결 상세를 노출하지 않습니다. SQLAlchemy URL.create로 비밀번호 특수문자를 처리합니다.

## 파일별 역할

| 파일 | 역할 |
|---|---|
| .python-version | Python 패치 버전 |
| pyproject.toml, uv.lock | 의존성·도구 설정과 잠금 |
| app/main.py | 앱 생성과 시작·종료 시 DB 엔진 수명 관리 |
| app/core/config.py | 환경변수 검증과 연결 URL 구성 |
| app/db/session.py | 엔진·요청별 세션 |
| app/routers/health.py | 생존·준비 상태 API |
| Dockerfile, .dockerignore | 비관리자 컨테이너 실행, 빌드 대상 제한 |
| tests/test_health.py | 상태 API·장애·비밀값·설정 검증 |

## 다음 작업

최초 마이그레이션 파일을 생성·리뷰한 뒤 별도 DB에서 검증합니다. 기존 DB에 create_all이나 스키마 자동 변경을 실행하지 않습니다.


## Alembic 설치·설정 (2026-11-02)

Alembic 1.20.1을 의존성과 uv.lock에 반영했습니다.

- alembic.ini: 스크립트·로그 설정. DB 비밀번호와 URL을 저장하지 않습니다.
- migrations/env.py: 앱 Settings에서 접속 정보를 받아 실행합니다. offline 모드는 SQL만 생성하며 DB에 연결하지 않습니다.
- app/db/migration.py: 다섯 모델의 metadata와 자동 생성 대상 필터.
- migrations/script.py.mako: 향후 revision 파일 생성 템플릿.
- migrations/versions/: 최초 revision 0001이 있습니다. 기존 coach DB에는 아직 적용하지 않았습니다.

설정 확인은 api/에서 실행합니다. 아래 두 명령은 DB에 연결하지 않습니다.

```sh
uv run --locked alembic heads
uv run --locked alembic history
```

현재 heads는 0001 (head), history는 <base> -> 0001을 표시합니다. `current`, `check`, `revision --autogenerate`는 DB 연결을 사용할 수 있습니다. `upgrade`, `downgrade`, `stamp`는 대상 DB 상태를 변경할 수 있으므로 별도 검증·리뷰 단계에서 진행합니다. 앱 시작 때 자동 실행하지 않습니다.

자동 생성은 metadata에 등록된 테이블만 비교하므로 infra_test 등 관리 외 테이블은 삭제 후보에서 제외됩니다. 이 필터는 자동 생성 보조 규칙이며, 수동 migration의 삭제 SQL 실행을 차단하는 장치는 아닙니다. 관리 모델을 제거해 테이블도 삭제할 경우 수동 변경과 리뷰가 필요합니다.

Dockerfile에도 Alembic 설정과 스크립트를 포함하도록 작성했지만 이번 단계에서 이미지를 다시 빌드하거나 컨테이너를 교체하지 않았습니다.


## 최초 마이그레이션 검증 (2026-11-02)

- 변경 파일: migrations/versions/0001_create_initial_service_tables.py
- SQL 검토용 파일: migrations/0001_review.sql. 직접 실행하지 말고 변경 적용은 Alembic으로 관리합니다.
- upgrade: users, presentations, rehearsals, analysis_jobs, live_sessions와 인덱스 생성.
- downgrade: 위 테이블을 역순으로 제거합니다. 실제 데이터가 있으면 삭제되므로 일반 종료에 사용하지 않습니다.
- Alembic은 적용 버전을 기록하는 alembic_version 테이블도 사용합니다.

기존 볼륨을 연결하지 않은 임시 PostgreSQL 15에서 적용 → 제약 검사 → 되돌리기 → 재적용을 통과했습니다. 관리 외 infra_test와 확인용 행은 전 과정에서 보존됐고, alembic check도 통과했습니다. 임시 컨테이너는 검증 후 제거했습니다.

통합 검사는 tests/test_migration_postgres.py입니다. 일반 pytest에서는 건너뛰며, COACH_MIGRATION_TEST=1과 전용 coach_check DB를 명시해야 실행됩니다. 이 테스트는 테이블을 생성·제거하므로 새 임시 DB만 사용합니다. 원본 DB의 백업·복원 확인과 실제 적용은 다음 작업입니다.
