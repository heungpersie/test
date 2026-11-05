# 비용·실행 시간·자원 정리 계획

작성·공식 자료 조회: 2026-11-04 (KST). 1주차 문서 계획이며 AWS 생성·설정 변경·중지·삭제를 실행하지 않았다. 실제 AWS 검증은 3주차다.

## 미확정 조건과 산정 방법

계정·리전·총예산/월예산·EC2/GPU 사양·RDS 사양·사용 일정·보존 기간은 미정이다. ap-northeast-2는 기존 예시일 뿐 확정이 아니다. 금액은 제시하지 않는다. 담당자 답변 후 같은 리전의 공식 단가로 계산하고 승인받는다. 무료 티어·크레딧은 계정 적용 여부 확인 전 차감하지 않는다.

견적 기록 항목: 조회일, 계정 과금 조건, 리전/AZ, 통화, 환율 적용일·세금, OS/CPU 아키텍처, 구매 방식, 수량, 시간, 용량, 요청 수, 전송 경로, 공식 URL, 단가·계산식·소계, 크레딧 적용 전/후 금액. 보관 비용은 실행 시간으로 줄이지 않고 실제 보관 기간으로 계산한다. 월 환산 기준과 시간/초 과금·최소 과금 단위는 각 서비스 조건을 적용한다. 예약·Savings Plans 등 약정 구매는 별도 결정 없이는 사용하지 않는다.

| 구분 | 견적 입력·계산 항목 | 중지 후 남는 비용 | 공식 자료 |
|---|---|---|---|
| EC2 API/선택 AI GPU | 타입·OS·아키텍처별 단가 × 대수 × 실제 실행 시간(준비·재시작·실패 복구 포함), 버스터블 초과 CPU 크레딧·라이선스 조건 | EBS-backed 인스턴스 stopped 이후 컴퓨팅 과금 중단. EBS·IP·별도 자원과 약정 비용은 별개 | [EC2 가격](https://aws.amazon.com/ec2/pricing/on-demand/) |
| EBS | root/data 볼륨별 provisioned GB × 보관 기간, 추가 IOPS·처리량 | 연결 해제·EC2 중지 상태에서도 볼륨 보관 과금 | [EBS 가격](https://aws.amazon.com/ebs/pricing/) |
| RDS PostgreSQL | 클래스·엔진 버전·Single/Multi-AZ별 단가 × 실행 시간, 할당 스토리지·추가 IOPS/처리량, Extended Support 해당 여부 | stopped여도 스토리지·해당 IOPS·백업 과금 유지 | [RDS 가격](https://aws.amazon.com/rds/postgresql/pricing/) |
| 백업 | RDS 자동 백업·수동/최종 스냅샷·EBS 스냅샷별 청구 대상 GB·기간, 복사·복원·리전 간 전송 | 원본 중지·삭제 후 남긴 백업 계속 과금 가능. 무료 할당은 실제 조건 확인 | [RDS 가격](https://aws.amazon.com/rds/postgresql/pricing/) / [EBS 가격](https://aws.amazon.com/ebs/pricing/) |
| S3 | 원본·결과·버전·미완료 multipart GB·기간, PUT/GET/LIST, lifecycle 전환·조회·최소 보관/최소 객체 크기 조건 | EC2/RDS 중지와 무관하게 객체·버전·미완료 업로드 보관 과금 | [S3 가격](https://aws.amazon.com/s3/pricing/) |
| ECR private | 저장 이미지 GB·기간, 전송, 선택 스캔/복제 비용 별도 | 서버 중지 후에도 이미지 보관·복제본 비용 | [ECR 가격](https://aws.amazon.com/ecr/pricing/) |
| 트래픽 | 영상 업/다운로드·이미지 pull·API 응답량, 인터넷 송신·AZ 간·리전 간 경로별 GB. 서비스별 면제 조건을 확인해 중복 계산 방지 | 별도 서비스가 계속 통신하면 발생 | [EC2 전송](https://aws.amazon.com/ec2/pricing/on-demand/) / [S3](https://aws.amazon.com/s3/pricing/) / [ECR](https://aws.amazon.com/ecr/pricing/) |
| 로그 | 현재 Docker json-file 컨테이너당 10 MB × 3개, EBS 사용량에 포함. CloudWatch는 미도입: 도입 시 수집·보관·조회 스캔·지표·알람 구분 | 로컬 파일은 EBS 비용, CloudWatch 도입 후 저장 로그는 중지 후에도 과금 가능 | [CloudWatch 가격](https://aws.amazon.com/cloudwatch/pricing/) |
| 네트워크 추가 자원 | public IPv4/EIP 수·시간, NAT Gateway 시간·처리 GB, interface endpoint 시간·GB. 선택 여부 미정 | EIP/NAT/endpoint는 EC2 중지만으로 제거되지 않음 | [VPC 가격](https://aws.amazon.com/vpc/pricing/) |

ALB·Route 53/도메인·CloudFront·KMS 고객 관리 키·Secrets Manager·큐·외부 AI API·유료 ECR 스캔 등은 현재 채택하지 않았다. 선택 시 해당 공식 가격 URL/조회일과 고정·사용량·보관 비용 행을 추가한 후 총액을 다시 승인받는다. GPU는 제공 환경·필요 메모리·모델·동시성 확인 후 별도 행으로 산정한다. 현재 이미지 linux/amd64와 EC2 아키텍처 호환성을 먼저 확인한다.

## 필요한 시간만 실행하는 일정안

아래는 운영 제안이며 날짜·요일·시각·시간 수는 담당자 합의 후 기입한다. KST로 기록한다. 자동 중지 스케줄·자동화 자원은 아직 만들지 않는다.

| 단계 | 실행 범위 | 담당자 기록 |
|---|---|---|
| 1~2주차 | 로컬 개발·파일/CI 확인. AWS 게시·배포 비활성 유지 | AI 로컬 실행 가능 여부 확인 |
| 3주차 검증 세션 전 | 승인된 자원만 시작. RDS available → EC2 status checks → Docker/API → 선택 AI 순서. RDS 복구는 수분~수시간 걸릴 수 있으므로 사전 측정한 여유 시간 확보 | 시작 담당자, 예정 시작/종료, 예상 시간·비용 |
| 세션 중 | ECR push/pull, RDS TLS·권한, S3 업/다운로드, 배포·복귀·외부 HTTPS 순으로 검증. GPU는 분석 시험 구간에만 실행 | 실행 시간, 입력 용량·요청 수, 결과·digest |
| 세션 종료 | 신규 작업 차단·진행 Job 종료/상태 보존 → API/Worker 중지 → EC2 중지 → 의존 앱 종료 확인 후 RDS 중지 | 실제 stopped 상태·종료시각·잔존 자원·다음 시작 |
| 발표 | 리허설에서 측정한 준비 시간 전에 시작, 발표/복구 여유 구간만 운영 후 같은 종료 절차 | 발표 책임자·종료 확인자 |
| 비사용일 | 담당자가 stopped 상태·청구·잔존 자원 확인. RDS 자동 재시작 예정일도 기록 | 다음 확인일과 대응 담당자 |

RDS는 연속 최대 7일 중지 후 자동 재시작한다. 무기한 중지로 계산하지 않는다. 자동 재시작을 예산·점검 일정에 반영하고 재시작 후 방치하지 않는다. 시작 시점과 실제 상태를 확인해 사용 시간을 기록한다. [공식 RDS 중지 조건](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_StopInstance.html)

예산 관리안: 담당자가 총액/월 상한과 알림 임계값·수신자를 정하고 AWS Budgets 사용 여부·비용을 확인한다. 세션 전 예상 잔액, 종료 후 실제 사용량과 보관 예상액을 대조한다. 알림은 자동 지출 차단을 보장하지 않으며 청구 반영 지연도 고려한다. 한도 초과 예상 시 다음 실행을 보류하고 담당자에게 판단을 요청한다.

## 중지·재시작 절차 — 문서만 작성

1. 계정·리전·환경·자원 ID·소유자·공유 여부를 대장으로 대조한다. dev/demo가 같은 EC2/RDS라면 양쪽 사용 종료를 확인한다. 현재 실행 digest/current 릴리스·DB 스키마 버전·Job 상태를 기록한다. 비밀번호·키는 기록하지 않는다.
2. 유입을 차단하고 처리 중 작업의 종료/재시도 상태를 BE/AI 정책에 따라 보존한다. 필요한 DB 백업·S3 결과와 원본 대응표를 확인한다. 아직 Job 정책 미합의라면 강제 중지하지 않는다.
3. 서버의 대상 환경·프로젝트·기존 환경 파일·current Compose를 명시하여 API/Worker만 stop한다. down -v·volume prune·DB migration은 수행하지 않는다. 컨테이너 stop만으로 EC2 과금이 멈추지 않는다.
4. AWS 콘솔에서 해당 EBS-backed EC2를 Stop하고 stopped를 확인한다. Terminate와 구분한다. 의존 앱이 모두 종료된 다음 지원되는 구성의 RDS를 Stop하고 stopped 및 자동 재시작 기한을 기록한다. 백업·유지보수·복제 구성에 따른 제한은 적용 전에 확인한다.
5. 재시작은 RDS Start → available/endpoint/TLS 확인 → EC2 Start → 상태 검사·Docker·네트워크 확인 순서다. EC2 일반 public IPv4는 바뀔 수 있으므로 DNS·접속 주소·GitHub SSH host 설정을 확인한다. host key는 독립 확인하며 검증을 끄지 않는다. [EC2 중지/시작](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/Stop_Start.html)
6. restart: unless-stopped로 명시 stop한 컨테이너는 재부팅만으로 복귀하지 않을 수 있다. 보존한 환경 파일·프로젝트·current digest로 Compose up --wait를 명시하고 /healthz·/readyz, DB 격리·S3·외부 HTTPS를 확인한다. 새 이미지를 임의로 배포하거나 migration을 실행하지 않는다. 문제가 있으면 기존 복귀 절차와 증거를 따른다.

## 삭제 계획 — 실제 삭제 금지, 보존 승인 후 별도 실행

| 대상 | 보존할 것 | 이후 승인된 정리 절차 |
|---|---|---|
| RDS | 필요한 메타데이터·스키마·Job/결과 참조, 최종 스냅샷/논리 백업, 복원 확인·만료일 | 백업 복원 검증·소유자 승인 → 삭제 보호 해제 여부 검토 → 최종 스냅샷/자동 백업 유지 선택 → DB 삭제. 남긴 스냅샷도 별도 만료 시 정리 |
| S3 | 동의된 기간 내 원본·분석 결과·DB 참조 대응, 개인정보 보존 근거 | 원본/결과 만료를 구분. 버전·delete marker·미완료 multipart·복제본·Object Lock 확인 후 승인 범위 삭제, 빈 버킷만 제거 |
| ECR | 발표·현재·복귀용 digest와 대응 코드/빌드 기록 | 활성·복귀 digest를 제외한 이미지만 만료. 불변 SHA 태그가 있으므로 untagged 규칙만으로는 정리가 안 됨. lifecycle preview 후 승인·적용 |
| EC2/EBS | 필요한 설정·릴리스 manifest·모델 버전·최소 장애 증거, 비밀정보는 별도 안전한 저장소 | root/data DeleteOnTermination 확인 → 종료 승인 → EC2 terminate → 남은 EBS·AMI·스냅샷 개별 점검. 기존 로컬 DB/볼륨은 대상에서 제외 |
| 네트워크·로그·기타 | 필요한 감사 로그·보존 기한, 공유 자원 소유자 | 미사용 EIP·NAT·endpoint·LB·로그 그룹·DNS·키/Secret 등 사용 여부 확인 후 별도 승인 정리. 공유 자원·복원용 KMS 키 임의 삭제 금지 |

대장 필수 열: 계정/리전/ID, 용도·환경·소유자, 생성/시작/중지 시각, 잔존 비용 종류, 백업 위치·접근 책임자·복원 결과·만료일, 삭제 승인자/기한, 실제 정리 결과. 빈 대장이 정리 완료 증거는 아니다. 정리 후 리전별 자원 목록과 Billing/Cost Explorer를 나중에 재확인하며, 삭제 직후 비용이 사라진다고 단정하지 않는다.

## 계정·예산 담당자에게 물을 질문

1. 사용할 AWS 계정·소유자·청구 책임자와 허용 리전은? 교육/조직 정책·서비스 제한·데이터 위치 요건은?
2. 전체/월 예산, 통화·세금·환율 기준, 크레딧/무료 티어 적용 조건·만료일은? 초과 시 연락·중지 판단 책임자는?
3. 3주차 실행 날짜·KST 시작/종료·주당 횟수·발표 가용 시간과 비사용일 중지 확인 담당자는? RDS 7일 후 자동 재시작은 누가 관리하는가?
4. EC2 CPU/RAM/디스크·아키텍처·대수는? AI GPU는 제공되는가, 필요 VRAM·모델·동시성·실행 시간은? GPU 할당량·지원 환경은?
5. RDS 엔진/지원 버전·클래스·용량·IOPS·Single/Multi-AZ, dev/demo 공유 여부와 복구 목표(RPO/RTO), 백업 보관 기간은?
6. 영상 크기·일 업로드/분석 수·동시성·결과 크기·다운로드 횟수와 원본/결과/백업별 보존·삭제 기한은? S3 버전 관리·암호화 요구는?
7. 승인된 VPC/AZ·기존 공유 자원, SSH runner 접속 경로·외부 HTTPS·도메인 방식은? IPv4/EIP·NAT·endpoint·LB 추가 비용 허용 범위는?
8. ECR 저장 용량·태그 불변·발표/복귀 이미지 보존 수·스캔/복제 여부, 로그 수집·보존 기간은?
9. OIDC/IAM·EC2 역할·RDS 앱 계정·비밀정보 발급 담당자와 게시/배포 활성화 승인자는? 팀 저장소와 리뷰·브랜치 보호 책임자는?
10. 종료 시 보존 데이터 인수자·접근 기간·삭제 승인자·공유 자원 제외 목록·청구 재확인 담당자는?

답변 전 리전·사양·금액·삭제일을 확정하지 않는다. 질문은 전달용 문서로만 정리했으며 타인에게 메시지를 보내지 않았다.
