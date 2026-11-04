# CI·이미지 게시·ECS CD 파일 해설

## 먼저 설명할 전체 흐름

“PR에서 코드를 검사하고, develop 병합 후 실행 이미지를 보관합니다. 나중에 검증한 이미지를 선택해 ECS 서비스를 교체합니다. 이미지 만들기와 실제 서버 배포는 분리했습니다.”

| 파일 | 실행 시점 / 역할 | 지금 상태 |
|---|---|---|
| .github/workflows/ci.yml | PR 또는 다른 워크플로 호출 → 검사·테스트·빌드 | 개인 저장소에서 검증 |
| .github/workflows/publish-api.yml | develop push → 같은 커밋 검사 → GHCR 게시 | 개인 저장소에서 검증 |
| .github/workflows/deploy-ecs.yml | 활성화 후 수동 실행 → 검사 → AWS 배포 | 초안·실환경 미검증 |

YAML의 `#`는 설명용 주석입니다. `${{ ... }}`는 GitHub가 평가하는 표현식, 쉘의 `$NAME`은 runner 환경변수입니다. `vars`는 설정값, `secrets`는 비밀값, `inputs`는 수동 입력, `steps.<id>.outputs`는 앞 단계가 기록한 결과입니다. `uses`는 액션·재사용 워크플로 호출, `run`은 쉘 명령 실행입니다. `needs`는 job 실행 순서를 정합니다.

## Task Definition JSON 항목별 주석

JSON은 표준상 `#`·`//` 주석을 허용하지 않습니다. AWS에 제출하는 원본은 유효한 JSON으로 유지하고 이 표를 옆에 두고 읽습니다. ${...}는 tools/render_ecs_task.py가 GitHub Environment 값으로 바꿉니다.

| 항목 | 설명 / 말로 설명할 때 |
|---|---|
| family | 같은 앱 실행 설정의 이름. 등록할 때마다 revision이 증가합니다. |
| networkMode: awsvpc | 태스크에 네트워크 인터페이스가 연결되는 방식. 실제 서브넷·보안 그룹은 서비스 생성 때 지정합니다. |
| requiresCompatibilities: FARGATE | BE 초안은 Fargate 실행을 전제로 합니다. AI GPU 방식까지 결정한 것은 아닙니다. |
| cpu: 256 | BE 태스크에 0.25 vCPU를 할당하는 초기 검토값입니다. |
| memory: 512 | BE 태스크 메모리 512 MiB. 실측 후 조정해야 합니다. |
| runtimePlatform | Linux X86_64, 현재 게시 이미지의 linux/amd64와 맞춥니다. |
| executionRoleArn | ECS가 이미지 pull·로그 전송·DB Secret 주입을 수행할 때 쓰는 역할입니다. |
| taskRoleArn | 실행 중인 앱이 AWS 서비스에 접근할 때 쓰는 역할입니다. GitHub 배포 역할과도 다릅니다. |
| containerDefinitions | 태스크 안에서 실행할 컨테이너 목록. 현재 BE api 하나입니다. |
| name: api | 컨테이너 식별 이름. 서비스의 로드밸런서 설정과 일치해야 합니다. |
| image | 검증된 repository@sha256:digest 주소. 동일 이미지 내용을 배포합니다. |
| essential: true | 이 컨테이너가 종료되면 태스크를 계속 유지할 수 없다고 표시합니다. |
| portMappings | 컨테이너는 TCP 8000에서 요청을 받습니다. 이 값만으로 인터넷에 공개되지는 않습니다. |
| environment | 비밀이 아닌 앱 설정. APP_ENV·DB_HOST·DB_PORT·DB_NAME·DB_USER입니다. |
| secrets / valueFrom | Secrets Manager에서 DB_PASSWORD를 주입합니다. ARN은 위치이고 비밀번호 자체가 아닙니다. 현재 예시는 문자열 Secret 전체가 비밀번호인 경우입니다. |
| logConfiguration | stdout/stderr를 미리 만든 CloudWatch Log Group에 전송합니다. 로그 보존 기간·비밀정보 필터링은 별도 관리합니다. |
| healthCheck.command | 컨테이너 내부에서 /readyz를 호출하여 앱과 DB 쿼리 가능 여부를 확인합니다. 업무 E2E 전체 검사는 아닙니다. |
| interval / timeout / retries | 30초 주기, 한 검사 최대 5초, 연속 실패 3회 기준입니다. HTTP 요청 자체는 코드에서 3초 제한입니다. |
| startPeriod | 초기 60초는 기동 유예 기간입니다. 모델 로딩이 긴 AI 설정과 혼동하지 않습니다. |
| stopTimeout | 종료 신호 후 최대 30초 기다립니다. AI 작업 drain 설정은 별도로 설계해야 합니다. |

## OIDC 신뢰 정책 JSON 항목별 주석

“누가 AWS 배포 역할을 맡을 수 있는가”를 정의합니다. 이 파일을 저장소에 올려도 AWS에 자동 적용되지는 않습니다.

| 항목 | 설명 |
|---|---|
| Version: 2012-10-17 | IAM 정책 문법 버전입니다. 문서 작성 날짜가 아닙니다. |
| Statement / Effect: Allow | 아래 조건을 만족하는 요청에 해당 동작을 허용합니다. |
| Principal.Federated | AWS에 등록한 GitHub OIDC Provider ARN입니다. ACCOUNT_ID는 실제 계정으로 교체합니다. |
| Action: sts:AssumeRoleWithWebIdentity | GitHub 신원을 제시하여 단기 AWS 역할 세션을 얻는 동작입니다. |
| aud: sts.amazonaws.com | 이 토큰이 AWS STS를 대상으로 발급됐는지 확인합니다. |
| sub: repo:OWNER/REPOSITORY:environment:ENV | 특정 저장소의 특정 GitHub Environment 실행만 허용합니다. dev/demo를 각각 구성합니다. |

Environment를 쓰면 sub가 브랜치 형식이 아니므로, Environment의 허용 브랜치·승인 설정과 워크플로 조건을 함께 적용합니다. OIDC 토큰 발급 권한 자체가 ECS 조작 권한을 의미하지는 않습니다.

## 배포 권한 정책 JSON 항목별 주석

“역할을 맡은 GitHub가 무엇을 할 수 있는가”를 정의합니다.

| 항목 | 설명 |
|---|---|
| ecs:RegisterTaskDefinition / Resource: * | 새 revision 등록. 이 API에 대한 기본 예시이며 필요 시 추가 IAM 조건을 검토합니다. 모든 AWS 권한을 허용한다는 뜻은 아닙니다. |
| ecs:DescribeServices | 지정 서비스 상태·기존 실행 설정을 읽습니다. |
| ecs:UpdateService | 지정 서비스의 실행 revision을 변경합니다. 신규 네트워크·DB·클러스터 생성 권한은 없습니다. |
| Resource의 service ARN | 계정·리전·클러스터·서비스 하나로 권한 범위를 제한합니다. 자리표시자 교체가 필요합니다. |
| iam:PassRole | 등록할 태스크에 execution/task 역할을 연결할 수 있게 합니다. GitHub가 해당 역할의 모든 권한을 직접 쓰는 것은 아닙니다. |
| iam:PassedToService | 역할 전달 대상을 ecs-tasks.amazonaws.com으로 제한합니다. |

execution role에 필요한 ECR/GHCR·CloudWatch·Secret 접근 정책과 앱 task role 정책은 배포 권한 정책과 별도로 준비합니다. 네트워크·레지스트리 선택에 따라 달라집니다.

## CD 단계별 발표 설명

1. 사용자가 환경과 검증한 이미지 digest를 선택합니다. 기본값은 비활성이므로 임의 실행되지 않습니다.
2. 허용 브랜치·활성화 조건을 확인하고 코드 CI를 재실행합니다. 이 CI만으로 입력 이미지의 출처까지 증명되는 것은 아니며 릴리스 리뷰에서 digest·검증 이력을 대조합니다.
3. 필수 변수를 확인하고 Task Definition JSON을 만듭니다. 이 단계는 AWS에 연결하지 않습니다.
4. OIDC로 단기 배포 권한을 얻습니다. 장기 AWS 키를 GitHub Secret으로 저장하지 않는 방식입니다.
5. 기존 서비스와 복귀할 이전 revision을 확인합니다. 신규 서비스 생성 워크플로는 아닙니다.
6. 새 revision을 등록하고 기존 서비스를 교체합니다. 여기부터 실제 실행 자원에 영향을 줍니다.
7. 안정화뿐 아니라 새 revision인지 확인하고 /healthz·/readyz를 검사합니다. 이전 버전으로 자동 복귀한 상태를 성공으로 오인하지 않게 합니다.
8. 실패 시 이전 revision으로 복귀를 시도합니다. 취소·runner 중단·시간 초과 시에는 실행을 보장하지 못하므로 ECS 자체 복구·수동 절차가 필요합니다. DB 데이터·migration은 되돌리지 않습니다.

## 1주차 완료와 남은 일

완료는 CD 초안 작성·로컬 문법/렌더링 검증까지입니다. AWS 리소스·과금 실행은 시작하지 않았습니다. 3주차 예산 확인 뒤 실제 변수·역할·네트워크·DB·기존 서비스를 준비하고 배포·롤백을 검증합니다. 자세한 준비 항목은 [설정 가이드](README.md)를 참고합니다.
