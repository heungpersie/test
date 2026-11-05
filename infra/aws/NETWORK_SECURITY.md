# AWS 네트워크·보안 설계 v1

작성: 2026-11-05 · 범위: 1주차 분석·설계. AWS 리소스 생성·정책 적용·공용 접속·보안 검증은 수행하지 않았다.

확정된 것은 EC2 + Docker Compose, RDS PostgreSQL, S3, ECR이다. 아래 네트워크·권한·암호화는 검토할 설계안이며 팀 승인·예산·계정별 실제 값과 구분한다. 데이터별 보관·삭제와 감사 로그 상세는 후속 문서 범위다.

## 1. 결정·구현 상태

| 항목 | 상태 | 근거 / 남은 조건 |
|---|---|---|
| 배포·저장 서비스 | 사용자 결정 | EC2/Compose·RDS·S3·ECR |
| BE 환경 분리·RDS TLS | 파일 작성·로컬 검사 | 환경/DB/포트 검사, verify-full·CA 마운트. 실 RDS 접속 미검증 |
| ECR 게시·pull 역할 | 파일 작성 | GitHub OIDC push / EC2 instance role pull. AWS 적용 미실행 |
| 사설 앱 배치·진입점 | 설계안 | VPC·ALB·NAT/endpoint·운영 접속 비용/제공 환경 확인 필요 |
| S3 앱 권한·LLM 인증 | 조건부 설계 | BE/AI 호출 주체·모델·데이터 범위 합의 필요. 현재 SDK 연동 없음 |
| 저장 암호화·운영 권한 | 설계안 | 계정 정책·KMS·관리 담당자 확인 후 적용 |

## 2. 네트워크 배치안

### 기본 검토안 — 앱과 DB를 사설망에 배치

- VPC 내부에 공개 진입 서브넷, 사설 앱 서브넷, 사설 DB 서브넷을 구분한다. 실제 CIDR·AZ·리전은 계정 네트워크 담당자가 제공하고 중복 여부를 검토한다.
- 인터넷-facing ALB는 공개 서브넷, 앱 EC2·AI 실행 자원은 사설 앱 서브넷에 둔다. RDS는 사설 DB subnet group에 배치하고 publicly accessible=false로 설정한다. subnet group에 여러 AZ가 필요하다는 것과 유료 Multi-AZ DB 배포 선택은 구분한다.
- 외부 HTTPS는 ALB에서 받고, 앱 EC2의 reverse proxy에 HTTPS로 전달한다. proxy→BE는 같은 호스트 loopback:18000(dev)/18001(demo)다. EC2 proxy·인증서·ALB 대상 그룹 설정은 미구현이며 실제 별도 검증한다.
- 현재 Compose는 API를 loopback에만 바인딩한다. ALB가 loopback API에 직접 붙는 구성은 동작하지 않으므로 proxy를 먼저 구성해야 한다. HTTP 내부 전달을 선택할 경우 암호화 예외·위험을 별도로 승인한다.
- 사설 앱에서 S3는 gateway endpoint를 우선 검토한다. ECR의 api/dkr interface endpoints·S3 경로 또는 NAT egress를 비교한다. 외부 LLM·업데이트 등 공용 인터넷 목적지는 별도의 outbound 경로가 필요하다. endpoint를 만들었다고 모든 외부 통신이 해결되는 것은 아니다.
- 사설 DB 서브넷에는 인터넷 기본 경로가 필요하지 않다. NACL은 임의 강화보다 SG/라우팅 검증 후 상태 비저장 특성·응답 ephemeral port를 고려해 설계한다.

ALB·NAT·interface endpoints는 고정/사용량 비용이 있으므로 예산 확정 전 생성하지 않는다. [비용 계획](COST_OPERATIONS.md)에 채택 항목을 반영한다. S3 gateway endpoint 경로는 VPC 라우팅에 연결하는 것이며 S3가 EC2 안에 생기는 것은 아니다.

### 예산 대안 — 공개 앱 EC2 + 사설 RDS

단일 EC2의 reverse proxy를 인터넷 HTTPS 입구로 쓰고 RDS는 사설망에 유지할 수 있다. ALB·NAT 등을 줄일 수 있지만 앱 EC2 자체는 public subnet이므로 “앱 전체 프라이빗 배치” 기준을 충족했다고 표시하지 않는다. 요구사항 책임자 승인 후에만 대안으로 채택하고 SG·SSH 접속 제한은 유지한다. 현재 배치도는 호스트 관점의 논리 그림이며 이 두 서브넷 대안을 확정한 그림은 아니다.

## 3. 허용 통신·보안 그룹 명세안

| 출발지 → 목적지 | 프로토콜·포트 | 허용 기준 | 그 외 |
|---|---|---|---|
| 사용자 → HTTPS 진입점 | TCP 443 | 서비스 대상 사용자의 접근. 인증은 BE에서 별도 검사 | 80은 필요 시 HTTPS redirect만 |
| ALB SG → 앱 proxy SG | TCP 443 | 지정 ALB SG에서만. proxy의 TLS 리스너 필요 | 공용 IP→앱 직접 접근 금지 |
| proxy → BE | 호스트 loopback HTTP 18000/18001 → 컨테이너 8000 | 동일 EC2의 지정 포트 | API 8000/18000/18001 인터넷 공개 금지 |
| 앱 SG → RDS SG | PostgreSQL TCP 5432·TLS | 지정 앱 SG만, 앱 DB 계정 사용 | 0.0.0.0/0·사용자 단말 DB 직접 접근 금지 |
| AI → RDS | TCP 5432·TLS, 조건부 | 직접 DB 접근 계약 채택 시 지정 AI SG·최소 DB 권한만 | 완료 API 방식을 채택하면 이 연결은 제거 |
| 관리 runner/운영 접속점 → EC2 | SSH TCP 22 | 승인된 VPN/고정 egress 또는 별도 관리망만 | 인터넷 전체 22 허용 금지 |
| EC2 host → ECR | HTTPS 443 | 지정 리전 registry·필요한 API/레이어 경로 | instance role은 지정 저장소 pull만 |
| BE/AI → S3 | HTTPS 443 | 지정 버킷·환경 prefix·작업에 제한 | 버킷 public 읽기 금지 |
| 브라우저 → S3 | HTTPS 443 | BE 소유권 확인 후 발급한 PUT/GET 서명 URL | 브라우저 AWS 자격정보 배포 금지 |
| AI → Bedrock/외부 LLM | HTTPS 443, 조건부 | 선정한 리전·모델/업체와 최소 입력만 | 임의 모델·전체 원본 전송 금지 |
| BE ↔ 큐/AI | 방식·포트 미정 | 실행 계약 확정 후 내부 SG 간만 허용 | 임의 Redis 등 포트를 미리 공개하지 않음 |

SG는 상태 저장이므로 응답용 inbound 전체 포트를 추가하지 않는다. SG outbound는 TLS 목적지·DB·DNS·필요 서비스에 제한하는 방향으로 설계한다. SG는 외부 LLM의 도메인 allowlist 기능이 아니므로 동적 공용 목적지 제한은 egress proxy/방화벽 등 추가 방식을 검토한다.

### 기존 SSH CD와 사설망의 연결 조건

현재 GitHub-hosted runner는 사설 EC2에 직접 SSH할 수 없다. 기본 검토안에서는 사설망 경로가 있는 전용 배포 runner/VPN 등을 준비하거나 SSM 배포로 워크플로를 변경해야 한다. 전용 runner를 프로덕션 앱 서버에 겸용 배치하거나 신뢰하지 않는 PR을 배포 runner에서 실행하지 않는다. CI의 GitHub-hosted runner는 유지한다. 네트워크 경로가 준비되기 전 COMPOSE_DEPLOY_ENABLED는 켜지 않는다. 별도 runner·VPN 제공 가능성 및 비용은 미확정이다.

## 4. 인증·권한 경계

| 주체 | 허용할 권한 | 주지 않을 권한 | 구현 상태 |
|---|---|---|---|
| 브라우저 USER | 본인 프로젝트·작업·보고서 조회, 지정 서명 URL | S3 장기 키·DB·ECR·운영 권한 | 업무 인증은 BE 범위, 현재 완료로 간주하지 않음 |
| GitHub 게시 역할 | 지정 ECR push·조회·로그인 | RDS·S3 데이터·Bedrock·EC2 생성 | OIDC·push 정책 예시 있음 |
| GitHub 배포 주체 | Environment 승인 후 제한된 SSH 배포 | DB 비밀번호 전달·권한 변경·인프라 생성 | SSH CD 초안·GitHub 승인 정책 있음 |
| EC2 host 역할 | 지정 ECR pull | 이미지 push·관리자 권한 | pull 정책 예시 있음 |
| BE runtime 역할 | 승인된 환경 S3 입력 업로드 URL 발급·소유 결과 읽기 등 필요한 작업만 | 다른 환경 객체·버킷 설정·무조건 전체 삭제 | 설계만. 정확한 prefix/action은 API 계약에 맞춰 확정 |
| AI runtime 역할 | 해당 작업 입력 읽기·산출물 쓰기, 선택한 LLM 호출 | 타인 작업 전체 열람·사용자/버킷/IAM 관리 | 설계만 |
| 정리 작업 역할 | 만료·철회가 확인된 객체만 정책 범위 삭제 | 서비스 운영자 전체 권한 | 수명주기 문서에서 상세 정의 예정 |
| 운영자 | 배포·장애 확인·필요한 집계/로그 | 기본적인 원본 영상·전사 열람 | 임시 예외 접근 사유·범위·종료·기록 필요 |

S3 prefix·DB명만 다르게 해서는 보안 경계가 만들어지지 않는다. 실제 IAM·DB GRANT와 BE의 소유권 검사를 함께 적용해야 한다. DB migration 계정과 runtime 계정 권한은 분리한다. AI가 DB에 직접 쓰는지 완료 API를 호출하는지는 기존 계약 제안 상태이며 팀 결정 전 권한을 넓히지 않는다.

### Compose의 역할 격리 한계

Compose에는 ECS task role 같은 자동 컨테이너별 AWS 역할 경계가 없다. 같은 호스트의 컨테이너들이 IMDS에 접근하면 인스턴스 역할을 공유할 수 있다. Docker 그룹·소켓 접근자도 호스트/컨테이너 Secret을 읽을 수 있다. 환경파일과 Docker 네트워크만으로 강한 권한 격리를 주장하지 않는다.

현재 host 역할은 ECR pull만 유지한다. S3·Bedrock runtime 권한은 별도 실행 머신/역할, 제한된 임시 자격 공급 또는 중앙 호출 서비스 중 하나를 선택하고 테스트한다. 단순히 모든 AWS 권한을 host 역할에 합치는 방식은 기본안으로 삼지 않는다. IMDSv2를 필수로 하고 필요한 컨테이너 경로만 허용한다. 컨테이너에서 IMDS를 사용할 때 hop limit·SSRF 위험을 검토하고 자격정보 노출·무단 역할 사용을 시험한다.

## 5. Bedrock / 외부 LLM 조건부 인증 설계

제품·모델은 미선정이며 두 서비스를 동시에 채택한 것은 아니다. 호출 주체는 원칙적으로 AI 서버/워커, 프론트 직접 호출은 금지한다.

| 선택 | 인증·Secret | 최소 권한·연결 | 확정할 사항 |
|---|---|---|---|
| Bedrock 선택 시 | SDK의 단기 IAM 자격·SigV4를 우선 제안. 장기 access key 미사용 | bedrock:InvokeModel, streaming 시에만 InvokeModelWithResponseStream. 지정 모델 및 필요한 inference profile/하위 모델 ARN에만 제한 | 리전·모델 ID·모델 접근·cross-region 처리 여부·runtime 역할·비용 |
| 외부 LLM 선택 시 | 업체 API 키를 AI 환경의 Secret으로 보관하고 서버에서만 주입 | 지정 업체 HTTPS endpoint와 계정/프로젝트·요청량 제한 | 업체·키 발급/폐기 주체·요금·제공자 데이터 이용/보관 조건 |

Bedrock API key 방식도 존재하지만 이번 기본안은 IAM 단기 자격이다. 실제 서비스 선정 후 인증 방식을 하나로 확정한다. 외부 업체 Secret 저장소는 Secrets Manager 또는 전용 호스트의 권한 600 파일 중 예산·운영 조건에 따라 선택한다. 두 경로 모두 FE·Git·이미지·평문 로그로 전달하지 않는다. 발급·교체·노출 시 폐기 담당자를 지정한다.

LLM에는 필요한 비식별 전사·지표 요약만 전달하는 것을 기본 제안으로 하고 원본 영상·얼굴 프레임·이메일·식별자를 자동 전송하지 않는다. 품질상 원문이 필요하면 데이터 범위·목적·제공 지역·동의·업체 보관 조건을 확인한 뒤 명시적으로 결정한다. 네트워크가 막힌 경우 보안 검증이나 모델 권한을 넓혀 해결하지 않는다.

## 6. 비밀정보 저장·교체

| 대상 | 현재/제안 위치 | 접근·주입 | 교체·폐기 |
|---|---|---|---|
| GitHub AWS 인증 | OIDC 단기 역할 | develop 신뢰 조건·ECR 최소 권한 | 신뢰 정책 변경·세션 수명/기존 세션 영향 확인 |
| 배포 SSH 키 | GitHub Environment Secret | 전용 배포 계정·검증된 known_hosts | authorized_keys와 Secret 동시 교체·호스트 교체 시 신뢰 재확인 |
| DB 비밀번호 | EC2 환경별 shared/api.env, 권한 600 | 지정 앱 계정으로 컨테이너 환경 주입 | DB 실제 비밀번호 변경과 환경 파일/서비스 갱신을 함께 수행 |
| 외부 LLM 키 | AI 전용 Secret, 위치 미확정 | 선택된 AI 프로세스만 | 업체에서 폐기·새 키 적용 후 호출 검증 |
| RDS CA bundle | EC2 공개 인증서 파일 | 앱에 읽기 전용 마운트 | 공식 CA 교체·유효 기간·호스트명 검증 |

설정 예시에는 실제 값을 넣지 않는다. SSH·DB·LLM 키는 개발/발표에 재사용하지 않는다. 로그·오류 메시지·Compose config 전체 출력·Actions artifact에 값을 남기지 않는다. 파일 기반 Secret은 암호화 서비스나 컨테이너별 비밀 격리를 대신하지 않는다. 노출 시 커밋 삭제만 하지 말고 자격을 폐기·재발급한다.

## 7. 암호화·S3 접근 설계안

| 대상 | 전송 | 저장·키 기본 제안 | 검증·주의 |
|---|---|---|---|
| 브라우저/API | HTTPS, 운영 시 HTTP 본문 전송 금지 | 이미지/디스크 별도 관리 | 인증서·호스트명·만료, 필요 Origin만 CORS |
| RDS PostgreSQL | PGSSLMODE=verify-full + 공식 CA | 생성 시 RDS 암호화 활성화·AWS 관리 KMS 키 우선 검토 | TLS 강제·암호화 설정·snapshot/restore 확인. 이미 생성된 평문 DB를 설정 한 줄로 바꿀 수 있다고 가정하지 않음 |
| EC2 root/data EBS | 서버 관리 접속 SSH | 생성 시 EBS 암호화·기본 aws/ebs 키 검토 | 스냅샷·복원·키 접근 범위 확인 |
| S3 원본·결과 | HTTPS, 비TLS 요청 거부 | 명시적 default SSE-S3 제안. 별도 키 통제 요구면 SSE-KMS로 변경·비용/권한 검토 | Block Public Access, ACL 비활성·bucket owner enforced, 실제 default encryption 확인 |
| ECR | HTTPS·단기 로그인 | 서비스 저장 암호화 설정 확인, KMS 선택은 요구 확인 후 | 불변 태그·최소 push/pull·digest 검증 |
| 백업·로그·Secret 파일 | 접근 경로 암호화 | 원본 서비스·디스크 암호화 유지, 별도 복사본도 확인 | 키 삭제/비활성화로 복원이 막힐 수 있으므로 데이터/백업 종료와 함께 관리 |

S3 암호화는 소유권 검사를 대신하지 않는다. 원본·결과는 별도 key 경로로 나누고 BE가 사용자·회차·객체를 검증한 뒤 짧은 유효기간의 URL을 발급한다. URL TTL 수치는 BE·FE 업로드 조건 확인 후 정한다. 서명 URL은 기한 내 재사용 가능하므로 일회용이라고 설명하지 않는다. URL 전체를 로그에 남기지 않는다. MIME·크기·길이는 실제 업로드 완료 검사도 필요하다.

서버의 S3 gateway endpoint만 허용하도록 bucket policy를 무조건 작성하면 외부 브라우저의 서명 URL 업로드/재생까지 막힌다. 서버 전용 경로와 외부 서명 URL 경로를 구분하고 최소 권한·TLS·환경 범위를 함께 검사한다. CORS는 브라우저 정책이며 IAM 인증이나 원본 데이터 권한을 대체하지 않는다.

## 8. 1주차 산출물과 3주차 확인

| 확인 항목 | 지금 작성할 근거 | AWS 적용 후 시험 |
|---|---|---|
| 네트워크 | 이 문서의 subnet·route·SG·접속 대안 | 공용 접속·허용 포트 성공, 직접 API/DB/무단 SSH 실패 |
| 인증 | ECR OIDC/pull 예시 + runtime/LLM 조건부 설계 | 잘못된 브랜치/역할/모델·타 환경 접근 거부 |
| 비밀정보 | 저장·주입·교체 표 | 누락 시 실패·로그 비노출·폐기한 자격 거부 |
| 암호화 | 서비스별 전송/저장/키 기준 | RDS 평문/잘못된 CA 거부, S3 공개/비TLS 거부·암호화 확인 |
| 공용 개발 접근 | 승인 계정·VPN/runner 경로 계획 | 제공 계정으로 접속·역할 분리·접근 종료 확인 |

3주차 실검증은 계정·권한·예산·자원 제공을 조건으로 이월한다. 이 문서 작성은 “설계 초안 작성” 근거이고 정책 적용·공용 환경 접근 완료 근거는 아니다.

## 9. 결정 대기 목록

| ID | 필요한 결정 | 협의 대상 | 결정 조건 |
|---|---|---|---|
| N01 | 사설 앱 기본안 또는 공개 앱 비용 대안, 관리 runner/VPN 경로 | 인프라·계정 제공자·요구사항 책임자 | private 요구 충족 여부·예산·제공 네트워크 |
| N02 | VPC/CIDR·AZ·리전·실제 SG·egress 방식 | 인프라·계정 제공자 | 자원 제공 정보·접속 시험 계획 |
| S01 | BE/AI runtime AWS 자격 공급과 별도 실행 범위 | BE·AI·인프라 | Compose 역할 격리 한계·GPU 위치·작업 계약 |
| S02 | Bedrock/외부 업체·모델·리전·전달 데이터 | AI·BE·제품 담당 | 품질·비용·데이터 취급·호출 주체 |
| S03 | Secret 보관 서비스·교체 담당·KMS 고객 키 필요 여부 | 인프라·팀 | 예산·운영 책임·계정 정책 |

보관 기간·삭제 SLA·데이터별 사용자 권한은 다음 데이터 수명주기 문서에서 구체화하고 감사 필드·보관·조회 권한은 감사 로그 문서에서 다룬다. 이 파일이 해당 후속 작업까지 완료한 것은 아니다.

## 공식 근거 (2026-11-05 확인)

- [사설 앱·NAT·S3 경로](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-example-private-subnets-nat.html)
- [S3 gateway endpoint](https://docs.aws.amazon.com/vpc/latest/privatelink/vpc-endpoints-s3.html)
- [RDS PostgreSQL TLS](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/PostgreSQL.Concepts.General.SSL.html)
- [RDS 저장 암호화](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/Overview.Encryption.html)
- [S3 서버 측 암호화](https://docs.aws.amazon.com/AmazonS3/latest/userguide/serv-side-encryption.html)
- [Bedrock IAM·모델 권한](https://docs.aws.amazon.com/bedrock/latest/userguide/security_iam_id-based-policy-examples.html)
- [Bedrock API key 대안](https://docs.aws.amazon.com/bedrock/latest/userguide/api-keys.html)
- [EC2 IMDS·컨테이너 설정](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/configuring-instance-metadata-options.html)
