# AWS 저장 서비스 결정·인증 설정

2026-11-04 사용자 결정: 실행 EC2 + Docker Compose, DB Amazon RDS for PostgreSQL, 영상·분석 파일 Amazon S3, 컨테이너 이미지 Amazon ECR(private). GHCR은 개인 저장소 검증 이력으로만 보존한다. 이번 작업은 파일 수정이며 AWS 자원 생성·정책 적용·실제 연결은 수행하지 않았다.

## 서비스별 준비·아직 남은 것

| 서비스 | 이번 반영 | 실제 적용 시 필요 |
|---|---|---|
| RDS PostgreSQL | DB_HOST를 RDS endpoint로 사용, dev/demo DB·계정 구분, 배포 Compose의 verify-full TLS·공식 CA 읽기 전용 마운트 | 엔진 버전·사양·리전·백업·비용·endpoint, 앱 계정 생성, EC2→RDS 보안 그룹 5432, 권한 격리·TLS 검증 |
| S3 | 원본·결과 저장소로 선정, 환경별 bucket/prefix 예약 명세·배치도 반영 | 실제 버킷·권한·CORS·서명 URL·보관/삭제 정책·BE/AI SDK 연동. 현재 API에 업로드 구현 없음 |
| ECR | OIDC push 워크플로, EC2 인스턴스 역할 pull·임시 로그인, 커밋 태그·digest | 저장소 생성·불변 태그·수명 정책, 역할·권한·계정 변수, 실제 push/pull·실행 확인 |

## ECR GitHub 설정

Repository Variables:

- ECR_PUBLISH_ENABLED: 기본 미설정. 계정/저장소/역할 준비 후 true로 설정해야 실제 게시 job 실행.
- AWS_REGION: 실제 리전. 예시는 ap-northeast-2이며 확정 아님.
- AWS_ACCOUNT_ID: 12자리 계정 ID.
- ECR_REPOSITORY: 사전 생성한 이미지 저장소 이름. 예: presentation-api. 소유자/리포 이름 자동 사용 대신 명시적으로 지정한다.
- AWS_ECR_PUBLISH_ROLE_ARN: GitHub OIDC 게시 역할 ARN.

GitHub Environment aws-dev/aws-demo의 IMAGE_REPOSITORY는 <ACCOUNT_ID>.dkr.ecr.<REGION>.amazonaws.com/<ECR_REPOSITORY>로 설정한다. COMPOSE_DEPLOY_ENABLED는 서버 준비 전까지 비활성으로 유지한다. 현재 초안은 AWS commercial partition용이며 China/GovCloud는 주소·ARN·인증 설정을 별도 검토한다.

게시 흐름: develop CI 통과 → 활성화 확인 → OIDC 인증 → 동일 커밋 태그 확인 → ECR 로그인 → 새 이미지 빌드·게시 또는 기존 digest 재사용. 동일 SHA 재실행에서 이미지를 덮어쓰지 않는다. 이미 존재하는 태그의 출처·무결성은 해당 저장소의 쓰기 권한과 태그 불변 정책으로 관리한다. 강제 재빌드는 새 커밋으로 진행한다.

## 권한 파일 설명

- github-ecr-trust.template.json: 지정 저장소 develop 실행만 GitHub 게시 역할을 맡을 수 있도록 한다. workflow는 Environment를 쓰지 않으므로 sub는 ref 형식이다. GitHub 브랜치 보호도 적용한다.
- github-ecr-push-policy.template.json: 토큰 발급과 지정 ECR 저장소에만 업로드/조회 허용. 자원 생성·EC2 접속·DB·S3 권한은 없음.
- ec2-ecr-pull-policy.template.json: EC2 인스턴스 역할에 붙일 읽기 전용 정책. 인스턴스 역할의 신뢰 주체는 ec2.amazonaws.com이며 실제 역할/instance profile 생성은 별도다.

JSON의 <...>는 계정별 치환 전 자리표시자다. 정책 파일을 GitHub에 올려도 AWS에 자동 적용되지 않는다. ECR 로그인 토큰은 단기이므로 배포 때마다 AWS CLI로 갱신하며 서버 스크립트는 임시 DOCKER_CONFIG를 종료 시 정리한다. 정적 AWS access key를 EC2나 GitHub에 저장하지 않는다.

## RDS 연결

배포 서버에 AWS 공식 RDS CA bundle을 준비하고 RDS_CA_BUNDLE_HOST_PATH로 위치를 지정한다. Compose는 /etc/ssl/rds/global-bundle.pem에 읽기 전용 마운트한다. DB_HOST는 증명서 호스트명과 맞는 실제 RDS endpoint를 사용한다. Pydantic DB URL에는 SSL 파라미터를 덮어쓰지 않으므로 Psycopg/libpq의 PGSSLMODE=verify-full·PGSSLROOTCERT가 적용된다. 로컬 개발 Compose에는 이 TLS 설정을 추가하지 않는다.

CA 파일은 공개 자료이며 비밀번호가 아니다. 공식 배포 주소: https://truststore.pki.rds.amazonaws.com/global/global-bundle.pem . 최초 준비와 갱신 때 출처·인증서 유효 기간을 확인한다. 빈 파일이나 임의 인증서로 TLS 검증을 통과시키지 않는다. RDS는 외부 공개를 기본으로 요구하지 않으며 EC2→DB 네트워크를 제한한다. DB 비밀번호는 서버의 환경별 shared/api.env에 별도 보관한다.

## S3 환경 구분과 미구현 경계

AWS_REGION, S3_BUCKET, S3_PREFIX를 환경별 예시에 예약했다. prefix 기본안은 dev/·demo/이며 버킷명은 계정·리전·전역 이름 가용성 확인 후 결정한다. 별도 버킷 또는 동일 버킷+prefix와 IAM 제한을 선택할 수 있다. 모든 버킷은 비공개로 두고 서명 URL로 특정 객체·작업·기한만 허용한다.

현재 Compose·BE는 S3 변수를 사용해 파일을 처리하지 않는다. 이후 SDK 코드와 최소 권한 자격 공급 방식, role 기반 prefix 제한을 함께 구현하고 검증해야 한다. 이름만 다른 prefix는 접근 제어가 아니다. SSE·보관/삭제·CORS·미완료 업로드 정리·영상 용량은 별도 정책 항목으로 남긴다. S3 자격을 준다는 이유로 ECR 전용 GitHub 게시 역할에 S3 권한을 추가하지 않는다.

## 검증 상태·공식 근거

파일 구문·환경 혼선 차단·설정 해석은 로컬에서 확인한다. 실제 ECR 게시·RDS TLS·S3 업로드·EC2 배포는 3주차 AWS 자원과 예산 준비 후 검증한다. 기존 GHCR 성공 기록을 새 ECR 성공으로 표시하지 않는다.

- [ECR 인증 토큰](https://docs.aws.amazon.com/cli/latest/reference/ecr/get-login-password.html)
- [RDS PostgreSQL TLS](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/PostgreSQL.Concepts.General.SSL.html)
