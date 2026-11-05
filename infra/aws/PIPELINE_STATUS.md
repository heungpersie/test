# ECR 게시·개발 자동 배포 기본 설정

2026-11-05 · AWS 리소스 생성·인증·게시·배포는 수행하지 않았다.

## 실행 조건

| 경로 | 동작 | 활성화 조건 |
|---|---|---|
| PR | API·Docker·환경 설정 검사 | 기존 PR CI |
| develop push | CI → ECR 게시·태그 digest 검증 | ECR_PUBLISH_ENABLED=true |
| 같은 게시 실행의 성공 이후 | 검증한 digest → aws-dev Compose CD | COMPOSE_DEPLOY_ENABLED=true도 필요 |
| 수동 ECR 게시 | CI·게시만 실행 | 자동 개발 배포를 호출하지 않음 |
| 수동 배포 aws-dev | develop에서만 실행 | COMPOSE_DEPLOY_ENABLED=true |
| 수동 배포 aws-demo | main에서 실행·Environment 승인 후 배포 | COMPOSE_DEPLOY_ENABLED=true 및 승인 |

publish-api.yml의 deploy-dev job이 같은 실행의 publish outputs(image·digest)를 직접 전달한다. 새 이미지를 추측해서 latest로 배포하지 않는다. ECR의 describe-images 결과가 게시 digest와 일치해야 게시 job이 성공한다. 배포용 reusable workflow는 workflow_call과 workflow_dispatch를 함께 지원한다. 기존 배포 단계의 코드 CI 재검사는 유지하며, 이는 입력 이미지 자체의 출처 증명은 아니다.

## 개인 GitHub 저장소 적용

- aws-dev: develop 브랜치만 허용, 별도 승인 없이 개발 배포 가능.
- aws-demo: main 브랜치만 허용, heungpersie의 승인이 있어야 배포 job 실행.
- 개인 테스트 저장소의 단일 소유자 승인 구성이므로 자기 실행 승인도 허용한다. 팀 저장소에서는 실제 담당 리뷰어를 지정하고 필요하면 자기 승인 방지를 켠다. 이는 기존 PR 리뷰 1명 필수 정책을 완화하지 않는다.
- AWS 활성화 스위치는 등록하거나 켜지 않았다. Environment를 만드는 것은 AWS EC2/RDS/S3/ECR 생성과 관계없다.

## 실검증에 필요한 값

Repository Variables: ECR_PUBLISH_ENABLED, AWS_REGION, AWS_ACCOUNT_ID, ECR_REPOSITORY, AWS_ECR_PUBLISH_ROLE_ARN. 실제 계정 OIDC Provider와 develop 신뢰 정책·ECR push 권한 역할, 사전 생성한 ECR 저장소가 필요하다.

배포는 추가로 COMPOSE_DEPLOY_ENABLED, 환경별 IMAGE_REPOSITORY, EC2_SSH_HOST·EC2_SSH_USER·EC2_SSH_PRIVATE_KEY·EC2_SSH_KNOWN_HOSTS와 서버의 Docker·RDS 설정이 필요하다. 실제 비밀키를 채팅으로 받지 않고 해당 GitHub Environment Secrets에 등록한다.

2026-11-05 확인 당시 위 AWS 관련 Repository Variables·Secrets는 없었다. 따라서 지금 완료 가능한 범위는 자동 연결 파일과 GitHub 브랜치/승인 정책·로컬 검사이며, ECR 실제 인증·게시 검증은 계정·권한 제공 후 진행한다. 새 워크플로는 PR 검토·병합 전에는 develop 운영 설정으로 적용되지 않는다.

## 완료 범위

- 작성: ECR 게시 → digest 확인 → 개발 자동 배포 연결, 발표 수동·승인 실행 조건.
- GitHub 적용: 개인 저장소 Environment·브랜치/승인 규칙(실행한 API 응답으로 재확인).
- 검증 대기: ECR 실제 인증·게시, 자동 개발 배포, 승인 게이트 실행, 실제 EC2·RDS 상태·복귀.
- 외부 조건 대기는 1주차 이월 대상이며 실제 검증 성공으로 표시하지 않는다.
