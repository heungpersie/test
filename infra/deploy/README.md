# EC2·Docker Compose 배포 기본 설정

2026-11-04 · ECS 대안을 종료하고 EC2에 Docker Compose로 배포하는 초안으로 교체했다. AWS 리소스 생성·SSH 접속·실배포는 수행하지 않았다. 1주차는 설정 준비, 실제 AWS 실행은 예산 확인 후 3주차 예정이다.

[환경 분리 기준·완료 범위](ENVIRONMENTS.md)를 먼저 확인한다. [비용·실행 일정·정리 계획](../aws/COST_OPERATIONS.md)도 함께 확인한다.

## 파일과 흐름

| 파일 | 역할 |
|---|---|
| .github/workflows/ci.yml | PR 코드·타입·테스트·빌드. 유지 |
| .github/workflows/publish-api.yml | develop 병합 후 CI·ECR 게시. 기본 비활성 |
| .github/workflows/deploy-compose.yml | 수동 입력·SSH 인증·파일 전달·서버 배포. 기본 비활성 |
| infra/deploy/compose.yaml | 서버에서 게시된 BE 이미지를 실행. RDS·AI·S3 생성 없음 |
| infra/deploy/deploy.sh | digest pull·교체·상태 검사·이전 이미지와 Compose 복귀 |
| infra/deploy/.env.example | 공통 예시. 실제 작성은 environments/dev·demo/.env.example 사용 |
| infra/deploy/validate_environment.py | 해석된 Compose의 대상 환경·DB·포트 혼선 검사 |

전체 흐름: PR CI → develop 병합·이미지 게시 → 검증한 digest 선택 → EC2 pull → Compose 교체 → /healthz·/readyz 확인. develop push의 ECR 게시 성공 후 개발 자동 배포를 호출하도록 연결했다. 수동 실행도 지원하며 발표는 main에서 수동·승인 방식이다. 두 활성화 스위치는 기본 비활성이고 실제 배포는 미검증이다.

## 실행 전 준비 — 지금 생성하지 않음

- AWS EC2 Linux x86_64 서버, Docker Engine·Compose v2(--wait 지원)·Python 3·AWS CLI v2·Bash·flock 설치. ARM 서버는 이미지 플랫폼과 에뮬레이션/별도 빌드를 검토한다.
- SSH 접속 계정은 Docker 실행과 배포 디렉터리 쓰기가 가능해야 한다. Docker 접근은 서버의 높은 권한에 해당하므로 전용 배포 키·계정으로 관리한다. 비밀번호·sudo 대화형 입력은 사용하지 않는다.
- SSH 22번 접근 경로를 마련한다. GitHub-hosted runner의 IP는 고정이 아니므로 사설 서버에는 네트워크가 연결된 self-hosted runner 등 별도 설계가 필요하다. 편의를 위해 인터넷 전체에 SSH를 열지 않는다.
- 서버에 /opt/presentation/dev/shared/api.env 또는 /opt/presentation/demo/shared/api.env 작성. 소유자를 배포 계정으로 지정하고 파일 권한 600. 파일은 Git·이미지·Actions artifact에 넣지 않는다.
- RDS PostgreSQL은 사전 준비하고 접근 주소·계정·DB를 환경별로 분리한다. 배포 Compose는 DB를 만들거나 로컬 coach 볼륨을 사용하지 않는다. migration은 별도 승인된 절차로 수행한다.
- API는 127.0.0.1의 18000(dev)·18001(demo) 등에만 바인딩한다. 외부 접속용 HTTPS reverse proxy·도메인·방화벽은 별도 설정한다.
- 이미지 저장소는 ECR이다. 서버는 읽기 전용 EC2 인스턴스 역할로 배포 때마다 ECR 로그인하며 임시 Docker 인증 파일은 종료 시 삭제한다. [AWS 역할·연결 준비](../aws/README.md)를 따른다.

## GitHub 변수·Secret

Repository Variable COMPOSE_DEPLOY_ENABLED를 true로 설정하기 전에는 배포가 실행되지 않는다. 기존 ECS_DEPLOY_ENABLED는 더 이상 사용하지 않으므로 등록돼 있다면 제거한다.

GitHub Environments aws-dev / aws-demo:

| 종류 | 이름 | 내용 |
|---|---|---|
| Variable | IMAGE_REPOSITORY | 허용할 경로. <ACCOUNT_ID>.dkr.ecr.<REGION>.amazonaws.com/<REPOSITORY> |
| Secret | EC2_SSH_HOST | 서버 DNS 또는 IPv4. IPv6는 현재 검증식에서 미지원 |
| Secret | EC2_SSH_USER | SSH 접속 계정 |
| Secret | EC2_SSH_PRIVATE_KEY | 전용 SSH 개인키. 원문을 문서·채팅에 붙이지 않음 |
| Secret | EC2_SSH_KNOWN_HOSTS | 독립적으로 확인한 서버 host key의 known_hosts 행 |

aws-dev는 develop, aws-demo는 main으로 Environment 허용 브랜치를 제한하고 발표 환경에는 승인자를 설정한다. 워크플로 자체에도 동일한 제한이 있다. 신규 워크플로는 기본 브랜치에 반영되어야 Actions 수동 실행 화면에서 이용할 수 있다. 서버 키를 확인 없이 ssh-keyscan 결과만 신뢰하지 않는다.

실제 앱 변수는 GitHub가 아니라 서버 api.env에 둔다: APP_ENV, API_HOST_PORT, DB_HOST(RDS endpoint), DB_PORT, DB_NAME, DB_USER, DB_PASSWORD, RDS_CA_BUNDLE_HOST_PATH. S3 변수는 SDK 연동 전 예약값이다. RDS 공개 CA bundle은 서버에 사전 준비한다. api.env는 Docker 환경변수로 전달되므로 Docker 관리자에게는 조회될 수 있다. AWS Secrets Manager 직접 주입은 이번 SSH 초안에 포함하지 않는다.

## 서버 배포 디렉터리

```text
/opt/presentation/dev/             # demo는 별도 디렉터리·Compose 프로젝트·포트
  shared/api.env                  # 비밀정보, Git 제외
  releases/<run-id>-<attempt>/
    compose.yaml                  # 해당 배포의 실행 설정
    deploy.sh                     # 해당 배포 실행 스크립트
    image.txt                     # digest, 비밀정보 아님
  current -> releases/성공한버전   # 성공한 뒤에만 포인터 변경
  deploy.lock                     # 같은 서버의 배포 중복 실행 차단
```

1. 활성화 이후 Actions에서 환경·허용 브랜치·검증한 이미지 digest 선택.
2. 기존 CI 재실행. 입력 digest가 검증된 게시 이미지인지 릴리스 리뷰로 대조.
3. runner에서 입력 검증·known_hosts 고정, 공개 설정 파일만 업로드.
4. 서버에서 잠금 획득, Compose 환경 분리 검증·pull. 이 단계 실패 시 기존 API를 변경하지 않음.
5. Compose up --wait와 컨테이너 내부 /healthz·/readyz HTTP 검사.
6. 성공하면 current 갱신. 실패하면 이전 릴리스의 Compose·digest로 복귀하고 상태 확인, 워크플로는 실패 유지.

첫 배포에는 이전 버전이 없으므로 실패한 API만 중지·제거한다. DB·볼륨은 삭제하지 않는다. 배포는 중단 시간이 발생할 수 있으며 무중단을 보장하지 않는다. SSH 단절·취소·timeout 시 복귀 완료는 보장하지 않으므로 서버 상태를 확인하고 이전 릴리스로 재실행한다. 공유 api.env·DB 데이터·migration·외부 저장소 설정은 복귀하지 않는다. 변경 전 별도 보존·호환성 검토가 필요하다.

## 로그·비용·검증 범위

Docker json-file 로그는 파일당 10 MB·최대 3개로 회전한다. CloudWatch 수집은 포함하지 않는다. 앱은 비밀번호·토큰·영상/전사 원문을 로그에 출력하지 않아야 한다. 로그 확인은 서버에서 동일 프로젝트·환경 파일·digest로 docker compose logs를 사용한다. compose config의 전체 출력은 비밀번호를 포함할 수 있으므로 검사에는 config --quiet를 사용한다.

EC2 중지 후에도 EBS·스냅샷·기타 AWS 자원 비용이 남을 수 있다. 예산·사용 시간·보존 데이터·삭제 대상을 먼저 정한다. docker compose down -v나 기존 개발 볼륨 삭제를 배포 절차에 넣지 않는다.

완료: 파일 작성·로컬 구문/설정 검증. 대기: EC2 접속·실배포·복귀·외부 HTTPS·업무 E2E. FE·AI 워커는 별도다.

## ECS 파일 변경 이력

deploy-ecs.yml·Task Definition·OIDC/배포 IAM 예시·render_ecs_task.py는 제거했다. 현재 경로는 Compose/SSH 기준이며 과거 초안은 Git 이력에서 확인한다. 기존 GitHub AWS Environment 변수는 새 변수·Secret 표로 교체하며, 실제 AWS IAM 리소스는 이번 작업으로 생성·삭제하지 않았다.

[Docker Compose 운영 가이드](https://docs.docker.com/compose/how-tos/production/) · [GitHub 배포 환경](https://docs.github.com/en/actions/concepts/workflows-and-actions/deployment-environments)

[자동 개발 배포·발표 승인 정책](../aws/PIPELINE_STATUS.md)

[네트워크·보안 설계](../aws/NETWORK_SECURITY.md): 사설 앱 배치에서는 현재 GitHub-hosted SSH 경로를 그대로 사용할 수 없으므로 관리망/runner 또는 SSM 방식 확정이 필요하다. 서버 생성 전 확인한다.
