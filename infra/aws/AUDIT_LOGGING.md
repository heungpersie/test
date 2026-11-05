# 감사 로그 설계·공통 출력 구현 v1

2026-11-05 · 문서뿐 아니라 공통 JSON 출력 모듈·요청 ID·테스트를 추가했다. 현재 업무 API가 미구현이므로 영상 조회·삭제·권한 변경의 실제 이벤트 연결은 하지 않았다. AWS 수집·불변 저장·영구 보존도 미적용이다.

## 1. 무엇을 구분하는가

| 종류 | 목적 | 현재 상태 |
|---|---|---|
| HTTP access log | 요청 경로·상태·응답시간 | 기본 서버 로그. 민감 query/path 유출 방지 설정은 별도 검토 |
| 운영 로그 | DB 연결 실패·작업 지연·worker 오류 | 기본 출력. 원문 예외의 민감정보를 그대로 남기지 않음 |
| 업무 감사 로그 | 누가 어떤 대상에 접근·변경·삭제했는지 | 이번 공통 모듈 작성, 업무 API 연결은 대기 |
| AWS 감사 로그 | IAM·S3·RDS 등 AWS API 활동 | CloudTrail 설정·권한·비용 검토 후 별도 적용 |

헬스체크마다 가짜 사용자 조회·삭제 이벤트를 남기지 않는다. CloudTrail만으로 앱 사용자 권한·조회 목적을 알 수 없고 앱 로그만으로 AWS 관리자의 직접 S3 조작을 전부 추적할 수도 없다.

## 2. 실제 추가한 코드

| 파일 | 내용 | 검증 범위 |
|---|---|---|
| api/app/core/audit.py | AuditEvent 허용 필드·사건 enum, JSON 한 줄 stdout 출력 | JSON 파싱·허용 목록·원문 필드 거부 테스트 |
| api/app/main.py | 앱 시작 시 전용 logger 연결, 서버 생성 request UUID·X-Request-Id 응답 | 정상 API 응답의 UUID 생성·외부 헤더 미신뢰 확인 |
| api/tests/test_audit.py | 출력·민감 필드/URL 식별자·미지정 사건·환경·request ID 검사 | 로컬 API 테스트와 CI에서 실행 |

로그 API는 allowlist 방식이다. 내부 actor/resource UUID만 사용하고 이메일·이름·서명 URL을 넣는 필드를 만들지 않는다. 외부 API의 불투명 ID는 BE가 내부 UUID로 매핑해야 한다. 입력한 본문을 통째로 AuditEvent에 전달하지 않는다. 검증 실패의 ValidationError 전체를 출력하면 거부한 민감 입력이 노출될 수 있으므로 고정 오류 코드만 기록한다.

현재 request middleware는 정상 응답에 ID를 부여한다. 처리되지 않은 예외가 middleware 밖에서 500으로 변환되는 모든 경우의 헤더 보장은 아직 시험하지 않았다. 큐·AI로 ID를 전달하는 코드와 analysisId 연계도 업무 연결 때 추가한다.

## 3. 기록할 사건과 시점

| 사건 | 처리 시점 | 기록 의미 / 주의 |
|---|---|---|
| video.url_issued | 소유권·동의·기한 검사 후 URL 생성 시 | URL 발급 기록이지 실제 다운로드 완료가 아님. URL 원문 기록 금지 |
| report.read | 권한 검사 후 리포트 응답 준비 시 | 어떤 내부 리포트를 제공했는지. 응답 본문 기록 금지 |
| access.denied | 접근 검사에서 거부 결정 시 | 신원 확인 전이면 actor 미상. 토큰·민감 경로·타인 정보 응답 금지 |
| data.delete_requested | 삭제 요청/논리 차단을 DB에 커밋한 뒤 | 실제 파일 삭제 완료와 구분 |
| data.delete_completed | 온라인 정리 완료를 검증한 뒤 | 백업 잔여 범위를 상태와 정책에 따라 별도 기록해야 함 |
| consent.changed | 목적별 동의 변경 커밋 뒤 | 목적·정책 버전 등 허용 메타데이터 확장 필요 |
| user.role_changed | 관리자 권한 검사·변경 커밋 뒤 | 대상·처리자와 전/후 역할을 typed 필드로 확장 필요 |
| analysis.retried | 다음 attempt 확정·예약 커밋 뒤 | 중복 예약·실제 실행을 구분. attempt/version typed 필드 확장 필요 |

인증 실패·평가 배정·모델/보정 활성화·감사 로그 열람·Secret 교체·배포·복원 등 추가 사건도 추적 대상이다. 아직 enum/업무 hook을 추가하지 않았으며, 실제 API 범위와 함께 확장한다. 기존 API 명세의 관리자 action/target/before/after 요구를 이번 최소 모듈만으로 전부 충족했다고 표시하지 않는다.

## 4. 최소 필드와 민감정보 제외

코드의 schemaVersion·eventId·at(기본 UTC)·environment·requestId·actorId·actorType·action·resourceType·resourceId·outcome을 사용한다. actorId와 resourceId는 내부 UUID 또는 null이며 성공한 사용자 업무 이벤트는 인증 계정과 대상에서 서버가 채워야 한다. 현재 모듈은 사건별 필수 actor/resource 조건까지 강제하지 않으므로 BE 통합 시 검증을 보완한다.

다음 필드는 추후 필요할 때 타입과 허용값을 정의해 확장한다: analysisId·attempt·policyVersion·승인된 reasonCode·권한 변경 전/후 역할. 자유 문자열 details·임의 dict before/after는 추가하지 않는다. HTTP 헤더·본문·SQL/DB URL·스택·원본/전사/프레임·리포트/Q&A 내용·이메일·LLM prompt/response·서명 URL·API 키·비밀번호를 담지 않는다.

공통 모듈은 호출자가 인증·소유권·성공 여부를 판단하는 기능을 대신하지 않는다. 클라이언트 actorId·action·outcome을 신뢰해서 기록하지 않는다. access 거부 사건의 존재가 타인 리소스 정보를 사용자에게 노출하지 않게 한다.

## 5. 출력·수집·무결성

현재: 앱 공통 모듈 → 전용 logger → stdout → Docker json-file 로그 회전(기존 10 MB × 3). 로그 크기 회전은 일수 기반 보관 기간이나 감사 영구 보존을 보장하지 않는다. 컨테이너 삭제·디스크 장애·운영 권한으로 로그가 유실/변조될 수 있다.

목표안: 수집기 → 환경별 제한된 CloudWatch Log Group 또는 별도 감사 저장소. 앱 역할은 가능한 기록 권한만, 감사 검토자는 열람만, 삭제/보관 정책 관리자는 별도 승인 역할을 사용한다. 개발·발표 데이터를 분리하고 로그 열람·내보내기도 감사한다. 보관은 R_AUDIT와 정책 버전·만료일을 승인 후 적용한다. CloudWatch·S3·KMS·수집 비용은 미선정/미산정이며 이번 작업에서 생성하지 않았다.

고위험 변경은 DB 상태 변경과 감사 기록을 원자적으로 연결하는 outbox/감사 테이블 등 영속 경로를 검토한다. 현재 stdout 출력은 best-effort이며 업무 트랜잭션과 원자적이지 않다. record_audit 성공이 영구 보관 성공을 뜻하지 않는다. 수집 실패·디스크 한도·handler 오류 시 알림, 재전송·중복 eventId 처리와 fail-open/fail-closed 정책은 위험도별로 팀 결정한다. 코드에서 이 정책을 이미 구현했다고 간주하지 않는다.

## 6. AWS·S3 감사와 보관/삭제 연결

CloudTrail 관리 이벤트와 객체 data event는 다르다. S3 GetObject/DeleteObject 등의 객체 활동은 data event 수집을 별도로 구성해야 하며 기본 Event history에 모두 기록된다고 가정하지 않는다. 대상 버킷·prefix·read/write 범위와 비용을 정하고 역할 session·객체 ID를 업무 이벤트와 연계한다. 서명 URL 발급 기록만으로 최종 다운로드 사용자를 확정할 수는 없다.

감사 로그는 본문 없는 최소 증거만 남기고 보관 기한을 별도로 정한다. 사용자 삭제 후 어떤 연결 식별자를 얼마나 남길지는 목적·접근자·승인 근거에 따라 결정한다. 삭제·원본 내용을 감사 데이터로 복제해 우회 보관하지 않는다. 백업 복원 후 삭제 재적용 여부도 증거 사건으로 확장한다. [데이터 수명주기](DATA_LIFECYCLE.md)와 일치시킨다.

## 7. 실제 업무 코드 연결 예시

다음은 BE 담당자가 향후 리포트 API 내부에 연결할 예시이며 현재 존재하는 API가 아니다. 성공 응답과 실제 기록 보장은 영속 경로·트랜잭션 설계를 함께 검토한다.

```python
# 인증·소유권 검사와 report 조회에 성공한 뒤, 서버 내부 UUID만 전달합니다.
from app.core.audit import AuditAction, AuditEvent, AuditOutcome, record_audit

record_audit(AuditEvent(
    environment=settings.app_env,
    request_id=request.state.request_id,
    actor_type="user",
    actor_id=current_user.id,
    action=AuditAction.REPORT_READ,
    resource_type="report",
    resource_id=report.id,
    outcome=AuditOutcome.SUCCESS,
))
```

## 8. 완료·후속 결정

완료: 사건/필드·권한·보관·실패 설계 초안, 공통 출력 코드·request ID 정상 응답 연결·로컬 테스트. 코드가 실제 기록하는 업무 이벤트는 아직 없고, 테스트에서만 모듈 출력을 확인했다.

후속: BE와 사건 hook·typed before/after/정책 버전·식별자 매핑, R_AUDIT·열람 담당자·중앙 저장소·영속 보장·수집 실패 대응, AWS data event 범위·비용을 확정한다. 3주차에는 실제 조회/거부/삭제 사건 연결·수집 누락·권한 거부·민감정보 비노출·복원/유실·삭제 기한을 시험한다.

[공식 S3 CloudTrail 수집 기준](https://docs.aws.amazon.com/AmazonS3/latest/userguide/enable-cloudtrail-logging-for-s3.html) · [네트워크·보안 설계](NETWORK_SECURITY.md)
