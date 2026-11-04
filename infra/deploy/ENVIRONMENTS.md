# 개발·배포 환경 분리 설정

2026-11-04 · BE 기준 설정 작성·로컬 검증. AWS 서버·RDS·S3·ECR·권한·팀 저장소 실제 적용은 아직 수행하지 않았다. FE·AI·영상 저장소는 연결 계약과 제품 선정 후 확장한다.

## 환경별 기준

| 항목 | 로컬 개인 개발 | AWS 개발·통합 | AWS 발표 |
|---|---|---|---|
| 목적 | 각자 코드 개발 | 팀 기능 연결·검증 | 승인한 버전 시연 |
| GitHub Environment | 없음 | aws-dev | aws-demo |
| 코드 기준 | 작업 브랜치 | develop | main |
| 실행 파일 | infra/compose.yaml | infra/deploy/compose.yaml | 동일 배포 파일 |
| Compose 프로젝트 | infra-db-demo (기존 유지) | presentation-dev | presentation-demo |
| API 공개 포트 | 127.0.0.1:8000 | 127.0.0.1:18000 | 127.0.0.1:18001 |
| APP_ENV | local | dev | demo |
| DB_NAME | coach | coach_dev | coach_demo |
| DB_USER | coach_app | coach_dev_app | coach_demo_app |
| DB 위치 | 로컬 postgres 서비스 | RDS PostgreSQL endpoint, 값 미정 | RDS PostgreSQL endpoint, 값 미정 |
| 환경 파일 | infra/.env / api/.env | /opt/presentation/dev/shared/api.env | /opt/presentation/demo/shared/api.env |
| 릴리스 경로 | 없음 | /opt/presentation/dev/releases/ | /opt/presentation/demo/releases/ |
| 설정 예시 | 기존 .env.example | environments/dev/.env.example | environments/demo/.env.example |
| 로그 | 로컬 Docker 로그 | dev Compose 프로젝트 로그 | demo Compose 프로젝트 로그 |
| 이미지 | 소스에서 빌드 | ECR의 검증한 digest | ECR의 승인 릴리스 digest |

두 AWS 환경을 동시에 켜거나 서버를 두 대 만들 필요는 없다. 같은 EC2라면 Docker 프로젝트·네트워크·포트·환경파일·DB 사용자와 데이터를 구분한다. CPU·디스크·호스트 장애는 공유하므로 물리 격리가 아니다. DB는 같은 PostgreSQL 인스턴스에 둘 수 있으나 이름만 달리한다고 권한이 분리되지는 않는다. 다른 DB 접속·조회·변경을 제한하는 실제 권한 설정과 음성 검증은 DB 생성 시 수행한다.

## 지금 적용된 차단 설정

- CD의 develop→aws-dev, main→aws-demo 조건과 명시적 target 검사.
- 서버 경로에서 dev/demo를 정해 Compose 프로젝트명을 강제. 저장소의 환경 파일 값으로 프로젝트를 바꾸지 않는다.
- Compose가 해석한 실제 설정을 validate_environment.py가 검사한다. APP_ENV·DB_NAME·DB_USER·프로젝트·고정 포트가 다르면 pull·서비스 교체 전에 실패한다.
- DB_HOST가 비어 있거나 localhost/로컬 Compose 서비스 주소이면 배포를 거부한다.
- 실제 DB_PASSWORD는 서버 파일에 두고, config JSON은 파이프로 검사기에만 전달한다. 원문·비밀번호는 로그에 출력하지 않는다.
- 로컬 Compose 프로젝트 이름·DB 볼륨·실제 .env는 수정하지 않았다.

실제 DB 호스트의 소유 환경, DB 권한, 데이터 내용·비밀번호의 환경별 유일성은 문자열 검사로 보장하지 못한다. dev와 demo의 비밀번호를 다르게 발급하고 교차 접근 불가를 AWS 적용 시 확인한다.

## 준비와 실제 적용 순서

1. 해당 환경 예시 파일을 보고 서버 shared/api.env를 새로 작성한다. 로컬 .env를 복사하지 않는다. 값의 따옴표·$ 등 특수문자는 Compose dotenv 문법에 맞게 저장하고 필요하면 리터럴 single quote를 사용한다.
2. 각 DB·앱 계정과 접근 제어를 별도 준비하고 실제 접속 값을 넣는다. DB_HOST·비밀번호가 비어 있는 예시는 실행 가능한 실제 설정이 아니다. RDS CA bundle을 준비하고 verify-full TLS 설정을 유지한다.
3. 환경별 SSH Secret·허용 이미지 경로·허용 브랜치·발표 승인자를 GitHub Environment에 설정한다. 프로젝트/환경 이름만으로 GitHub 권한 정책이 자동 생성되지 않는다.
4. API_HOST_PORT는 dev=18000, demo=18001로 고정한다. 배포 서버 쉘에 남은 APP_ENV·DB_*·포트 변수는 제거하고 전용 배포 계정을 사용한다. 셸 변수는 dotenv보다 우선하지만 검사에서 환경·DB·포트 혼용을 차단한다.
5. 3주차 첫 배포에서 데이터 쓰기·삭제·권한·로그·외부 URL이 서로 격리되는지 검증한다. 발표 버전 태스크 교체만으로 개발 데이터가 발표 환경으로 복사되지는 않는다.

## 아직 미확정인 자원

DB는 RDS PostgreSQL, 영상은 S3, 이미지는 ECR로 선정했다. 계정별 endpoint·버킷·저장소·영상 보관 정책은 별도 항목이다. S3에 dev/demo 별도 버킷 또는 prefix와 그 범위에 제한된 권한을 설정한다. 현재 존재하지 않는 버킷·IAM을 설정 완료로 표시하지 않는다. 로그는 Docker json-file 회전 기본 설정이며 구조화 로그·추적 ID·장기 수집 정책은 후속 작업이다.

## 완료 판정

- 완료: 환경 구분표·dev/demo 설정 예시·배포 전 차단 검사·CI 테스트·로컬 Compose 설정 해석 검증.
- 대기: AWS 계정별 실제 값 주입, DB·Secret·GitHub Environment 적용, AWS 데이터/권한 격리·배포·복귀 실검증.
- 환경 분리는 BE 범위다. AI 실행 환경·FE 주소·CORS 등은 담당자 정보가 준비되면 추가한다.
