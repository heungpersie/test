# 이미지 태그·ECR 게시 규칙

2026-11-04 · 이미지 저장소는 Amazon ECR(private)로 선정. 과거 GHCR의 성공 검증은 [개인 저장소 검증 기록](GITHUB_TEST_RESULT.md)에 보존하며 ECR 동작 성공을 의미하지 않는다. 이번 수정은 설정 작성으로 AWS 자원·이미지는 생성하지 않았다.

## 이름·태그

- 이미지: <ACCOUNT_ID>.dkr.ecr.<REGION>.amazonaws.com/<ECR_REPOSITORY>.
- 태그: sha-<전체 커밋 SHA>.
- 배포 식별자: 이미지주소@sha256:<digest>. 이동 태그 latest는 사용하지 않는다.
- 동일 SHA가 존재하면 재빌드·덮어쓰기 대신 기존 digest를 반환한다. ECR 저장소는 불변 태그를 권장하며 잘못 게시한 이미지는 새 수정 커밋으로 교체한다.
- 플랫폼 linux/amd64. ARM 서버 도입 시 이미지 아키텍처 검증이 별도로 필요하다.
- 현재는 BE만 게시한다. FE·AI 저장소 이름과 이미지는 코드 준비 후 추가한다.

## 실행·인증

develop push 또는 develop 수동 실행 → 같은 커밋의 CI → ECR_PUBLISH_ENABLED=true인 경우에만 게시 job → OIDC 단기 AWS 역할 인증 → ECR 로그인 → 빌드·push 또는 기존 digest 확인 → Summary 기록.

Repository Variables AWS_ACCOUNT_ID·AWS_REGION·ECR_REPOSITORY·AWS_ECR_PUBLISH_ROLE_ARN을 준비한다. 기본 게시 비활성으로 계정이 없을 때 AWS 인증·빌드 게시를 시도하지 않는다. GitHub의 packages:write·GITHUB_TOKEN 로그인은 GHCR 전용이므로 제거했고 대신 id-token:write와 AWS ECR 전용 역할을 사용한다.

EC2는 별도 읽기 전용 인스턴스 역할로 ECR에서 이미지를 pull한다. GitHub 게시 역할에 SSH 키·RDS·S3 권한을 몰아주지 않는다. [AWS 권한 예시](../../infra/aws/README.md), [Compose 배포 준비](../../infra/deploy/README.md)를 따른다.

## 적용·검증 대기

1. 계정·리전·예산 확인 후 ECR 저장소·OIDC Provider·게시 역할·EC2 pull 역할 준비.
2. Repository Variables·GitHub Environment의 IMAGE_REPOSITORY·배포 SSH Secrets를 설정. ECR_PUBLISH_ENABLED만 먼저 활성화하면 이미지 게시만 진행하고 서버 배포는 하지 않는다.
3. 테스트 PR CI 통과·develop 병합 후 ECR 게시 성공, 태그·커밋·digest 대응 확인.
4. 서버에서 해당 digest pull·기동·RDS TLS 연결 확인.
5. 같은 SHA 재실행에서 기존 digest 재사용, 권한 실패 시 게시 중단을 확인.

실제 서버 배포·롤백은 COMPOSE_DEPLOY_ENABLED와 별도 승인을 사용하며 3주차에 검증한다. ECR 게시·RDS·S3 연결을 GHCR 과거 실행으로 완료 처리하지 않는다.
