# ECS CD 기본 설정 초안

2026-11-04 · BE 전용 Fargate 제안. AWS 리소스 생성·권한 적용·배포를 수행하지 않았다. 첫 실환경 검증은 3주차 예정이며 예산·권한 확인 후 진행한다. AI GPU·FE 배포 설정은 별도다.

## 준비한 파일

- ../../.github/workflows/deploy-ecs.yml: 수동 배포, CI 재검증, OIDC 인증, 기존 ECS Service 교체, 검증·실패 복귀.
- task-definition.template.json: BE Fargate Task Definition, 내부 8000 포트, DB Secret 참조, CloudWatch 로그, /readyz 검사.
- ../../tools/render_ecs_task.py: 환경변수를 안전하게 JSON 값에 넣는 렌더러. AWS API 호출 없음.
- github-oidc-trust.template.json: GitHub Environment에 제한된 역할 신뢰 정책 예시.
- github-deploy-policy.template.json: 지정 ECS Service 갱신·Task Definition 등록·지정 역할 PassRole 예시.

CPU 256·메모리 512 MiB는 BE 초기 검토값이며 측정 후 조정한다. 현재 이미지와 동일한 X86_64로 지정했다. Fargate 선택은 BE 초안에 한하며 전체 ECS 실행 방식이나 GPU 선택을 확정하지 않는다.

## 지금 실행되지 않는 이유

워크플로는 push·PR에서 배포하지 않고 workflow_dispatch만 제공한다. Repository Variable ECS_DEPLOY_ENABLED가 문자열 true일 때만 실행된다. 기본값은 미설정이므로 비활성이다. aws-dev는 develop에서, aws-demo는 main에서만 실행된다. 현재 AWS 계정·클러스터·서비스를 생성하거나 기존 GHCR 게시 동작을 바꾸지 않는다.

## 3주차 전에 설정할 GitHub 값

Repository Variable:

| 이름 | 값 |
|---|---|
| ECS_DEPLOY_ENABLED | 준비 완료 후에만 true |

GitHub Environments aws-dev / aws-demo를 각각 만들고 아래 Environment Variables를 등록한다. Environment에서 허용 브랜치를 각각 develop / main으로 제한한다. aws-demo에는 승인자를 설정한다. 보호 기능의 제공 범위는 저장소·플랜에서 확인한다. OIDC 신뢰 정책은 브랜치 sub가 아니라 해당 Environment sub와 일치시킨다.

| 변수 | 내용 |
|---|---|
| AWS_REGION | 사용할 AWS 리전 |
| AWS_ACCOUNT_ID | 12자리 AWS 계정 ID |
| AWS_DEPLOY_ROLE_ARN | GitHub OIDC가 사용할 배포 역할 |
| ECS_CLUSTER / ECS_SERVICE | 미리 만든 기존 클러스터·서비스 |
| ECS_TASK_FAMILY | 해당 환경의 BE Task Definition family |
| ECS_EXECUTION_ROLE_ARN | 이미지 pull·로그·Secret 주입용 역할 |
| ECS_TASK_ROLE_ARN | 앱에서 사용하는 AWS API 권한용 역할. 필요 없으면 권한 없는 ECS task 역할 |
| ECS_LOG_GROUP | 미리 만든 CloudWatch Log Group |
| ECS_IMAGE_REPOSITORY | 허용할 이미지 저장소 전체 경로. ghcr.io/heungpersie/test-api 등 |
| APP_ENV | dev 또는 demo 등 해당 환경명 |
| DB_HOST / DB_NAME / DB_USER | 해당 환경의 DB 연결 정보. 컨테이너 localhost·개발 PC 주소 사용 금지 |
| DB_PASSWORD_SECRET_ARN | DB 비밀번호 문자열을 보관한 Secrets Manager Secret ARN |
| API_BASE_URL | GitHub runner에서 접근 가능한 해당 서비스 HTTPS URL |

워크플로 입력 image는 검증된 repository@sha256:<64자리> 형식이다. 태그나 임의 저장소 이미지는 거부한다. GHCR 유지가 기본이며 ECR로 변경하면 먼저 이미지 게시/이전·검증을 하고 허용 저장소 값을 바꾼다. 이번 워크플로는 ECR 이미지를 생성하지 않는다. 입력 digest와 테스트 결과의 대응은 릴리스 리뷰에서 확인하며 자동 출처 증명 검증은 아직 없다.

## 미리 필요한 AWS 리소스 — 지금 생성하지 않음

- OIDC Provider와 배포 역할: 신뢰 정책의 계정·저장소·Environment 자리표시자를 실제 값으로 교체. 제시한 정책은 리소스 생성 권한을 주지 않는다.
- ECS execution role·task role의 신뢰 주체는 ecs-tasks.amazonaws.com. execution role에는 이미지 취득·로그·지정 Secret 읽기 권한, 필요 시 지정 KMS 키 복호화 권한을 부여한다. task role에는 앱에 필요한 권한만 부여한다. 배포 역할에는 DB 비밀번호 읽기 권한이 필요 없다.
- VPC·서브넷·보안 그룹·로드밸런서·대상 그룹·TLS·DB·Secret·Log Group 준비. Service는 ECS rolling deployment controller와 Fargate 용량을 사용하며 desiredCount 1 이상, api:8000 대상 그룹과 /readyz 상태 검사를 구성한다. 배포 circuit breaker·rollback도 활성화 권장.
- 네트워크는 이미지·로그·Secret 접근 경로와 DB 접근 경로를 제공해야 한다. GHCR pull은 인터넷 접근이 필요하며 사설 서브넷이면 NAT 등 비용을 포함한다. ECR 선택 시 필요한 네트워크 경로를 별도 검토한다.
- 비공개 GHCR은 repositoryCredentials와 Secrets Manager 자격정보, execution role 읽기 권한이 추가로 필요하다. 현재 Task Definition에는 포함하지 않았다. ECR이면 execution role에 해당 ECR pull 권한이 필요하다.
- HTTPS URL은 해당 환경의 ECS Service로 연결되어야 한다. 내부 전용 URL이면 GitHub-hosted runner가 접근하지 못하므로 runner·검증 위치 설계를 변경해야 한다.
- 신규 Service 최초 생성과 DB schema migration은 이번 CD에 포함되지 않는다. 앱이 요구하는 schema를 별도 승인된 절차로 준비하고, 최초 배포도 사전 bootstrap으로 수행한다. 이 CD는 기존 서비스 버전 교체를 담당한다.

## 실제 실행 순서

1. 예산·리전·네트워크 비용·지원 GPU 범위를 확인하고 AWS 자원 생성 계획 승인.
2. 환경별 기반 자원·역할·Secret·기존 ECS Service 준비. Secret의 값은 GitHub·채팅·코드에 넣지 않는다.
3. GitHub Environment Variables와 브랜치·승인 제한 구성. ECS_DEPLOY_ENABLED=true로 활성화.
4. Actions → Deploy API to ECS (manual) → 허용 브랜치·환경·검증한 이미지 digest 선택.
5. CI 통과 후 Task Definition 렌더링·OIDC 인증·이전 버전 기록·새 revision 등록·Service 업데이트.
6. ECS 안정화 및 실제 새 revision 적용을 확인하고 /healthz·/readyz HTTP 성공 확인. circuit breaker가 이전 버전으로 되돌린 경우 새 revision 검증에 실패하므로 성공으로 오인하지 않는다.
7. 업데이트/검증 실패 시 이전 revision으로 복귀 요청·안정화 대기. 원래 배포는 실패 상태로 유지한다. 타임아웃·취소·runner 중단은 복귀 단계 실행을 보장하지 않으므로 ECS circuit breaker와 수동 복구 절차도 확인한다.

복귀는 이미지·Task Definition 수준이다. DB 데이터·migration은 되돌리지 않는다. 파괴적 schema 변경은 별도 계획이 필요하다. 안정화 waiter는 제한 시간이 있으며 장시간 배포는 실패할 수 있다. 복귀 후 API·DB 점검과 로그 확인은 운영자가 수행한다. 진행 중 AI 작업은 이번 BE CD 범위가 아니다.

## 비용 관리

1주차는 파일 작성·로컬 검증만 수행한다. 3주차 최초 배포 전 실행 시간·종료 방법·남는 자원 비용을 정한다. 태스크 중지나 desiredCount=0만으로 ALB·DB·NAT·로그·저장소 비용이 모두 사라지지 않는다. 데이터 보존·복구 기준을 정한 뒤 리소스별 정리 계획을 따른다.

## 공식 참고

- [GitHub OIDC / AWS](https://docs.github.com/en/actions/how-tos/secure-your-work/security-harden-deployments/oidc-in-aws)
- [GitHub ECS 배포](https://docs.github.com/en/actions/how-tos/deploy/deploy-to-third-party-platforms/amazon-elastic-container-service)

현재 완료: CD 초안 파일 작성·로컬 구문/렌더링 검증. 미완료: GitHub 실제 실행, AWS 인증·배포·롤백 실환경 검증.
