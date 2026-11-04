# 발표 코칭 DB 설계 초안

2026-11-02 · 사용자와 단계별 검토 중. 이메일·비밀번호 로그인을 합의했고 공통 Base와 다섯 ORM 모델(User·Presentation·Rehearsal·AnalysisJob·LiveSession)을 작성했다. 마이그레이션·실제 테이블에는 아직 적용하지 않았다.

## 이번 범위

User, Presentation, Rehearsal, AnalysisJob, LiveSession의 기본 관계를 정한다. 결과·점수·전문가 평가·보정은 후속 범위이며, 이 다섯 테이블만으로 전체 서비스 DB 설계가 완료되는 것은 아니다.

## 공통 규칙 제안

- id: UUID 기본키. 생성 주체는 애플리케이션으로 통일한다.
- 시각: PostgreSQL timestamptz, UTC 기준 저장·전달. 화면에서 사용자 시간대로 표시한다.
- 필수 여부가 선택인 필드는 NULL을 허용한다. 아직 측정하지 않은 값에 0을 넣지 않는다.
- 상태·모드는 허용값 제약을 둔다. 상태 전이와 소유자 권한은 서비스 로직에서 별도로 검증한다.
- 초기 FK 삭제 정책은 RESTRICT. 영상·진행 작업 정리 없이 DB 행만 자동 연쇄 삭제하지 않는다. 삭제 흐름 구현 시 순서와 정책을 재검토한다.
- 비밀번호 해시·토큰 해시는 공개 응답 스키마에서 제외한다. ORM 모델을 그대로 API 응답으로 반환하지 않는다.

## 1. User → users

이메일·비밀번호 로그인으로 시작하기로 사용자와 합의했다. User 모델에 UUID, 정규화한 이메일 unique, 역할 제약, 시각 필드를 반영했다. 이메일 형식 검증·비밀번호 해싱·권한 부여·응답 스키마는 아직 구현하지 않았다.

| 필드 | DB 타입 | 필수 | 제약·의미 |
|---|---|---|---|
| id | uuid | 예 | 기본키 |
| email | varchar(320) | 예 | 공백 제거·소문자 정규화 후 저장, unique |
| password_hash | text | 예 | 원문 비밀번호 저장 금지 |
| role | varchar(20) | 예 | presenter / expert, 기본 presenter |
| created_at | timestamptz | 예 | 가입 시각 |

일반 회원가입에서 expert를 직접 지정하지 못하게 한다. 역할과 발표별 접근 권한은 별개다. 전문가가 어떤 발표에 접근할 수 있는지는 추후 별도 배정 관계가 필요할 수 있다.

## 2. Presentation → presentations

사용자 합의 후 모델에 반영했다. owner_id 외래키(RESTRICT)·인덱스, 제목 공백 검사, 선택 설명, 생성·수정 시각을 정의했다. updated_at은 SQLAlchemy UPDATE에서 갱신되며 DB 트리거는 아니다. ORM relationship 탐색 속성은 아직 추가하지 않았다.

| 필드 | DB 타입 | 필수 | 제약·의미 |
|---|---|---|---|
| id | uuid | 예 | 기본키 |
| owner_id | uuid | 예 | users.id FK, 조회용 인덱스 |
| title | varchar(200) | 예 | 공백만 있는 제목 불가 |
| description | text | 아니오 | 발표 설명 |
| created_at | timestamptz | 예 | 생성 시각 |
| updated_at | timestamptz | 예 | 수정 시각, 앱에서 갱신 |

User 1 : N Presentation. 다른 사용자의 발표는 소유자 ID를 기준으로 접근을 제한한다.

## 3. Rehearsal → rehearsals

사용자 합의 후 ORM 모델에 반영했다. 회차 복합 unique, 외래키 RESTRICT, 모드·상태·양수 제약을 정의했다. 상태 전이·회차 번호 배정·동의 검사·만료 계산은 후속 서비스에서 구현하며 DB에는 아직 적용하지 않았다.

| 필드 | DB 타입 | 필수 | 제약·의미 |
|---|---|---|---|
| id | uuid | 예 | 기본키 |
| presentation_id | uuid | 예 | presentations.id FK |
| sequence | integer | 예 | 1 이상, 발표 내 회차 번호 |
| mode | varchar(10) | 예 | upload / live |
| status | varchar(20) | 예 | 아래 상태 후보, 기본 created |
| video_key | text | 아니오 | 객체 저장소 위치, 파일 자체는 저장하지 않음 |
| video_content_type | varchar(100) | 아니오 | 업로드 파일의 형식 |
| duration_seconds | double precision | 아니오 | 측정 후 저장, 0보다 큼 |
| consented_at | timestamptz | 예 | 영상 처리 동의 시각 |
| created_at | timestamptz | 예 | 회차 생성 시각 |
| expires_at | timestamptz | 예 | 원본 보관 만료 시각, 조회용 인덱스 |

Presentation 1 : N Rehearsal. (presentation_id, sequence)에 unique 제약을 둔다. 회차 번호는 동시 생성 충돌을 고려해 발표 행 잠금 등으로 배정하며 단순 MAX+1만 사용하지 않는다.

상태 후보: created, live, uploaded, queued, analyzing, done, failed. mode는 연습 방식이고 status는 진행 단계다.

- upload: created → uploaded → queued → analyzing → done 또는 failed.
- live: created → live → uploaded 이후 같은 배치 흐름.
- 실제 업로드 완료·작업 접수·재시도·연결 종료 처리 계약에 맞춰 전이를 확정한다.
- 원본 보관 30일은 기술서의 초기 정책 후보다. expires_at 계산 기준과 삭제 범위는 확정 후 구현한다.

## 4. AnalysisJob → analysis_jobs

기록된 초기안을 ORM 모델에 반영했다. 재시도·결과 보존 계약은 아래 미결정 사항대로 후속 확인하며, 작업 등록 API나 실제 DB에는 아직 적용하지 않았다.

초기 제안: 한 행은 논리적인 배치 분석 요청 하나다. 같은 작업 재시도는 attempt로 추적하고, 모델·평가 기준을 바꾼 재분석은 새 행으로 만든다. 개별 재시도의 상세 이력이 필요하면 AnalysisAttempt를 후속 추가한다.

| 필드 | DB 타입 | 필수 | 제약·의미 |
|---|---|---|---|
| id | uuid | 예 | 기본키 |
| rehearsal_id | uuid | 예 | rehearsals.id FK, 인덱스 |
| external_job_id | text | 아니오 | AI 서비스의 논리 작업 ID, 존재 시 unique |
| status | varchar(20) | 예 | queued / running / succeeded / failed |
| stage | varchar(50) | 아니오 | AI와 합의한 처리 단계 |
| progress | integer | 예 | 0~100, 기본 0 |
| attempt | integer | 예 | 실행 시도 번호, 1부터 시작 |
| error_code | varchar(100) | 아니오 | 실패 코드 |
| error_message | text | 아니오 | 민감정보를 제거한 실패 설명 |
| created_at | timestamptz | 예 | 생성 시각 |
| started_at | timestamptz | 아니오 | 실행 시작 |
| finished_at | timestamptz | 아니오 | 실행 종료 |

Rehearsal 1 : N AnalysisJob. 완료 콜백은 작업 ID로 식별하고 중복 도착을 처리해야 한다. 회차 status와 작업 status는 같은 트랜잭션으로 일관되게 갱신한다.

구현 전 BE·AI 확인 사항:

- AI가 재시도마다 새 외부 ID를 발급하는가? 그렇다면 별도 시도 엔티티가 필요할 수 있다.
- 결과 파일 키·모델/평가 버전·점수는 어느 엔티티에 보존할 것인가?
- 여러 분석 중 회차 화면에 표시할 결과는 무엇인가?

이 사항은 미결정이다. 아직 작업 등록·결과 보존 API를 이 스키마로 구현하지 않는다.

## 5. LiveSession → live_sessions

회차당 논리 세션 하나인 초기안을 ORM 모델에 반영했다. 토큰·재접속 API 계약은 후속 확인 대상이다.

초기 제안: 회차당 논리 세션 하나이며 일시적인 WebSocket 재접속은 같은 세션이다. 여러 세션을 허용해야 한다면 unique 제약과 모델을 변경한다.

| 필드 | DB 타입 | 필수 | 제약·의미 |
|---|---|---|---|
| id | uuid | 예 | 기본키 |
| rehearsal_id | uuid | 예 | rehearsals.id FK, unique |
| status | varchar(20) | 예 | prepared / active / ended / expired |
| token_hash | text | 아니오 | api가 검증을 담당할 경우 저장, 원문 금지 |
| expires_at | timestamptz | 예 | 논리 세션 만료, 토큰 개별 만료와 구분 |
| started_at | timestamptz | 아니오 | 시작 시각 |
| ended_at | timestamptz | 아니오 | 종료 시각 |

Rehearsal 1 : 0..1 LiveSession. live 모드 회차에만 연결하는 규칙은 서비스에서 검사한다. FK만으로 다른 테이블의 mode 값까지 검증되지는 않는다.

토큰 발급·검증 주체, 재발급, 알림 로그와 전사 보관 위치는 AI 담당자와 확정한다. 실시간 원시 측정값을 모두 DB에 넣는 구성은 채택하지 않았다.

## 다음 작업

다섯 모델의 Python 정의와 등록을 완료했다. PostgreSQL용 DDL 생성·외래키 해석·제약조건 구성과 코드 검사를 확인한다. DB에서 제약조건을 실제 실행한 검증은 아직 아니다.

1. BE·AI와 재시도 ID, 결과 보존, 세션·토큰 계약을 확인한다.
2. Alembic을 추가하고 관리 대상 외 infra_test가 삭제 후보가 되지 않게 한다.
3. 별도 DB에서 마이그레이션과 제약을 검증하고 기존 DB 백업·복원 확인 후 적용한다.

현재 데이터·볼륨·계정은 변경하지 않는다. create_all, 초기화 스크립트 재실행, down -v는 수행하지 않는다. ORM relationship 탐색 속성은 아직 없으며 외래키로 관계를 정의했다. 인증·상태 전이·접근 권한은 별도 서비스 로직으로 구현해야 한다.

## Alembic 설정 후속 기록

2026-11-02: Alembic 설치·metadata 연결·자동 생성 테이블 필터를 구성했다. 최초 revision 생성과 DB 적용은 아직 하지 않았다.

## 최초 마이그레이션 검증

2026-11-02: revision 0001과 검토용 SQL을 생성했다. 별도 임시 PostgreSQL 15에서 실제 적용·제약 검사·downgrade·재적용·관리 외 데이터 보존을 확인했다. 기존 coach DB에는 연결하거나 적용하지 않았다.
