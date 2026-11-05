#!/usr/bin/env bash
# 파일 역할: EC2에서 이미지 digest로 BE를 교체하고 실패하면 이전 릴리스로 복귀합니다.
# 입력: 배포 루트, 업로드된 릴리스 디렉터리, 검증한 이미지 digest.
# 전제: Docker Compose v2(--wait 지원), Python 3, flock, DB 연결, AWS CLI v2·EC2 인스턴스 역할, shared/api.env 사전 준비.
# 범위: 서버/DB 생성·migration·TLS·AI 배포는 수행하지 않습니다.
set -euo pipefail

# 1. 입력과 서버 환경 확인: 원격 경로·이미지 형식을 제한하고 배포를 잠급니다.
base=${1:?deployment root}; release=${2:?release directory}; image=${3:?image digest}
[[ "$base" =~ ^/opt/presentation/(dev|demo)$ ]] || exit 2
[[ "$release" =~ ^$base/releases/[0-9]+-[0-9]+$ ]] || exit 2
[[ "$image" =~ ^([0-9]{12})\.dkr\.ecr\.([a-z]{2}-[a-z]+-[0-9]+)\.amazonaws\.com/[a-z0-9._/-]+@sha256:[a-f0-9]{64}$ ]] || exit 2
registry="${image%%/*}"
ecr_region="${BASH_REMATCH[2]}"
[[ -f "$base/shared/api.env" && -f "$release/compose.yaml" ]] || exit 2
exec 9>"$base/deploy.lock"
flock -n 9 || { echo 'Another deployment is active' >&2; exit 1; }
export COMPOSE_PROJECT_NAME="presentation-${base##*/}"
chmod 600 "$base/shared/api.env"
previous=''
if [[ -L "$base/current" ]]; then previous=$(readlink -f "$base/current"); fi
printf '%s\n' "$image" > "$release/image.txt"

# 2. 공통 실행 설정: 환경 파일·프로젝트명을 고정하여 dev/demo가 섞이지 않게 합니다.
compose() {
  local directory=$1; shift
  API_IMAGE=$(cat "$directory/image.txt") docker compose --env-file "$base/shared/api.env" -f "$directory/compose.yaml" "$@"
}
# 실패 복귀도 동일한 조건으로 검사하며 민감한 환경값·로그는 출력하지 않습니다.
probe() {
  compose "$1" exec -T api /app/.venv/bin/python -c "import urllib.request; print([(p, urllib.request.urlopen('http://127.0.0.1:8000'+p, timeout=5).status) for p in ['/healthz','/readyz']])"
}

# 3. 변경 전 검사·pull: 실패해도 현재 실행 버전을 건드리지 않습니다.
compose "$release" config --format json | python3 "$release/validate_environment.py" "${base##*/}"
# EC2에 연결한 읽기 전용 인스턴스 역할로 인증합니다. GitHub의 push 역할과 분리합니다.
# 로그인 토큰을 영구 저장하지 않도록 임시 Docker 설정을 사용하며 종료 시 삭제합니다.
export DOCKER_CONFIG
DOCKER_CONFIG=$(mktemp -d)
trap 'rm -rf "$DOCKER_CONFIG"' EXIT
aws ecr get-login-password --region "$ecr_region" | docker login --username AWS --password-stdin "$registry"
compose "$release" pull api

# 4. 서비스 교체·상태 확인: 새 버전 성공 시에만 current 포인터를 갱신합니다.
if compose "$release" up -d --no-build --wait --wait-timeout 120 api && probe "$release"; then
  ln -sfn "$release" "$base/current.next"
  mv -Tf "$base/current.next" "$base/current"
  echo "Deployment passed: $image"
else
  # 5. 이전 릴리스의 Compose와 digest로 복귀합니다. DB·서버 환경 파일은 복구하지 않습니다.
  echo 'Deployment failed; attempting recovery' >&2
  if [[ -n "$previous" && -f "$previous/image.txt" ]]; then
    compose "$previous" up -d --no-build --wait --wait-timeout 120 api
    probe "$previous"
    echo "Previous release restored: $previous" >&2
  else
    # 첫 배포 실패에는 복귀 버전이 없으므로 실패한 API만 정리합니다. 볼륨 삭제는 하지 않습니다.
    compose "$release" stop api
    compose "$release" rm -f api
    echo 'No previous release; failed API stopped' >&2
  fi
  exit 1
fi
