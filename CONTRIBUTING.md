# Git 브랜치·PR 협업 규칙

2026-11-03 · 브랜치 구조: 사용자 선택 확정. 아래 리뷰·병합·보호 세부 설정은 팀 적용안이며 GitHub 적용은 미확인.

## 브랜치 구조

main·develop과 짧은 작업 브랜치를 사용한다. 작업 브랜치는 최신 develop에서 생성하고 일반 작업 PR은 develop으로 보낸다. develop에서 FE·BE·AI·인프라를 통합 검증한 뒤 develop → main 릴리스 PR로 반영한다. main은 발표·배포 기준 코드다. main 병합 자체가 실제 배포 완료를 뜻하지 않으며 태그·이미지·배포 승인 방식은 후속 배포 규칙에서 정한다.

```text
작업 브랜치 → PR → develop → 릴리스 PR → main
                   통합·검증             발표·배포 기준
```

main과 develop은 유지하고, 병합이 끝난 작업 브랜치만 삭제한다. 기본 브랜치는 팀 설정에 따라 확인하되 일반 작업 PR의 대상은 develop인지 명시적으로 확인한다.

| 접두사 | 용도 | 예시 |
|---|---|---|
| feat/ | 기능 | feat/fe-upload, feat/be-analysis-api, feat/ai-worker |
| fix/ | 버그 수정 | fix/be-upload-validation |
| infra/ | 실행 환경·네트워크·저장소 | infra/analysis-queue |
| ci/ | 검사·빌드 자동화 | ci/pr-checks |
| cd/ | 배포 자동화 | cd/demo-deploy |
| docs/ | 문서·다이어그램 | docs/deployment-architecture |
| refactor/ | 동작을 유지하는 코드 개선 | refactor/be-db-session |
| test/ | 검증 코드·시나리오 | test/analysis-load |

브랜치 이름은 소문자 영문·숫자·하이픈으로 작성한다. 장기간 유지하는 FE/BE/AI별 브랜치를 만들지 않고 검토 가능한 변경 목적별로 나눈다.

## PR 흐름 — 팀 적용안

1. 최신 develop에서 작업 브랜치를 만든다. 이 로컬 폴더는 유효한 Git 저장소로 확인되지 않았으므로 clone 또는 연결 상태를 먼저 확인한다.
2. 하나의 변경 목적을 구현하고 관련 검사를 수행한다. 미완성 작업은 Draft PR로 공유한다.
3. develop을 대상으로 PR을 생성하고 변경 목적·검증 결과·관련 서비스 영향을 작성한다.
4. 작성자 외 팀원 1명 이상이 리뷰하고 필수 CI 통과 후 병합한다. API 계약 변경은 관련 FE·BE, 분석 계약 변경은 BE·AI 담당자에게 리뷰를 요청한다.
5. 작업 → develop은 Squash merge를 기본 제안으로 사용한다. 병합 뒤 해당 작업 브랜치를 삭제한다.
6. 통합 검증 후 develop → main 릴리스 PR을 만든다. 포함 변경·검증 결과·이미지/배포 영향·복귀 절차를 리뷰하고 필수 CI 통과 후 반영한다. 장기 브랜치의 공통 이력을 유지하도록 이 PR은 merge commit 방식을 제안한다. main·develop은 삭제하지 않는다.
7. main만 수정한 긴급 PR이 있다면 즉시 main → develop 동기화 PR로 반영한다. 긴급 변경도 리뷰와 CI를 거친다.

main·develop 직접 push와 force push를 제한한다. 새 커밋이 올라오면 이전 승인을 무효화하고 변경분을 다시 검토하는 것을 제안한다. 긴급 변경도 PR·검증을 거친다. 브랜치 보호의 실제 강제 여부는 GitHub 설정에 달려 있다.

## 현재 CI와 필수 검사 후보

설정 근거: [.github/workflows/ci.yml](.github/workflows/ci.yml).

| 체크 이름 | 범위 |
|---|---|
| API checks | uv 잠금 의존성 설치, Ruff lint·format, mypy, pytest |
| API Docker build | api/Dockerfile 이미지 빌드 검증 |

현재 CI는 모든 PR에서 API 검사를 실행한다. FE·AI 검사, 이미지 게시, CD, GPU 실환경 검증이 포함된 것은 아니다. 워크플로 파일의 존재만으로 GitHub 실행 성공을 간주하지 않는다. 필수 검사에는 실제 PR 실행에서 나타나는 체크 이름을 확인해 등록한다.

## PR에 반드시 남길 정보

- 해결하는 문제와 변경된 동작.
- 수행한 검사와 결과. 미실행은 이유를 명시한다.
- FE·BE·AI 간 요청/응답 변경과 이전 버전 호환 여부.
- DB migration, 새 환경변수, 배포 순서, 진행 중 AI 작업에 대한 영향.
- 복귀 방법. DB 변경은 이전 이미지 배포만으로 복구된다고 가정하지 않는다.

비밀번호·토큰·실제 .env·서명 URL을 커밋하거나 PR 로그에 첨부하지 않는다. Secret은 이름과 용도만 문서화하고 값은 환경별 비밀 저장소에 등록한다.

## GitHub 적용 체크리스트 — 아직 미적용

저장소 관리자가 대상 저장소의 main·develop 보호 규칙에 적용한다. GitHub 플랜·조직 정책에 따른 기능 제공 여부를 확인한다.

- [ ] main·develop 존재 여부와 기본 브랜치 설정 확인. 일반 PR 대상은 develop으로 안내.
- [ ] PR을 통한 변경만 허용하고 승인 1명 이상 요구.
- [ ] 실제 실행한 API checks·API Docker build를 필수 검사로 등록.
- [ ] 리뷰 대화 해결 요구·새 커밋 시 기존 승인 무효화 설정 검토.
- [ ] force push·브랜치 삭제 제한, 우회 권한 대상을 확인.
- [ ] Squash merge와 merge commit 허용. 작업 PR은 squash, 릴리스 PR은 merge commit 사용을 안내. 장기 브랜치가 자동 삭제되지 않도록 보호 설정 후 작업 브랜치 자동 삭제 검토.
- [ ] 테스트 PR에서 CI 실패 시 병합이 차단되는지 확인.

다음 단계: 레지스트리·이미지 이름·불변 태그 규칙 결정. 그다음 BE 이미지 게시와 환경별 CD를 연결한다.
