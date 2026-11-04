# 이미지 태그·게시 규칙과 개인 저장소 검증

2026-11-04 · GHCR을 개인 저장소 검증용 기본안으로 사용한다. 파일 작성 완료이며 GitHub 게시·서버 배포 검증은 아직 수행하지 않았다. Compose/Kubernetes 선택과 독립적으로 사용한다.

## 이름과 버전

- 레지스트리: ghcr.io.
- BE 이미지: ghcr.io/<소유자>/<저장소명>-api. GitHub repository 값을 소문자로 변환하여 자동 생성한다.
- 태그: sha-<전체 Git 커밋 SHA>. 같은 커밋 태그를 다른 소스에 재사용하지 않는다.
- 배포 식별자: 이미지주소@sha256:<digest>. 태그는 재게시될 수 있으므로 실제 검증·배포 이력은 digest로 기록한다.
- 플랫폼: 현재 linux/amd64 하나. ARM 또는 다른 실행 환경이 필요하면 플랫폼 설정과 해당 환경 실행 검증을 추가한다.
- FE·AI: 준비되면 -web·-ai 접미사를 사용한다. 현재는 이미지 게시 대상이 아니다.
- latest·develop 같은 이동 태그는 현재 게시하지 않는다.

소유자 seunghye3760-afk의 저장소 이름이 바뀌거나 팀 저장소로 이동해도 워크플로 내 이름 수정은 필요 없다. 기존 패키지·권한·Secrets·배포 이력은 자동 이전되지 않는다.

## 실행 흐름

작업 PR → API CI → develop 병합 → 동일 커밋의 CI 재실행 → 통과 시 BE 이미지 빌드·GHCR 등록 → Actions Summary에 태그·digest 기록.

publish-api.yml은 develop push에서 실행한다. workflow_dispatch 수동 실행도 develop을 선택해야 하며 다른 브랜치에서는 게시 job이 건너뛰어진다. ci.yml에 workflow_call을 추가하여 기존 lint·format·mypy·pytest·Docker 빌드 검사를 재사용한다. PR CI에는 이미지 게시 권한을 추가하지 않는다. 게시 job만 contents: read, packages: write를 사용한다.

main 릴리스 PR에서 검증된 이미지 digest를 기록한다. main 병합 시 이미지를 자동 재빌드하지 않는다. main의 merge commit SHA와 이미지 소스인 develop SHA는 다를 수 있으므로 둘 다 기록한다. 환경별 CD와 승인·릴리스 기록 자동화는 아직 미구현이다.

## 개인 저장소 적용 순서

1. 실제 코드와 .github/workflows를 개인 저장소에 올리고 main·develop을 준비한다. 실제 .env·토큰은 올리지 않는다.
2. main·develop PR 보호와 필수 CI는 CONTRIBUTING.md에 따라 설정한다. 새 저장소에 Actions 실행이 허용되는지 확인한다.
3. 변경을 작업 브랜치에서 develop으로 PR하여 API checks·API Docker build 통과를 확인한다.
4. 병합 후 Publish API image 실행의 validate와 publish 성공을 확인한다.
5. GitHub Packages에서 <저장소명>-api와 커밋 태그를 확인하고 Actions Summary의 digest를 보관한다.
6. 아래 방식으로 이미지를 pull하여 실행한다. API·DB 통합 검증은 별도 환경에서 수행한다.

GHCR 게시에는 자동 GITHUB_TOKEN을 사용하므로 별도 PAT Secret을 요구하지 않는다. 조직 정책·기존 패키지 권한 때문에 packages 쓰기가 제한될 수 있으며, 기존 패키지라면 해당 저장소의 Actions 접근 권한을 확인한다. 비공개 이미지를 로컬·배포 서버에서 pull하는 인증은 별도다. 비공개 상태를 유지하고 read:packages 등 필요한 권한을 가진 계정으로 인증한다. 토큰 원문을 명령 인수나 문서에 넣지 말고 docker login --password-stdin 방식으로 전달한다.

## pull 및 실행 확인

Actions Summary의 실제 digest를 사용한다. 다음은 자리표시자 예시이므로 그대로 실행하지 않는다.

```bash
docker pull ghcr.io/<소유자>/<저장소명>-api@sha256:<digest>
docker run --rm -p 127.0.0.1:18000:8000 --env-file <테스트용-API-env-파일> ghcr.io/<소유자>/<저장소명>-api@sha256:<digest>
```

테스트용 API env 파일은 api/.env.example의 변수를 기준으로 별도 작성하고 Git에서 제외한다. DB_HOST는 컨테이너에서 실제 접근 가능한 DB 주소여야 한다. 기존 Compose의 postgres라는 이름은 같은 Docker 네트워크에서만 해석된다. 현재 로컬 운영 중인 DB·볼륨을 삭제하거나 비밀번호를 변경하지 않는다.

다른 터미널에서 /healthz는 앱 생존을, /readyz는 DB 쿼리 연결을 검사한다.

```bash
curl --fail http://127.0.0.1:18000/healthz
curl --fail http://127.0.0.1:18000/readyz
```

/healthz 성공만으로 DB·업무 API·큐·AI 연결 검증을 완료 처리하지 않는다. 현재 업무 분석 경로는 미구현이다. Apple Silicon에서 amd64 이미지는 에뮬레이션이 필요할 수 있으므로 실제 배포 아키텍처에 맞게 검증한다.

## 완료 상태

- 작성: 이미지 규칙, CI 재사용, develop 병합 후 이미지 게시 워크플로.
- 대기: 실제 개인 저장소 업로드·브랜치 보호·Actions 성공·GHCR pull 및 실행 검증.
- 후속: 배포 자원 확정 후 CD 인증·서비스 교체·상태 검사·롤백 연결. 이미지 게시만으로 CD 전체 완료로 표시하지 않는다.

공식 근거: [GitHub 패키지 게시 인증·권한](https://docs.github.com/en/packages/managing-github-packages-using-github-actions-workflows/publishing-and-installing-a-package-with-github-actions), [Container registry 인증·접근](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry).
