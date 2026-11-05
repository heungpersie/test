# AI 발표 코칭 API 명세 v2

2026-11-02 · 원본: @이지영 · API 계약 정리 v2

> 문서 버전 v2이며 URL은 `/api/v1`을 유지한다. 원본 1~8장의 기능과 화면 범위를 보존한다. 이 문서의 기술 계약은 구현·합의용 수정안이며 배포 완료를 뜻하지 않는다. 각 절의 **v2 상세 계약**이 요약 표보다 우선한다. 운영 정책의 미확정 값은 8-2에서 관리하며, JSON의 예시 값은 정책 확정 근거가 아니다.
>
> 원본 외 요구사항서·app.html·분석 엔진 명세는 제공되지 않았다. 원본 대화의 첨부 Markdown을 기준으로 작성했으며, 이전 답변 본문은 참조 표시만 제공되어 검토 근거로 사용하지 않았다.

## 1. 공통 규칙

프로토타입의 기능을 유지하면서 요청·응답·상태·실패 계약을 정의한다. 8-2의 확인 필요 정책은 제품·운영·보안 담당자의 결정 후 반영한다.

- **Base URL**: `/api/v1`, JSON(UTF-8), 시간은 ISO 8601(KST 표기는 화면에서 변환)
- **인증**: 로그인하면 액세스 토큰(JWT, 짧은 만료)과 리프레시 토큰을 받아요. 보호된 HTTP 요청은 `Authorization: Bearer <token>` 헤더를 쓴다. 브라우저 WebSocket·SSE와 스토리지 업로드는 각 절의 별도 계약을 따른다. 공개 API는 표에 `공개`로 표시했어요.
- **역할**: `USER`(발표자), `EXPERT`(전문 평가자), `ADMIN`(관리자). 권한이 없으면 `403`, 로그인이 안 됐으면 `401`이에요. 프론트는 `401`이면 로그인으로 보내고 로그인 후 원래 화면으로 돌려보내요(`next`).
- **성공 응답**: `{ "data": … }`, 목록은 `{ "data": [...], "page": { "number": 0, "size": 20, "total": 135 } }`
- **에러 응답**: `{ "error": { "code": "STRING", "message": "사용자에게 보여줄 문장", "fields": { "email": "형식 오류" } } }`
- **주요 에러 코드**: `VALIDATION_FAILED`(400), `UNAUTHENTICATED`(401), `FORBIDDEN`(403), `NOT_FOUND`(404), `ACCOUNT_SUSPENDED`(403, 정지된 계정 로그인), `UPLOAD_TOO_LARGE`(413), `UNSUPPORTED_MEDIA`(415), `ALREADY_DELETED`(410, 삭제한 녹화), `UNDO_EXPIRED`(410, 서버가 정한 되살리기 기한 초과)
- **비동기 분석**: 영상 분석은 몇 분이 걸려서 요청 즉시 `202`와 `analysisId`를 돌려줘요. 프론트는 `GET /analyses/{id}`를 2\~3초마다 조회하거나 SSE(`/analyses/{id}/events`)로 단계 진행을 받아요. 단계는 `QUEUED → EXTRACTING → ANALYZING → SCORING → DONE`(실패 시 `FAILED`)이에요.
- **파일 업로드**: 큰 영상은 서버를 거치지 않고 사전 서명 URL로 직접 올려요(3단계: 업로드 URL 발급 → 스토리지 PUT → 완료 통지).
- **분석 항목 키**: `pace`(발화 속도), `delivery`(전달력), `confidence`(자신감), `tone`(톤앤매너), 종합은 `total`이에요. 점수는 0\~100 정수예요.


### 1-1. v2 상세 계약: 전송·타입·응답

- HTTPS/WSS만 사용한다. JSON 요청은 `Content-Type: application/json`. 바이너리는 3-2/3-3을 따른다. 성공은 단건/객체 `{ "data": {...} }`, 배열 목록 `{ "data": [...], "page": {...} }`, `204`는 본문이 없다. 표의 `items[]`는 목록 항목을 뜻하며 실제 최상위 응답에는 `items`를 중복 포장하지 않는다. `history.series`, `calendar.events`, `qa`처럼 도메인 객체의 배열은 유지한다.
- ID(`id`, `projectId`, `sessionId`, `analysisId`, `uploadId`, `assignmentId`, `jobId`, `userId`, `videoId`, 평가 ID)는 불투명한 비어 있지 않은 string이다. `version`, `modelVersion`, `rubricVersion`, `calibrationVersion`도 string이며 순서를 문자열로 비교하지 않는다.
- `roundNo`, 경로 `{n}/{m}`, `seq`는 1부터 시작하는 integer. 회차 번호는 프로젝트 내부에서 유일하고 삭제·실패로 생긴 번호를 재사용하지 않는다. `recordingGeneration`은 1부터 시작하는 integer다.
- 시각은 UTC RFC 3339 string(`2026-11-02T02:00:00Z`), 날짜는 `YYYY-MM-DD`, 달은 `YYYY-MM`. 화면이 KST로 변환한다. 일정의 날짜 경계 및 KPI 집계 시간대는 8-2 확인 필요다. `finalDate`는 시각이 아닌 날짜다.
- `sizeBytes`, `count`, 카운터는 0 이상 integer(요청 `count`는 1 이상). 시간 길이·`atSec`·`startSec`·`endSec`·`elapsedSeconds`는 0 이상 number, `targetSeconds`는 양수 integer다. 타임라인 구간은 `0 <= startSec < endSec <= durationSeconds`다.
- 점수는 항목별 0~100 integer, 점수 차이는 -100~100 integer다. 비율 필드는 0~1 number, 퍼센트는 0~100 number다. 평균·통계는 number, 표본이 없으면 `null`이다. `progressPercent`는 0~100 integer, `etaSeconds`는 0 이상 integer 또는 추정 불가 시 `null`이다.
- `true/false`는 boolean이며 문자열·숫자 대용을 허용하지 않는다. enum은 대소문자를 구별하고 표에 없는 값은 거부한다. `name`, `topic`, `label`, `question`, `answerDirection`, `text`, `guide`, `reason`, `memo`는 string이다. 식별 이름·주제·질문·안내는 공백만 허용하지 않는다. 선택 메모는 생략 또는 빈 문자열을 허용하되 `null`은 허용하지 않는다. 문자열 최대 길이·비밀번호 정책은 8-2에서 확인한다.
- 요청 표의 `?`만 선택 필드다. 객체 요청은 별도 규칙이 없으면 표의 필드가 모두 필수다. 응답 표의 필드는 항상 존재하며 아래에서 명시한 경우에만 `null`이다. 배열은 값이 없으면 `[]`, boolean은 기본 의미가 불분명한 `null`을 쓰지 않는다.
- `PATCH`는 생략한 필드를 유지하며 적어도 하나의 필드가 필요하다. `finalDate:null`만 발표일 해제를 뜻한다. 생성 시 `finalDate`는 필수 키이고 date 또는 `null`이다. 프로젝트 `done` 생성 기본값은 `false`다. 허용되지 않은 요청 필드는 `400 VALIDATION_FAILED`다. 클라이언트는 응답의 신규 필드를 무시할 수 있어야 한다.
- 목록 공통 쿼리는 `page=0`, `size=20`; page는 0 이상, size는 1~100 integer다. `page{number,size,total}`의 total은 필터 적용 후 개수다. 원본에 페이지를 명시하지 않은 배열도 목록 엔드포인트는 이 규칙을 따른다. 도메인 객체 내부 배열은 페이지 분할하지 않는다. 기본 정렬은 `createdAt DESC,id ASC`; 회차·시계열은 `roundNo ASC`, 배정 목록은 `videoIndex ASC`다.
- `GET /projects`의 status 기본값은 `active`; assignments 기본값은 `todo`; history item 기본값은 `total`이다. `month`는 필수, compare의 with는 선택이다. 다른 필터 생략은 전체다. 대시보드 `asOf`와 validation `version`의 생략 기준은 7-5를 따른다.
- `Cache-Control: no-store`를 인증·개인 리포트·서명 URL 응답에 적용한다. 서버는 `X-Request-Id`를 반환한다. 브라우저 저장소·접근 로그에 비밀번호, 토큰, 서명 URL, 영상·음성 원문을 기록하지 않는다.

### 1-1a. 공통 도메인 사전 보완

별도 상세 스키마에 없는 요약 필드는 아래 타입을 적용한다. `?`는 요청 선택 여부에만 쓰며 응답 null 허용은 명시된 경우로 한정한다.

| 영역 | 타입·의미 |
| --- | --- |
| user | id/name/email/role/createdAt 필수, role=`USER|EXPERT|ADMIN`; email은 이메일 형식 string |
| project | id/name/topic 필수 string, finalDate=date 또는 null, done=boolean, createdAt=시각; 목록 집계·rounds는 해당 조회에서만 포함 |
| 요약·일정 | calendar.events의 date는 date, type=`FINAL|PRACTICE`, projectId/label은 string. calendar 같은 날 여러 연습 이벤트는 회차별로 반환하며 roundNo는 PRACTICE에서 integer, FINAL에서 null |
| discard recap | elapsedSeconds=number, alertCount=integer, topAlert=string 또는 안내 없으면 null, alerts는 `{atSec,kind,text,positive}` 배열. kind는 5장의 alert enum |
| metrics | pace.state=`LOW|OK|FAST`, syllablesPerMin=0 이상 number; volume.state=`LOW|OK|HIGH`; gaze.state=`AUDIENCE|AWAY`. 각 객체는 추정 불가 시 null |
| 대시보드 | signups/weeklyPractices/funnel.count는 integer, liveShare/uploadShare/analysisSuccessRate/discardRate/undoRate는 0~1 number 또는 분모 없으면 null, avgAnalysisSeconds는 number 또는 null |
| attention | type/status는 string 분류 코드, text는 string, link는 앱 내부 경로 string. 분류 코드 목록·대응 경로는 KPI 기준과 함께 확인 필요 |
| 실패 목록·차이 | reason=사용자용 string, retryable=boolean, gap=0~100 number, itemKey는 분석 항목 key |
| 평가자 관리 | done/total은 integer, agreement.meanAbsGap는 number 또는 null; invitationId는 불투명 string, invitation status=`PENDING` |

### 1-2. 권한·오류·재시도·멱등성

역할 검사는 리소스 소유권/배정 검사와 별개다. USER는 자기 프로젝트·회차·세션·분석·업로드만, EXPERT는 자기 배정만 접근한다. ADMIN 역할이 영상 재생 권한을 자동 부여하지 않는다. 타인의 식별자를 사용하면 존재 여부를 숨기기 위해 `404 NOT_FOUND`, 역할 자체가 맞지 않으면 `403 FORBIDDEN`을 반환한다.

| HTTP | code | 발생 조건 / 클라이언트 처리 |
| --- | --- | --- |
| 400 | VALIDATION_FAILED | 형식·필수·enum·범위 오류. fields의 JSON 경로로 수정 |
| 401 | UNAUTHENTICATED | 토큰 누락·만료·폐기. refresh 1회 후 실패하면 로그인 |
| 403 | FORBIDDEN / ACCOUNT_SUSPENDED / CONSENT_REQUIRED | 역할·정지·유효한 동의 부재. 자동 반복 금지 |
| 404 | NOT_FOUND / NO_COMPARABLE_ROUND | 자원 없음/접근 불가 또는 비교 가능한 이전 회차 없음 |
| 409 | INVALID_STATE / IDEMPOTENCY_CONFLICT / CHUNK_CONFLICT / UPLOAD_INCOMPLETE / REPORT_NOT_READY / VERSION_MISMATCH / OPERATION_IN_PROGRESS | 현재 상태·중복 내용·버전 충돌. 상태 재조회 후 판단 |
| 410 | ALREADY_DELETED / UNDO_EXPIRED / UPLOAD_EXPIRED | 삭제된 영상·되살리기 기한 초과·만료 업로드 |
| 413 | UPLOAD_TOO_LARGE | 업로드 또는 WS 메시지 크기 한도 초과 |
| 415 | UNSUPPORTED_MEDIA | 실제 미디어/인코딩 미지원 |
| 429 | RATE_LIMITED | `Retry-After`(초) 이후 재시도 |
| 500 / 503 | INTERNAL_ERROR / TEMPORARILY_UNAVAILABLE | 요청 ID 기록, 안전한 요청만 지수 백오프 재시도 |

```json
{
  "error": {
    "code": "INVALID_STATE",
    "message": "녹화를 마친 뒤 저장해 주세요.",
    "fields": {},
    "details": {"currentState": "RECORDING", "allowedStates": ["FINISHED"]},
    "retryable": false,
    "requestId": "req_example"
  }
}
```

`error.code/message/fields/details/retryable/requestId`는 필수다. fields는 string→string 객체, details는 코드별 객체(없으면 `{}`)다. 스택·내부 경로·민감 정보를 노출하지 않는다. `retryable`은 동일 작업의 재시도 가능성을 뜻하며 POST의 중복 방지를 대신하지 않는다.

- 모든 업무 POST(생성, complete, save, undo, 재생성, 평가 제출, 관리자 작업)에는 `Idempotency-Key` string이 필수다. 로그인·refresh·logout과 WS 티켓 발급은 제외한다. 키는 클라이언트가 작업 의도별로 생성하며 재전송은 같은 키와 본문을 쓴다.
- 서버는 `(인증 주체 또는 가입 요청의 정규화 이메일, HTTP method, 정규화 경로, key)`에 요청 해시와 응답 상태·본문·Location을 저장한다. 같은 키·같은 요청은 최초 결과를 재생하고, 다른 본문은 `409 IDEMPOTENCY_CONFLICT`, 처리 중이면 `409 OPERATION_IN_PROGRESS`와 `Retry-After`를 반환한다. 영구 실패는 재생하고, 실행 전의 인증/검증 실패는 키를 소비하지 않는다.
- 키 보관 시간은 8-2에서 확정해야 한다. 키 만료와 무관하게 upload→round, session→round, assignment→최종 평가, analysis→retry attempt에는 DB 유일성/조건부 상태 전이를 적용하여 이중 생성하지 않는다. save와 undo가 다른 키로 호출되어도 동일 회차·분석을 반환한다.
- PUT/DELETE/PATCH는 같은 값을 반복 적용해도 추가 부작용이 없어야 한다. DELETE 재호출은 접근 가능한 삭제 표식이 있으면 `204`. 이미 삭제한 영상의 GET은 `410`. 외부 큐 발행은 상태 변경과 원자적으로 연결하여 작업 유실·중복 실행에 대비한다.
- 일반 생성 `201`, 비동기 접수 `202`, 동기 성공 `200`, 무본문 `204`. `201/202`는 조회 가능한 자원에 `Location`을 제공한다. 네트워크 시간 초과가 실패를 뜻하지 않으므로 재시도 전에 같은 키 또는 조회 API로 확인한다.

## 2. 인증 · 계정

회원가입은 항상 `USER`로 만들어지고, 역할 변경은 관리자 API(섹션 7)로만 할 수 있어요. 로그인 응답의 `role`로 프론트가 시작 화면을 정해요(이용자 `/me`, 평가자 `/expert/home`, 관리자 `/admin`).

| Method | Path | 권한 | 설명 | 요청 → 응답 핵심 필드 |
| --- | --- | --- | --- | --- |
| POST | `/auth/signup` | 공개 | 회원가입 | `name, email, password, agreements{terms, privacy, videoAnalysis}, agreementVersions` → `user, accessToken, accessTokenExpiresAt, refreshToken, refreshTokenExpiresAt` |
| POST | `/auth/login` | 공개 | 로그인 | `email, password` → `user{id,name,email,role}, accessToken, refreshToken`. 정지된 계정이면 `ACCOUNT_SUSPENDED` |
| POST | `/auth/refresh` | 공개 | 토큰 재발급 | `refreshToken` → `accessToken, accessTokenExpiresAt, refreshToken, refreshTokenExpiresAt` |
| POST | `/auth/logout` | 로그인 | 리프레시 토큰 폐기 | `refreshToken` → `204` |
| GET | `/me` | 로그인 | 내 정보 | → `id, name, email, role, createdAt` |
| PATCH | `/me` | 로그인 | 이름 변경(계정 설정 화면) | `name` → `user` |
| DELETE | `/me` | 로그인 | 계정 삭제. 모든 프로젝트·영상·리포트가 함께 삭제돼요 | → `204` |

비밀번호 찾기는 프로토타입에서 "준비 중"이라 이 초안에는 넣지 않았어요.


### 2-1. v2 상세 계약: 인증과 동의 입력

- signup의 name/email/password/agreements는 필수다. agreements의 terms/privacy/videoAnalysis는 boolean이고 각 약관의 버전 string을 `agreementVersions{terms,privacy,videoAnalysis}`에 함께 보낸다. 약관별 필수 동의 여부는 8-2 확인 필요이며, 영상 분석은 실제 업로드·라이브 시작 시 명시적 동의를 다시 검증한다. 이메일 정규화·중복 정책은 8-2에서 확정한다. 이미 등록된 이메일 처리 코드는 `409 EMAIL_ALREADY_EXISTS`다.
- signup `201`, login/refresh `200`. 인증 응답은 `user{id,name,email,role,createdAt},accessToken,accessTokenExpiresAt,refreshToken,refreshTokenExpiresAt`를 포함한다. refresh는 `refreshToken`만 받아 새 토큰 쌍과 각 만료 시각을 반환한다. user는 refresh 응답에서 제외한다. refresh 토큰은 회전하고 재사용을 탐지하면 해당 토큰 계열을 폐기한다.
- refresh는 Bearer 인증을 요구하지 않지만 유효한 refresh token이 필요하다. logout은 자기 토큰만 폐기하며 반복 호출은 `204`. 동시 refresh를 클라이언트에서 직렬화한다. 로그인·갱신 토큰 수명과 회전 응답 유실 시 복구 정책은 8-2에서 확정한다.
- 역할 변경·정지·계정 삭제 이후의 새 HTTP 요청/WS 재인증은 최신 계정 상태를 검사한다. next는 허용된 앱 내부 경로만 허용하여 외부 리다이렉트를 차단한다.
- 동의 기록은 userId, purpose, policyVersion, granted(boolean), recordedAt, source, 관련 sessionId/uploadId를 서버에 남긴다. 카메라·마이크 브라우저 권한 허용과 서비스의 영상 분석 동의는 별개다. 동의 API/철회 화면은 범위에 추가하지 않는다. 철회 접수 방식은 8-2에 남긴다.
- `DELETE /me`의 204는 접근 차단과 삭제 예약의 성공이다. 프로젝트·영상·리포트·진행 작업의 접근을 즉시 차단하고 비동기 물리 삭제를 수행한다. 법정 보존·백업·감사 로그의 보존 범위 및 완료 기한은 8-2 확인 필요이며 즉시 물리 소거 완료로 표현하지 않는다.

```json
{
  "name": "발표자",
  "email": "speaker@example.com",
  "password": "example-only-password",
  "agreements": {"terms": true, "privacy": true, "videoAnalysis": true},
  "agreementVersions": {"terms": "terms-example", "privacy": "privacy-example", "videoAnalysis": "analysis-example"}
}
```

## 3. 프로젝트 · 연습 세션

발표 하나가 프로젝트이고, 연습할 때마다 회차(round)가 하나씩 쌓여요. 회차는 라이브 또는 업로드 방식(`mode`)으로 만들어지고, 저장하면 분석이 시작돼요. 연습 세션은 "녹화하는 동안의 상태"이고, 저장하기 전에는 회차가 아니에요.

### 3-1. 프로젝트 (내 발표 프로젝트, 새 연습)

| Method | Path | 권한 | 설명 | 요청 → 응답 핵심 필드 |
| --- | --- | --- | --- | --- |
| GET | `/projects?status=active\|done\|all` | USER | 내 발표 프로젝트 목록 | → `id, name, topic, finalDate, done, roundCount, uploadCount, liveCount, latestTotal, deltaFromFirst, bestGainItem, weakestItem, trendSeries[]`(카드의 추이·항목 바) |
| POST | `/projects` | USER | 새 프로젝트 만들기 | `name, topic, finalDate` → `project` |
| GET | `/projects/{id}` | USER | 프로젝트 상세 | → `project, rounds[]` |
| PATCH | `/projects/{id}` | USER | 이름·주제·발표일 수정, 발표 완료 표시 | `name?, topic?, finalDate?, done?` → `project` |
| DELETE | `/projects/{id}` | USER | 프로젝트 삭제(모든 회차·리포트 함께) | → `204` |

### 3-2. 영상 업로드 연습

| Method | Path | 권한 | 설명 | 요청 → 응답 핵심 필드 |
| --- | --- | --- | --- | --- |
| POST | `/projects/{id}/uploads` | USER | 업로드 준비. 영상 형식·크기 검사 후 사전 서명 URL 발급 | `fileName, sizeBytes, contentType, checksumSha256, consentVideoAnalysis(true 필수), agreementVersions` → `uploadId, uploadUrl, expiresAt` |
| POST | `/projects/{id}/uploads/{uploadId}/complete` | USER | 업로드를 마친 뒤 회차를 만들고 분석 시작 | `memo?` → `202 { roundNo, analysisId }` |

프로토타입의 "샘플 영상으로 체험"은 실제 서비스에는 없어요(시연용).

### 3-3. 라이브 연습

연습 중 실시간 안내는 WebSocket으로 주고받고(섹션 5), 녹화 영상은 조각(chunk) 단위로 올려요. "저장하지 않고 끝내기"를 누르면 영상은 삭제 대기 상태가 되고, 서버가 반환한 `undoUntil` 전에는 되살릴 수 있어요(원본 화면의 30초는 확인 필요). "바로 삭제하기"는 그 대기를 건너뛰고 접근·되살리기를 즉시 차단하고 물리 삭제를 예약해요.

| Method | Path | 권한 | 설명 | 요청 → 응답 핵심 필드 |
| --- | --- | --- | --- | --- |
| POST | `/projects/{id}/live-sessions` | USER | 연습 시작(카메라·마이크 동의 후) | `targetSeconds, consentCameraMic(true 필수), consentVideoAnalysis(true 필수), agreementVersions` → `sessionId, status, wsUrl, wsTicket, wsTicketExpiresAt, chunkUploadPathTemplate, recordingGeneration` |
| PUT | `/live-sessions/{sessionId}/chunks/{seq}` | USER | 녹화 조각 업로드 | 바이너리 + generation·체크섬 헤더 → `204` |
| POST | `/live-sessions/{sessionId}/pause` | USER | 일시정지 | → `{ status:"PAUSED", elapsedSeconds }` |
| POST | `/live-sessions/{sessionId}/resume` | USER | 이어서 하기 | → `{ status:"RECORDING" }` |
| POST | `/live-sessions/{sessionId}/restart` | USER | 다시 하기(지금까지 녹화 삭제, 이력에 남기지 않음) | → `{ sessionId, recordingGeneration, status:"RECORDING" }` |
| POST | `/live-sessions/{sessionId}/finish` | USER | 타이머 종료 또는 "마치기". 저장 여부는 다음 단계에서 선택 | `lastChunkSeq, durationSeconds` → `{ elapsedSeconds, alertCount, status:"FINISHED" }` |
| POST | `/live-sessions/{sessionId}/save` | USER | 저장하고 분석 시작 | → `202 { roundNo, analysisId }` |
| POST | `/live-sessions/{sessionId}/discard` | USER | 저장하지 않고 끝내기. 영상은 `undoUntil`까지만 되살릴 수 있음(기간 확인 필요) | → `{ undoUntil, recap{ elapsedSeconds, alertCount, topAlert, alerts[] } }` |
| POST | `/live-sessions/{sessionId}/undo-discard` | USER | `undoUntil` 전에 되살리고 저장·분석 | → `202 { roundNo, analysisId }`. 시간 초과면 `UNDO_EXPIRED` |
| DELETE | `/live-sessions/{sessionId}` | USER | 바로 삭제하기. 녹화 접근·되살리기를 즉시 차단하고 물리 삭제 예약 | → `204` |

`discard` 응답의 `recap`은 "저장하지 않고 마쳐어요" 화면에서 연습 시간, 받은 안내, 다음에 신경 쓸 점을 한 번만 보여주는 데 쓰여요. 녹화 영상과 이 요약은 이력에 저장하지 않아요.


### 3-4. v2 상세 계약: 업로드 완료와 회차 생성

**업로드 연습**은 단일 사전 서명 PUT 방식을 사용한다. 원본의 `uploadUrl`을 유지하되 `uploadMethod:"PUT", uploadHeaders, expiresAt`를 반드시 반환한다. 스토리지 요청에는 앱 Bearer 토큰을 보내지 않는다. 앱 서버의 인증된 준비/완료 API와 스토리지의 서명 인증을 혼용하지 않는다.

1. 준비 시 파일 크기·지원 MIME·파일명·SHA-256(소문자 64자리 hex)·소유권·동의 버전을 검증하고 `uploadId`를 발급한다. 응답 상태는 `201`. 서버가 정한 객체 키만 사용하고 파일명은 경로로 해석하지 않는다.
2. 브라우저는 응답의 URL/method/headers 그대로 원본 바이너리를 전송한다. `multipart/form-data`가 아니다. 스토리지 CORS는 허용된 앱 origin, PUT, 필요한 헤더만 허용한다. ETag를 SHA-256으로 간주하지 않는다.
3. 스토리지 PUT 성공 후 앱 complete를 호출한다. 요청은 선택 memo만 포함하며 빈 객체도 허용한다. 서버는 객체 존재·실제 바이트 수·체크섬·미디어 형식·재생 가능 여부를 검증한다. 헤더 선언만으로 검사를 통과시키지 않는다. 미완료는 `409 UPLOAD_INCOMPLETE`, 크기·형식 오류는 413/415, 해시 불일치는 `400 CHECKSUM_MISMATCH`다.
4. 검증 후 회차와 분석 작업을 한 번만 생성하고 `202 {data:{projectId,roundNo,analysisId}}`와 `Location: /api/v1/analyses/{analysisId}`를 반환한다. 검증 실패는 회차를 만들지 않는다. 같은 uploadId의 반복 complete는 기존 결과를 반환하며 memo를 수정하지 않는다.

업로드 상태는 `PREPARED → VERIFYING → COMPLETED`, 만료 시 `EXPIRED`, 확정 검증 실패 시 `REJECTED`다. PUT 자체는 저장소 작업이므로 앱 상태를 확정하지 않는다. VERIFYING 중 반복 complete는 OPERATION_IN_PROGRESS다. 만료된 URL은 새 준비 요청으로 새 uploadId를 만들며 기존 미완료 객체는 정리한다. 만료/삭제된 객체는 complete할 수 없다. MIME 허용 목록·최대 크기·영상 길이·URL TTL·미완료 객체 정리 기한은 8-2 확인 필요다. 이 계약에는 멀티파트 업로드를 추가하지 않는다.

```json
{
  "data": {
    "uploadId": "upl_example",
    "uploadUrl": "https://storage.example.com/upload/example?signature=example",
    "uploadMethod": "PUT",
    "uploadHeaders": {"Content-Type": "video/webm"},
    "expiresAt": "2026-11-02T02:10:00Z"
  }
}
```

### 3-5. v2 상세 계약: 라이브 녹화와 상태 전이

라이브 chunk는 **앱 서버의 인증된 PUT**으로 통일한다. `chunkUploadUrl`은 제거하고 `chunkUploadPathTemplate:"/api/v1/live-sessions/{sessionId}/chunks/{seq}"`를 반환한다. 라이브도 스토리지 서명 방식으로 해석하지 않는다. 요청 헤더는 Bearer, `Content-Type`, `X-Recording-Generation`, `X-Checksum-Sha256`가 필수다. WS 프레임 seq와 chunk seq는 별개다.

- seq는 각 generation에서 1부터 증가한다. 서버는 `(sessionId,generation,seq)`를 유일 키로 사용한다. 같은 seq·동일 해시는 `204`, 다른 내용은 `409 CHUNK_CONFLICT`. 과거 generation은 `409 VERSION_MISMATCH`. 전송 순서가 뒤바뀌어도 저장할 수 있다.
- pause/finish 전에 생성된 조각은 PAUSED/FINISHED에서도 업로드를 허용한다. finish 요청은 `lastChunkSeq`(1 이상 integer), `durationSeconds`(0보다 큰 number)를 필수로 보내 녹화를 봉인한다. 이후 seq가 lastChunkSeq보다 큰 조각은 거부한다. finish 후 미전송 조각을 보충하고 save/undo 전에 1..lastChunkSeq의 누락·중복·조립 가능성을 검증한다. 빈 녹화 finish는 `400 VALIDATION_FAILED`다.
- 조각은 독립 재생 파일임을 가정하지 않는다. 같은 generation의 녹화 컨테이너를 순서대로 조립해 검증한다. 브라우저 코덱·chunk 크기/주기·전송 재시도 한도는 8-2에서 확정한다. 제한 초과는 413, 누락은 `409 UPLOAD_INCOMPLETE`다.
- 누적 연습 시간은 일시정지 시간을 제외한 녹화 길이다. 서버가 저장 시 실제 미디어 길이와 대조한다. 타이머 만료도 finish와 동일한 상태 전이를 수행한다.

| 현재 상태 | 동작 | 다음 상태 / 규칙 |
| --- | --- | --- |
| 없음 | create | RECORDING, generation=1, 아직 회차 없음 |
| RECORDING | pause | PAUSED, 반복 pause는 현재 값 반환 |
| PAUSED | resume | RECORDING, 반복 resume는 현재 값 반환 |
| RECORDING / PAUSED | restart | RECORDING, generation 증가, 이전 조각·안내·타이머 초기화, WS 재연결 |
| RECORDING / PAUSED | finish | FINISHED, WS 종료; 반복 동일 manifest는 기존 결과 |
| FINISHED | save | SAVED, 영상 검증 후 회차·분석 1개 생성 |
| FINISHED | discard | DISCARD_PENDING, 서버 시각 기준 undoUntil 발급 |
| DISCARD_PENDING | undo-discard | 기한 전에 원자적 선점·검증 후 SAVED, 회차·분석 생성 |
| DISCARD_PENDING | 기한 도래 | DELETED, 되살리기 차단·물리 삭제 예약 |
| RECORDING / PAUSED / FINISHED / DISCARD_PENDING | DELETE | DELETED, 즉시 접근 차단·되살리기 차단·물리 삭제 예약 |
| SAVED | save / undo-discard | 기존 회차·분석 반환, 추가 생성 없음 |

그 밖의 전이는 `409 INVALID_STATE`다. SAVED 세션 DELETE는 기존 회차를 우회 삭제하지 않도록 409이며 프로젝트 삭제 경로를 사용한다. finish 반복에서 manifest가 바뀌면 409다. discard 반복은 최초 undoUntil/recap을 반환하여 시간을 연장하지 않는다. `now < undoUntil`만 되살릴 수 있고 경계와 이후는 410이다. undo와 삭제가 경합하면 서버의 조건부 상태 갱신에 먼저 성공한 하나만 유효하다. 유효한 undo가 검증 실패하면 기한 내 DISCARD_PENDING으로 복귀하며 기한은 연장하지 않는다.

save/undo의 검증·회차 생성·분석 큐 등록은 하나의 논리 작업이다. 프로젝트 삭제가 선행되면 저장을 거부하고, 저장이 선행되어도 프로젝트 삭제 시 그 결과를 함께 삭제한다. restart 후 과거 WS·업로드를 거부한다. restart는 세션 ID를 유지하지만 generation을 변경한다. discard recap은 원본대로 이력에 저장하지 않으며 되살리기 응답의 재생을 위한 임시 보관만 허용한다. recap 보관 만료와 안내 로그 삭제 기한은 8-2에서 확정한다.

화면 복귀·충돌 해소용 기술 조회 `GET /live-sessions/{sessionId}`(USER, 소유자)를 추가한다. 응답은 `sessionId,status,recordingGeneration,elapsedSeconds,lastChunkSeq,receivedChunkSeqs,undoUntil,roundNo,analysisId`다. 마지막 네 의미 중 lastChunkSeq는 finish 전 null, undoUntil은 폐기 대기 외 null, roundNo/analysisId는 SAVED 전 null이다. receivedChunkSeqs는 integer 배열이다. DELETED 조회는 410이다.

```json
{
  "data": {
    "projectId": "prj_example",
    "roundNo": 2,
    "analysisId": "ana_example"
  }
}
```

## 4. 분석 · 리포트 · 이력 · 일정

리포트 한 장이 회차 하나에 해당해요. 리포트 안에 점수, 시간축, 구간별 피드백, 예상 질의응답이 함께 들어 있어요. 분석은 한국어 발화 기준(군말, 말끝 처리, 존대 표현)으로 하고, 점수는 분석 시작 시 고정한 모델·루브릭·보정 버전(섹션 7)을 따른다.

### 4-1. 분석 진행

| Method | Path | 권한 | 설명 | 요청 → 응답 핵심 필드 |
| --- | --- | --- | --- | --- |
| GET | `/analyses/{analysisId}` | USER | 진행 상태 조회(폴링) | → `status(QUEUED\|EXTRACTING\|ANALYZING\|SCORING\|DONE\|FAILED), progressPercent, etaSeconds, projectId, roundNo` |
| GET | `/analyses/{analysisId}/events` | USER | 단계 진행 SSE(폴링 대신 선택) | 이벤트 `progress`, `done`, `failed` |
| POST | `/analyses/{analysisId}/notify` | USER | "끝나면 알려주세요" 알림 신청 | → `204` |

### 4-2. 리포트 · 비교

| Method | Path | 권한 | 설명 | 요청 → 응답 핵심 필드 |
| --- | --- | --- | --- | --- |
| GET | `/projects/{id}/rounds/{n}/report` | USER | N회차 분석 리포트 | → `roundNo, mode, durationSeconds, scores{total,pace,delivery,confidence,tone}, deltaFromPrev{...}, modelVersion, rubricVersion, calibrationVersion, language:"ko", timeline{pace[],volume[],pitch[],gazeSegments[],gestureSegments[]}, segments[{index,startSec,endSec,label,good{title,detail},fix{title,detail}}], liveAlerts[{atSec,text,positive}], video{status}, qa[]` |
| GET | `/projects/{id}/rounds/{n}/compare?with={m}` | USER | 지난 회차와 비교. 생략하면 바로 앞 회차. 첫 회차면 `404` | → `items[{key, prev, current, delta}]` |
| GET | `/projects/{id}/rounds/{n}/video` | USER | 리포트 재생용 영상 서명 URL(보관 기간은 확인 필요, 삭제 후 `410`) | → `url, expiresAt` |

### 4-3. 예상 질의응답

리포트 안의 섹션이에요. 화면은 질문을 눌러 펼치면 답변 방향이 보여요. 질문은 프로젝트 주제와 발표 내용(음성 인식본)을 바탕으로 생성해요.

| Method | Path | 권한 | 설명 | 요청 → 응답 핵심 필드 |
| --- | --- | --- | --- | --- |
| GET | `/projects/{id}/rounds/{n}/qa` | USER | 예상 질의응답 목록(리포트 응답의 `qa[]`와 동일) | → `items[{id, question, answerDirection}]` |
| POST | `/projects/{id}/rounds/{n}/qa/regenerate` | USER | 질문 다시 생성 | `count?` → `items[]` |

### 4-4. 이력 · 추이 · 일정

| Method | Path | 권한 | 설명 | 요청 → 응답 핵심 필드 |
| --- | --- | --- | --- | --- |
| GET | `/projects/{id}/history?item=total\|pace\|delivery\|confidence\|tone` | USER | 이력·추이 화면의 그래프와 표 | → `series[{roundNo, date, mode, total, items{...}}], pendingRounds[{roundNo, analysisId}]` |
| GET | `/me/calendar?month=2026-11` | USER | 발표 일정 달력(프로젝트 최종 발표일과 연습한 날) | → `events[{date, type:"FINAL\|PRACTICE", projectId, label}]` |

프로젝트가 없거나 회차가 없으면 에러가 아니라 빈 배열을 돌려줘요(빈 상태 화면).


### 4-5. v2 상세 계약: 분석·리포트·중복 조회 정리

- 분석 상태는 원본의 `QUEUED → EXTRACTING → ANALYZING → SCORING → DONE`을 유지한다. 실행 중 어느 단계나 FAILED가 될 수 있다. DONE/FAILED는 해당 attempt의 종결 상태다. 진행률은 한 attempt 내 감소하지 않으며 DONE=100이다.
- 상태 조회 응답은 `analysisId,attempt,status,progressPercent,etaSeconds,projectId,roundNo,modelVersion,rubricVersion,calibrationVersion,createdAt,updatedAt,error`다. attempt는 1 이상 integer. error는 실패가 아니면 null, FAILED이면 `{code,message,retryable}`다. 실패 후 보고서는 준비되지 않으며 report GET은 `409 REPORT_NOT_READY`와 analysisId/status를 반환한다.
- 분석 접수 시 모델·루브릭·보정 버전을 고정한다. QUEUED부터 값은 null이 아니며, 유효한 버전 조합이 없으면 접수 자체가 `503 TEMPORARILY_UNAVAILABLE`다. 최초 분석과 관리자 재시도는 동일 회차를 사용한다. 재시도는 FAILED일 때만 attempt 증가 후 QUEUED로 이동하고 성공 리포트를 덮어쓰지 않는다. 동시 재시도는 하나만 생성한다. 재시도는 원래 버전 조합을 사용하며 버전 실행 자산이 없으면 `409 VERSION_UNAVAILABLE`이다.
- DONE은 점수·타임라인·구간·QA를 포함한 리포트가 읽기 가능하게 커밋된 뒤에만 표시한다. 실패·삭제된 회차는 pendingRounds에 성공으로 표시하지 않는다. history는 `series`(DONE), `pendingRounds`(실행 중), `failedRounds[{roundNo,analysisId,error}]`를 분리해 실패가 사라지지 않게 한다.
- `notify`는 사용자·analysisId 단위 중복 없는 구독 upsert다. 이미 완료된 작업이면 구독 상태를 기록하되 중복 발송하지 않는다. 알림 채널·허용 동의·실패 처리 기준은 8-2 확인 필요이며 임의 이메일/SMS 발송을 전제하지 않는다.

SSE는 fetch 기반 스트리밍으로 Authorization 헤더를 보낸다. 브라우저 기본 EventSource에 토큰 쿼리를 붙이지 않는다. 연결 시 현재 snapshot을 progress 또는 종결 이벤트로 제공하고, 이벤트는 `id`, `event`, `data`를 갖는다. data는 상태 조회와 같은 객체다. `Last-Event-ID`로 재개하며 보존 범위 밖이면 현재 snapshot을 보낸다. 중복 이벤트는 `(analysisId,attempt,eventId)`로 무시한다. 연결 유지는 주석 heartbeat, 종결 이벤트 후 연결 종료다. 이벤트 보존 시간·heartbeat 간격은 8-2 확인 필요다. SSE 실패 시 원본대로 2~3초 폴링으로 전환하고 DONE/FAILED에서 멈춘다.

```text
id: ana_example:1:3
event: progress
data: {"analysisId":"ana_example","attempt":1,"status":"ANALYZING","progressPercent":55,"etaSeconds":null,"projectId":"prj_example","roundNo":2,"modelVersion":"model-example","rubricVersion":"rubric-example","calibrationVersion":"cal-example","createdAt":"2026-11-02T02:00:00Z","updatedAt":"2026-11-02T02:00:20Z","error":null}

```

**리포트 필드 계약**

| 필드 | 타입·필수/null·의미 |
| --- | --- |
| roundNo / mode / durationSeconds | integer / `UPLOAD` 또는 `LIVE` / number, 모두 필수 |
| scores | `{total,pace,delivery,confidence,tone}` 모두 필수 integer. total 산식·가중치는 확인 필요 |
| deltaFromPrev | 같은 키의 차이 객체 또는 비교 가능한 이전 성공 회차가 없으면 null |
| modelVersion / rubricVersion / calibrationVersion / language | 필수 string, language는 `ko` |
| timeline | pace/volume/pitch/gazeSegments/gestureSegments 배열, 측정 불가이면 해당 배열 `[]` |
| segments | `{index,startSec,endSec,label,good,fix}` 배열. index는 1 이상, good/fix는 `{title,detail}` 또는 피드백 없으면 null |
| liveAlerts | `{atSec,text,positive}` 배열. 업로드 모드는 `[]` |
| video | `{status:"AVAILABLE\|DELETED\|EXPIRED"}`. report에 서명 URL을 중복 저장하지 않음 |
| qa | `{id,question,answerDirection}` 배열. QA GET은 동일한 현재 스냅샷 |

타임라인 pace는 `{atSec,syllablesPerMin}`, volume은 `{atSec,dbfs}`, pitch는 `{atSec,hz}`이며 수치는 number다. dBFS는 0 이하, hz는 양수다. gazeSegments는 `{startSec,endSec,state:"AUDIENCE|AWAY|UNKNOWN"}`, gestureSegments는 `{startSec,endSec,label}`다. 측정 실패를 0점·0Hz로 대체하지 않는다. 모델이 필수 점수를 만들 수 없으면 분석 FAILED로 처리한다. 허용 측정 결손 기준은 8-2에서 확인한다.

- 영상 URL은 **GET …/video 한 곳**에서만 발급한다. 반환은 `{data:{url,expiresAt}}`; report의 기존 videoPlayUrl은 video.status로 대체한다. 삭제/만료 후 보고서 유지 여부는 보관 정책에 따르고 영상 GET은 410이다.
- QA는 report의 qa를 정본으로 하며 GET …/qa는 `{data:{items:[...]}}` 형태의 호환 조회다(페이지 목록 아님). regenerate는 count 선택 양수 integer, 생략 시 현재 개수(현재 비어 있으면 기본 개수는 확인 필요)를 사용한다. `200 {data:{items:[...]}}`로 현재 QA를 원자 교체하고 이후 report/qa에 동일하게 반영한다. 실패하면 기존 목록을 유지한다. 동시 재생성은 409 OPERATION_IN_PROGRESS다.
- compare는 `{data:{items:[{key,prev,current,delta}],previousRoundNo,currentRoundNo,comparable,reason}}`. key는 total 및 네 항목이다. with 생략 시 번호가 작은 가장 가까운 DONE 회차를 선택한다. 다른 프로젝트/미완료 회차는 404/409다. 버전 조합이 다르면 `comparable:false,reason:"VERSION_MISMATCH",items:[]`를 반환한다. 원점수는 각 리포트에서 조회한다.
- 카드 latestTotal/weakestItem은 최근 DONE 기준이고 없으면 null, trendSeries는 `[{roundNo,total}]`다. deltaFromFirst/bestGainItem은 동일 버전 조합으로 비교할 수 있을 때만 값이 있으며 그 외 null이다. bestGainItem/weakestItem은 항목 key string이다. roundCount는 저장된 모든 회차, uploadCount/liveCount는 mode별 개수다. 프로젝트 상세 rounds는 `{roundNo,mode,analysisId,status,createdAt}` 배열이다. history의 date는 회차 생성 시각이며 UTC RFC 3339다.

```json
{
  "data": {
    "roundNo": 2,
    "mode": "UPLOAD",
    "durationSeconds": 10.5,
    "scores": {"total": 78, "pace": 80, "delivery": 76, "confidence": 79, "tone": 77},
    "deltaFromPrev": null,
    "modelVersion": "model-example",
    "rubricVersion": "rubric-example",
    "calibrationVersion": "cal-example",
    "language": "ko",
    "timeline": {
      "pace": [{"atSec": 1, "syllablesPerMin": 240}],
      "volume": [{"atSec": 1, "dbfs": -18.5}],
      "pitch": [{"atSec": 1, "hz": 180}],
      "gazeSegments": [{"startSec": 0, "endSec": 10.5, "state": "UNKNOWN"}],
      "gestureSegments": []
    },
    "segments": [{"index": 1, "startSec": 0, "endSec": 10.5, "label": "도입", "good": {"title": "분명한 도입", "detail": "주제를 먼저 소개했습니다."}, "fix": null}],
    "liveAlerts": [],
    "video": {"status": "AVAILABLE"},
    "qa": [{"id": "qa_example", "question": "핵심 근거는 무엇인가요?", "answerDirection": "발표에서 사용한 근거와 한계를 설명하세요."}]
  }
}
```
예시 점수는 total 산식이나 가중치를 규정하지 않는다.

## 5. 실시간 피드백 (WebSocket)

라이브 연습 중 말 속도, 음량, 시선을 1초 간격으로 보내고 안내 문구를 받아요. 여기의 안내는 연습을 돕는 용도이고, 리포트 점수는 저장한 영상을 처음부터 다시 분석해 계산해요. 현재 프로토타입의 실시간 항목은 말 속도·음량·시선 세 가지예요. 요구사항서(FR-05)와 범위가 맞는지는 원문을 보고 확인해야 해요.

**연결**: `wss://{host}/api/v1/live-sessions/{sessionId}/feedback?ticket=<oneTimeTicket>`. 장기·액세스 토큰을 URL에 넣지 않는다. 상세 인증·재연결 규칙은 5-1을 따른다. `finish` 후 서버가 연결을 닫는다.

| 방향 | type | 페이로드 | 설명 |
| --- | --- | --- | --- |
| 클라이언트 → 서버 | `frame` | `{ seq, atSec, audio(base64 PCM 조각), gaze{ x, y, onScreen } }` | 1초 단위 입력. 얼굴·시선 특징은 브라우저에서 뽑아 보내면 영상 전송을 줄일 수 있어요 |
| 클라이언트 → 서버 | `config` | `{ alertsEnabled }` | "안내 문구 켜짐/꺼짐" 토글. 꺼져 있어도 안내는 기록되고 화면에만 안 보여요 |
| 서버 → 클라이언트 | `metrics` | `{ atSec, pace{ state:"LOW\|OK\|FAST", syllablesPerMin }, volume{ state:"LOW\|OK\|HIGH" }, gaze{ state:"AUDIENCE\|AWAY" } }` | "지금 상태" 카드의 막대 3개 |
| 서버 → 클라이언트 | `alert` | `{ atSec, kind:"PACE\|VOLUME\|GAZE\|PRAISE\|PAUSE_HINT", text, positive }` | 영상 위 안내 토스트와 "받은 안내" 목록. 같은 종류는 일정 시간 간격을 두고 보내요 |
| 서버 → 클라이언트 | `status` | `{ state:"RECORDING\|PAUSED\|FINISHED", elapsedSeconds }` | 일시정지·재개와 타이머 동기화 |

**연결이 끊길 때**: 안내는 잠시 멈추지만 녹화는 계속돼요. 클라이언트는 지수 백오프로 다시 연결하고, 녹화 조각(섹션 3-3)은 WebSocket과 별개로 계속 올라가요.


### 5-1. v2 상세 계약: 브라우저 인증·프레임·재연결

- 세션 생성 응답에 소유자·sessionId·recordingGeneration에 묶인 단회용 불투명 wsTicket과 wsTicketExpiresAt을 제공한다. 재연결에는 `POST /live-sessions/{sessionId}/feedback-ticket`(USER, Bearer, 빈 본문, 200)을 호출하여 `{data:{wsUrl,wsTicket,wsTicketExpiresAt,recordingGeneration}}`를 받는다. 이는 인증 보조 API이며 새 화면/새 업무 기능이 아니다.
- 서버는 upgrade 때 Origin 허용 목록, 티켓 만료·미사용 여부, 최신 사용자 권한, 세션 RECORDING/PAUSED, generation을 검사하고 티켓을 원자 소비한다. URL 로그에서 ticket을 마스킹한다. accessToken/refreshToken을 query에 넣지 않는다. 만료·재사용 티켓은 upgrade 401, 권한은 403, 세션 상태는 409다.
- 연결된 상태에서의 인증 유효 기한은 발급 근거 accessTokenExpiresAt을 넘지 않는다. 만료 시 4401로 닫고 HTTP refresh 및 새 티켓으로 재연결한다. 로그아웃·정지·삭제 시 기존 연결도 폐기한다. 티켓 TTL, 동시 연결 수는 8-2에서 확정한다.
- frame은 `type,recordingGeneration,seq,atSec,audio,gaze` 필수다. audio는 `{encoding:"PCM_S16LE",sampleRateHz:16000,channels:1,data:"base64"}`다. WS 분석 입력용 규격이며 녹화 컨테이너와 다르다. 원본의 1초 프레임을 유지한다. gaze는 `{x,y,onScreen}` 또는 추정 불가 시 null; x/y는 0~1 number, onScreen은 boolean이다. atSec는 일시정지를 뺀 누적 녹화 시간이다.
- 서버는 generation/seq로 중복 프레임을 무시한다. 재연결 시 클라이언트는 seq를 초기화하지 않는다. 과거 프레임 재생을 요구하지 않으며 연결 중단 구간의 실시간 안내는 복원하지 않는다. 저장 영상의 사후 분석은 영향을 받지 않는다. PAUSED에서는 frame 처리를 중단한다.
- config의 alertsEnabled는 **화면 표시 여부**다. false여도 서버의 안내 생성·alert 이벤트·recap 집계는 계속한다. 재연결마다 config를 다시 보낸다. 상태 변경은 HTTP API가 정본이고 WS status는 통지다.
- metrics/alert/status는 원본 필드에 `type,eventId,recordingGeneration`을 필수 추가한다. eventId는 불투명 string이며 클라이언트는 중복 토스트를 제거한다. 감지 불가한 pace/volume/gaze는 해당 객체가 null이며 임의 OK로 표시하지 않는다. alert의 positive는 boolean이다.
- 정상 종료 1000, 잘못된 메시지/순서 정책 1008, 크기 초과 1009, 일시 서버 오류 1011, 재시작 1012, 인증 만료 4401, 권한 철회 4403. 가능한 경우 종료 전 `{type:"error",code,message,retryable,eventId,recordingGeneration}`를 보낸다. 4403·FINISHED·DELETED에는 자동 재연결하지 않는다. 그 외에는 jitter 포함 지수 백오프를 사용하고 새 티켓을 발급한다. WS 단절만으로 녹화 상태를 바꾸지 않는다.

```json
{
  "type": "frame",
  "recordingGeneration": 1,
  "seq": 12,
  "atSec": 11,
  "audio": {"encoding": "PCM_S16LE", "sampleRateHz": 16000, "channels": 1, "data": "AAA="},
  "gaze": null
}
```
위 audio.data는 인코딩 형태만 보이는 축약 예시이며 실제 1초 프레임이 아니다. 실시간 임계값·알림 간격·FR-05 확장 여부는 8-2에서 결정한다.

## 6. 전문 평가자

평가자 화면에는 AI 점수가 나오지 않아야 해요(편향 방지). 아래 API의 응답에는 AI 점수 필드를 넣지 않고, 평가 영상은 비식별 처리된 키만 내려줘요. 평가 결과는 발표자 리포트에 직접 보이지 않고 점수 보정 기준을 만드는 데만 써요.

| Method | Path | 권한 | 설명 | 요청 → 응답 핵심 필드 |
| --- | --- | --- | --- | --- |
| GET | `/expert/overview` | EXPERT | 평가자 홈: 진행률과 기준표 | → `assignedCount, doneCount, rubric[{key,label,guide}]` |
| GET | `/expert/assignments?status=todo\|done` | EXPERT | 배정된 영상 목록 | → `items[{assignmentId, videoIndex, durationSeconds, status}]` |
| GET | `/expert/assignments/next` | EXPERT | 다음에 평가할 영상 | → `assignmentId, index, total, playUrl`. 남은 게 없으면 `204` |
| POST | `/expert/assignments/{assignmentId}/evaluation` | EXPERT | 평가 저장(저장하고 다음 영상) | `scores{pace,delivery,confidence,tone}(0~100), memo?, rubricVersion` → `{ done, total }` |
| PUT | `/expert/assignments/{assignmentId}/evaluation/draft` | EXPERT | 임시 저장 | `scores(부분 입력 가능), memo?, rubricVersion` → `204` |
| POST | `/expert/assignments/{assignmentId}/skip` | EXPERT | 건너뛰기 | `reason?` → `204` |

평가자가 끝낸 영상은 수정할 수 있게 할지는 정해야 해요(섹션 8의 확인 필요 항목).


### 6-1. v2 상세 계약: 평가 스냅샷과 중복 제출

- 배정에 `rubricVersion`을 고정하고 overview 및 next 응답에 반환한다. next는 GET이므로 배정을 생성하거나 기존 영상을 완료 처리하지 않는다. 응답의 index는 videoIndex와 같은 integer다. next의 playUrl에는 별도 `playUrlExpiresAt`을 포함하고 만료 시 next를 다시 조회한다. URL은 해당 평가자·배정 범위로 제한한다.
- 평가 목록 status는 `TODO|DRAFT|DONE|SKIPPED`이고 쿼리 todo는 TODO/DRAFT, done은 DONE을 뜻한다. skip은 SKIPPED로 전이하고 next에서 제외한다. 재노출/재배정 정책은 8-2 확인 필요다. overview doneCount는 DONE만, assignedCount는 전체 유효 배정 수다.
- draft의 scores 객체는 필수지만 네 항목은 각각 선택 integer이고 빈 객체를 허용한다. memo는 선택 string이다. PUT은 임시 저장 전체 교체이며 생략 항목은 draft에서 지운다. 최종 제출 scores는 네 항목 모두 필수이고 total은 입력받지 않는다. 요청은 `rubricVersion`을 포함하며 배정 버전과 다르면 409 VERSION_MISMATCH다.
- 최종 제출은 TODO/DRAFT→DONE을 원자 처리하고 assignmentId마다 최종 평가 하나만 생성한다. 최초 제출 응답은 `200 {data:{done,total}}`(카운터 integer). 같은 키 재전송은 최초 응답 재생이다. 이미 DONE에 다른 요청은 `409 EVALUATION_ALREADY_SUBMITTED`이며 수정 API로 암묵 처리하지 않는다. 완료 평가 수정 허용 여부는 확인 필요이고 이 문서는 수정 기능을 추가하지 않는다.
- AI 점수·리포트·발표자 신원 필드는 평가자 응답에서 제외한다. 비식별 키 제공은 영상 자체의 익명화를 보장하지 않는다. 얼굴·음성·발표 내용 식별 가능성 및 가림 처리 방식은 8-2에서 확인한다. 적법한 전문가 활용 동의가 확인되지 않은 영상은 배정하지 않는다.

```json
{
  "scores": {"pace": 80, "delivery": 75, "confidence": 78, "tone": 82},
  "memo": "핵심 내용을 분명하게 설명했습니다.",
  "rubricVersion": "rubric-example"
}
```

## 7. 관리자

관리자 API는 모두 `ADMIN`만 호출할 수 있고 아니면 `403`이에요. 변경을 일으키는 호출(역할 변경, 정지, 배정 등)은 감사 로그에 기록해요. 이용자의 영상 자체는 이 API로 내려주지 않아요.

### 7-1. 대시보드

| Method | Path | 설명 | 응답 핵심 필드 |
| --- | --- | --- | --- |
| GET | `/admin/dashboard?asOf=2026-10-30` | 서비스 현황 | `kpis{signups, weeklyPractices, liveShare, uploadShare, analysisSuccessRate, avgAnalysisSeconds}, funnel[{stage:"SIGNUP\|FIRST_PRACTICE\|ANALYZED\|REPRACTICE", count}], discard{discardRate, undoRate}, attention[{type, text, status, link}]` |
| GET | `/admin/analyses?status=FAILED` | 분석 실패 목록 | `items[{analysisId, reason, createdAt, retryable}]` |
| POST | `/admin/analyses/{analysisId}/retry` | 실패 분석 재시도 | `202` |

### 7-2. AI 점수 검증

이전에 마이페이지에 있던 기능을 관리자 쪽으로 옮겼어요.

| Method | Path | 설명 | 요청 → 응답 핵심 필드 |
| --- | --- | --- | --- |
| GET | `/admin/validation?version=v1\|v0` | AI·전문가 점수 비교 | → `evaluatedVideos, evaluators, meanAbsGapBefore, meanAbsGapAfter, byItem[{key, before, after}], scatter[{expert, ai}]` |
| GET | `/admin/validation/disagreements?minGap=15` | 차이가 큰 영상(재평가 대기) | → `items[{videoId, itemKey, gap}]` |
| POST | `/admin/validation/disagreements/{videoId}/reevaluate` | 재평가 요청 | `assigneeId?` → `204` |
| GET | `/admin/calibrations` | 보정 버전 목록 | → `items[{version, createdAt, basedOnCount, active}]` |
| POST | `/admin/calibrations` | 평가 결과로 새 보정 버전 계산(기울기·절편) | `{ basedOnEvaluationIds? }` → `202 { jobId, status:"QUEUED", version:null }` |
| POST | `/admin/calibrations/{version}/activate` | 보정 버전 적용. 이후 분석 점수에 반영돼요 | `204` |

### 7-3. 전문가 평가 관리

| Method | Path | 설명 | 요청 → 응답 핵심 필드 |
| --- | --- | --- | --- |
| GET | `/admin/experts` | 평가자 목록과 진행 | → `items[{id, name, email, done, total, lastActiveAt}], agreement{meanAbsGap}` |
| POST | `/admin/experts/invitations` | 평가자 초대 | `name, email` → `201` |
| POST | `/admin/experts/{expertId}/assignments` | 영상 배정 | `count` → `{ total }` |
| GET | `/admin/rubric` | 평가 기준표 | → `items[{key,label,guide}]` |
| PUT | `/admin/rubric` | 기준표 수정 | `items[], expectedVersion` → `204` |

### 7-4. 사용자 관리

| Method | Path | 설명 | 요청 → 응답 핵심 필드 |
| --- | --- | --- | --- |
| GET | `/admin/users?query=&role=&status=` | 사용자 목록·검색(이름 또는 이메일) | → `items[{id, name, email, role, joinedAt, practiceCount, status}]` |
| PATCH | `/admin/users/{userId}/role` | 역할 변경. 본인의 역할은 바꿀 수 없어요 | `role` → `user` |
| PATCH | `/admin/users/{userId}/status` | 이용 정지·해제. 본인은 정지할 수 없어요 | `status:"ACTIVE\|SUSPENDED"` → `user` |

데이터 관리(영상 보관·삭제 대기열, 동의 이력, 삭제 요청)와 운영·감사 로그는 프로토타입에서 "준비 중"이라 이 초안에는 없어요. 다음 단계에서 추가할 수 있어요.


### 7-5. v2 상세 계약: 비동기 보정·버전·집계

보정 계산 접수와 보정 버전 생성을 분리한다. `POST /admin/calibrations`의 요청 `basedOnEvaluationIds`는 선택 string 배열이며 중복 ID를 허용하지 않는다. 생략 시 서버는 실행 시점에 적격한 최종 평가 집합을 스냅샷으로 고정한다. 빈 배열·대상 없음은 `400 VALIDATION_FAILED`다. 적격성/최소 표본/집계 방식은 8-2 확인 필요이며 임의 기준으로 실행하지 않는다.

| Method | Path | ADMIN 응답/행동 |
| --- | --- | --- |
| POST | `/admin/calibrations` | `202 {data:{jobId,status:"QUEUED",version:null}}`, Location은 아래 작업 조회 |
| GET | `/admin/calibration-jobs/{jobId}` | 보정 비동기 작업 상태 조회. `{jobId,status,progressPercent,version,modelVersion,rubricVersion,evaluationCount,createdAt,updatedAt,error}` |
| GET | `/admin/calibrations` | 완료 버전 목록 `{version,createdAt,basedOnCount,active,modelVersion,rubricVersion}` + 공통 page |
| POST | `/admin/calibrations/{version}/activate` | 완료되고 호환되는 버전만 활성화. `204`, 미완료·비호환은 409 |

- 작업 상태는 `QUEUED → RUNNING → SUCCEEDED` 또는 QUEUED/RUNNING→FAILED다. version은 SUCCEEDED 때만 비어 있지 않은 string이고 그 외 null이다. error는 FAILED 때 `{code,message,retryable}`, 그 외 null. progressPercent는 성공=100, 실행 중 0~99다. modelVersion/rubricVersion은 접수 시 고정한 string, evaluationCount는 고정 표본 개수 integer다.
- 보정 작업은 동결된 평가 ID·평가 리비전·모델/루브릭 조합·계산 설정을 기록한다. 서로 다른 루브릭/모델 기준의 점수를 근거 없이 섞지 않는다. 잘못된 조합은 409 VERSION_MISMATCH다. 실패 작업은 버전 목록에 나타나지 않으며 새 키의 POST로 다시 접수할 수 있다. 같은 키는 기존 실패 작업을 반환한다.
- 보정 버전은 불변이다. 기울기·절편, 생성 시각, 표본 목록의 내부 감사 참조를 보관한다. 보정 계수 산식·클리핑·정수 반올림·total 가중치·검증 데이터 분리 방식은 8-2 확인 필요다. 사용자 리포트에 원본 전문가 평가를 노출하지 않는다.
- 활성 버전 전환은 원자적이며 모델/루브릭 조합별 활성 보정 하나만 존재한다. 동시에 활성화 요청이 오면 직렬화하고 감사 로그에 최종 순서를 남긴다. 같은 활성 버전을 다시 활성화하면 204다. 기존 분석·진행 중 분석은 접수 시 버전을 유지하고 과거 리포트를 재채점하지 않는다.
- `PUT /admin/rubric`은 `{items:[{key,label,guide}],expectedVersion}`를 받는다. 네 항목 key를 정확히 한 번씩 포함하며 기존 버전을 덮어쓰지 않고 새 rubricVersion을 생성한다. 204 응답에 새 버전을 ETag로 제공한다. GET은 `{data:{rubricVersion,items}}`와 같은 ETag를 반환한다. expectedVersion 불일치는 409 VERSION_MISMATCH다. 기존 배정은 기존 기준을 유지한다. 새 기준에 호환 보정이 준비되기 전에는 신규 분석에 적용하지 않는다. 모델 배포/루브릭 서비스 적용의 운영 절차는 확인 필요다.
- `GET /admin/validation?version=`은 보정 version string을 받는다. v0/v1은 원본의 예시일 뿐 고정 enum이 아니다. 생략은 현재 서비스 모델/루브릭의 활성 보정 버전이다. 활성 버전이 없으면 `409 VERSION_UNAVAILABLE`. 응답에 `modelVersion,rubricVersion,calibrationVersion,sampleCount`를 추가한다. disagreements도 같은 선택 version을 받으며 `minGap`은 0~100 number, 기본 15다.
- evaluatedVideos/evaluators/basedOnCount는 integer다. meanAbsGapBefore/After, byItem.before/after, scatter.expert/ai, agreement.meanAbsGap는 number이며 표본 없음은 통계 null·scatter []다. 원본 대시보드의 실제 집계 분모·기간·재시도 포함 여부는 8-2에서 확정한다. asOf 생략은 집계 시간대의 오늘이며 그 시간대는 확인 필요다. admin users의 status는 ACTIVE/SUSPENDED, joinedAt/lastActiveAt은 시각이며 활동 이력 없을 때 lastActiveAt만 null이다.
- retry 응답은 `{data:{analysisId,attempt,status:"QUEUED"}}`와 Location을 반환한다. invitations는 `201 {data:{invitationId,status:"PENDING"}}`; 배정 count는 양수이며 적격 영상 부족 시 `409 INSUFFICIENT_ELIGIBLE_VIDEOS`로 전체 취소한다. reevaluate는 기존 평가를 삭제하지 않고 새 배정을 생성한다. 대상 적격성/재평가자 선정 규칙은 확인 필요다. role/status PATCH의 요청·응답은 원본대로 유지한다.
- 모든 관리자 변경은 actorId/action/targetId/requestId/before/after/at을 감사 기록한다. 자격·동의 미확인 영상 배정과 본인의 역할 변경·정지는 거부한다. 감사 로그에 토큰·원본 영상·음성을 넣지 않는다.

```json
{
  "data": {
    "jobId": "caljob_example",
    "status": "SUCCEEDED",
    "progressPercent": 100,
    "version": "cal-example",
    "modelVersion": "model-example",
    "rubricVersion": "rubric-example",
    "evaluationCount": 24,
    "createdAt": "2026-11-02T02:00:00Z",
    "updatedAt": "2026-11-02T02:01:00Z",
    "error": null
  }
}
```
evaluationCount=24는 예시이며 최소 표본 수를 뜻하지 않는다. 보정 작업 조회는 기존 관리자 검증 화면의 진행 표시를 완성하기 위한 기술 API다.

## 8. 화면별 호출 매핑 및 확인 필요한 가정

### 8-1. 화면별 호출 매핑

| 화면 (주소) | 역할 | 호출하는 API |
| --- | --- | --- |
| 로그인 / 회원가입 | 공개 | `POST /auth/login`, `POST /auth/signup` |
| 내 발표 프로젝트 (`/me`) | USER | `GET /projects`, `PATCH\|DELETE /projects/{id}` |
| 이력 · 추이 (`/me/history`) | USER | `GET /projects`, `GET /projects/{id}/history` |
| 발표 일정 (`/me/calendar`) | USER | `GET /me/calendar` |
| 계정 설정 (`/me/account`) | USER | `GET\|PATCH\|DELETE /me` |
| 새 연습 (`/new`) | USER | `GET /projects`, `POST /projects` |
| 영상 올리기 (`/upload`) | USER | `POST /projects/{id}/uploads`, `…/complete` |
| 라이브 연습 (`/live`) | USER | `POST /projects/{id}/live-sessions`, WebSocket, chunks, pause\|resume\|restart\|finish |
| 저장하지 않고 마쳐어요 (`/discarded`) | USER | `POST …/discard`, `POST …/undo-discard`, `DELETE /live-sessions/{id}` |
| 분석 중 (`/analysis`) | USER | `GET /analyses/{id}`, SSE, `POST …/notify` |
| 분석 리포트 (`/report/{p}/{n}`) | USER | `GET …/report`, `…/compare`, `…/video`, `…/qa` |
| 평가자 홈 · 영상 평가 (`/expert/home`, `/expert`) | EXPERT | `GET /expert/overview`, `…/assignments`, `POST …/evaluation` |
| 관리자 대시보드 (`/admin`) | ADMIN | `GET /admin/dashboard`, `GET /admin/analyses` |
| AI 점수 검증 (`/admin/validation`) | ADMIN | `GET /admin/validation`, `…/disagreements`, `…/calibrations` |
| 전문가 평가 관리 (`/admin/experts`) | ADMIN | `GET /admin/experts`, `POST …/invitations`, `…/assignments`, `…/rubric` |
| 사용자 관리 (`/admin/users`) | ADMIN | `GET /admin/users`, `PATCH …/role`, `PATCH …/status` |

### 8-2. 확인 필요: 정책 결정 등록부

아래 값은 원본에서 확정되지 않았거나 구현에 필요한 추가 합의 사항이다. 예시 값을 운영 기본값으로 승격하지 않는다. 해당 정책이 정해지지 않은 기능은 검증된 설정 없이 운영 활성화하지 않는다. 기능 범위 확정과 운영 값 확정을 구분한다.

| ID | 확인 필요 사항 | 원본 근거 / 필요한 결정 | 관련 절 |
| --- | --- | --- | --- |
| P01 | FR 매핑·실시간 범위 | 요구사항서 미제공. FR-05와 속도/음량/시선 범위 대조, 군말·전달력 추가 여부 | 5 |
| P02 | 영상 보관·되살리기 | 원본 화면은 원본 영상 30일·discard 30초. 실제 기간 확정 아님. 기산점·정확한 만료 시각·기한 경계·삭제 SLA 승인 필요 | 3,4 |
| P03 | 전문가 활용 동의 | 대상 영상 범위·별도 동의 문구/버전·철회 효과·미성년자 처리·평가자 접근 기간·얼굴/음성 비식별 처리 | 2,6,7 |
| P04 | 보관 대상별 기간 | 원본/조각/음성/전사문/특징량/리포트/QA/recap/동의/감사/백업 각각의 기간과 삭제 완료 기준 | 2~7 |
| P05 | 삭제·철회 후 처리 | 진행 분석/보정 중단, 이미 학습·보정에 사용된 데이터의 추적/제외·재계산, 법정 보존 예외·삭제 접수 채널 | 2,7 |
| P06 | 평가 수정·skip | 최종 평가 수정 허용, 새 리비전 관리, 보정에 사용한 평가 변경 영향, skip 재노출·재배정 | 6 |
| P07 | 엔진·품질 기준 | STT/시선/제스처 모델 구성과 버전 식별, 필수 점수 산출 실패 조건·결손 허용 범위 | 4,5 |
| P08 | 점수·보정 기준 | total 산식/가중치, 회귀·클리핑·반올림, 최소 표본, 전문가 합의도, 평가 집합/검증 집합 분리, 비교 동등성 | 4,7 |
| P09 | 서비스 집계 | KPI 분모·기간·성공률/재시도/삭제 포함 기준, 일정 날짜 경계·집계 시간대·동점 시 최약/최대 개선 항목 선택 | 4,7 |
| P10 | 업로드 제한 | MIME/코덱·최대 크기/길이, 서명 TTL, 임시 업로드 정리 기한, chunk 한도/주기 | 3 |
| P11 | 인증·전송 제한 | 토큰/티켓 TTL, refresh 유실 복구·저장 방식, Origin 목록, WS 동시 연결·메시지 한도, 재연결 상한, SSE heartbeat/보존 시간 | 1,2,5 |
| P12 | 멱등성·동시성 운영 | 키 보관 기간, 외부 큐 중복 처리 보존 기간, 요청 제한·timeout | 1 |
| P13 | 입력 정책 | 문자열 길이·비밀번호·이메일 정규화, 목표 연습 시간/업로드 크기/QA count/배정 count의 최대값 | 1~7 |
| P14 | 알림·QA | 완료 알림 채널/동의/전달 실패 기준, QA 기본 개수·생성 timeout | 4 |
| P15 | 약관 필수성·운영 적용 | 가입 단계의 영상 동의 선택 여부, 이용약관/개인정보 문서 버전, 역할 변경 시 기존 프로젝트 접근, 모델·루브릭 배포 승인 절차 | 2,7 |

### 8-3. 동의·보관 공통 실행 규칙

정해진 보관 기간 값과 무관하게 다음 기술 규칙을 적용한다.

1. 서버는 동의 문서의 유효 버전과 목적을 검증하며 클라이언트의 true만 신뢰하지 않는다. 영상 분석 동의는 전문가 열람·평가 활용 동의를 대체하지 않는다. 전문가 활용 동의가 확인되지 않으면 배정에서 제외한다.
2. 저장된 영상에는 `retentionExpiresAt`, discard에는 `undoUntil`을 서버가 계산한다. 운영 기간 미승인 상태에서는 날짜를 임의 생성하여 상용 기능을 열지 않는다. 승인된 설정으로만 서버 시각 기준 기한을 계산한다.
3. 삭제는 접근 차단→작업 취소/결과 공개 차단→원본·조각·파생 데이터 정리→완료 기록 순으로 추적한다. 비동기 작업은 삭제 표식을 확인하여 결과를 다시 생성하지 않는다. 외부 저장소 물리 삭제는 재시도 가능한 작업으로 관리한다.
4. 서명 URL TTL은 데이터 접근 허용 기한을 넘지 않도록 제한한다. 즉시 삭제 시 이미 발급한 URL을 무효화할 수 있는 객체 삭제/접근 차단 수단을 적용한다. 그 수단과 지연 한도는 운영 검증이 필요하다.
5. 전문가 키의 비식별성과 실제 영상의 식별 가능성을 구분한다. 관리자 통계·감사에 원본 영상을 노출하지 않는다. 새로운 데이터 관리 화면/삭제 대기열 관리 API는 이 v2에 추가하지 않는다.

### 8-4. 화면 매핑 보완 및 중복 제거 목록

8-1의 모든 화면·주소·역할을 유지하며 아래 호출을 보완한다.

| 기존 화면 | 보완 호출 / 정본 |
| --- | --- |
| 영상 올리기 | prepare → 스토리지 PUT → complete. 앱 서버에 파일 바이너리 중복 전송하지 않음 |
| 라이브 연습 | 기존 호출 + GET /live-sessions/{sessionId}, POST …/feedback-ticket, finish manifest, POST …/save |
| 저장하지 않고 마쳐어요 | discard 응답 recap과 undoUntil 사용, undo/discard/delete 경합은 서버 상태 기준 |
| 분석 중 | 폴링 또는 인증 fetch-SSE 중 하나만 주 경로로 사용 |
| 분석 리포트 | report가 QA 정본, qa GET은 호환 조회, regenerate 후 동일 스냅샷. 영상 URL은 video GET에서만 발급 |
| 평가자 홈·영상 평가 | next, draft PUT, skip POST도 원본 기능대로 연결 |
| AI 점수 검증 | calibration POST 후 GET /admin/calibration-jobs/{jobId} 폴링, 성공한 version만 activate |
| 전문가 평가 관리 | rubric 조회는 GET, 수정은 PUT. 원본 화면 표의 포괄 POST 표기를 정정 |

변경되는 필드/요청은 프론트·백엔드 동시 반영이 필요하다. URL namespace를 v2로 바꾸지 않으므로 기존 클라이언트에 자동 하위 호환을 보장하지 않는다. 특히 ws token query, chunkUploadUrl, report.videoPlayUrl, calibration 접수 응답 version의 즉시 사용을 교체해야 한다.

### 8-5. 검토 시 수용 기준

- 같은 complete/save/undo·최종 평가·관리자 retry를 동시에 재전송해도 업무 결과가 하나다.
- chunk 유실·해시 충돌·과거 generation·manifest 변경이 4xx로 구분되고, 미완료 영상으로 분석을 시작하지 않는다.
- 폐기 기한 경계의 undo와 삭제가 동시에 성공하지 않고 restart 전 프레임/조각이 섞이지 않는다.
- 만료/재사용 WS 티켓·잘못된 Origin·타인 ID·정지 계정을 거부한다. 인증 정보를 URL/로그에 노출하지 않는다.
- 분석 FAILED와 보정 FAILED가 화면에서 조회 가능하며, 완료 전 리포트·보정 버전을 제공하지 않는다.
- 보정 활성화/루브릭 변경 후에도 기존 분석·배정의 버전이 바뀌지 않는다. 버전이 다른 점수의 차이를 같은 기준의 개선으로 표시하지 않는다.
- 영상 삭제·동의 범위·평가자 AI 점수 비노출 규칙을 목록/리포트/서명 URL/비동기 작업 전체에서 동일하게 적용한다.
- 8-2 정책 결정이 운영 설정·약관·화면 문구에 반영되기 전에는 미확정 값을 확정 문구로 배포하지 않는다.
