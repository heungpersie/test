"""파일 역할: 배포 직전 Compose의 실제 해석 결과가 dev/demo 대상과 맞는지 검사합니다.

입력: 인수 dev|demo와 stdin의 docker compose config --format json 결과.
출력: 성공/실패만 표시합니다. JSON 원문·DB 비밀번호를 출력하거나 AWS에 접속하지 않습니다.
범위: 프로젝트·환경명·DB명·계정·포트 혼선을 차단합니다. 실제 DB 권한 격리는 별도 검증합니다.
"""
import json
import sys

# 1. 환경별 고정 기준: 같은 EC2를 사용하더라도 프로젝트·포트·DB·계정을 구분합니다.
POLICIES = {
    'dev': {'project': 'presentation-dev', 'port': '18000',
            'db': 'coach_dev', 'user': 'coach_dev_app'},
    'demo': {'project': 'presentation-demo', 'port': '18001',
             'db': 'coach_demo', 'user': 'coach_demo_app'},
}


def validate(config, target):
    """원문 값을 포함하지 않는 오류 목록을 반환합니다."""
    if target not in POLICIES:
        return ['대상 환경은 dev 또는 demo여야 합니다.']
    policy = POLICIES[target]
    errors = []
    api = config.get('services', {}).get('api', {})
    env = api.get('environment', {})

    # 2. 해석된 환경·데이터 연결 검사. APP_ENV 하나만 바꾸는 실수를 차단합니다.
    checks = [
        (config.get('name') == policy['project'], 'Compose 프로젝트명이 대상 환경과 다릅니다.'),
        (env.get('APP_ENV') == target, 'APP_ENV가 대상 환경과 다릅니다.'),
        (env.get('DB_NAME') == policy['db'], 'DB_NAME이 대상 환경과 다릅니다.'),
        (env.get('DB_USER') == policy['user'], 'DB_USER가 대상 환경과 다릅니다.'),
        (bool(env.get('DB_PASSWORD')), 'DB_PASSWORD가 비어 있습니다.'),
        (env.get('PGSSLMODE') == 'verify-full' and
         env.get('PGSSLROOTCERT') == '/etc/ssl/rds/global-bundle.pem',
         'RDS 연결은 verify-full 및 지정 CA 경로를 사용해야 합니다.'),
        (bool(env.get('DB_HOST')) and env.get('DB_HOST', '').lower() not in
         {'localhost', '127.0.0.1', '::1', 'postgres', 'host.docker.internal'},
         'DB_HOST는 사전 준비한 배포 DB의 접근 가능한 주소여야 합니다.'),
    ]
    for valid, message in checks:
        if not valid:
            errors.append(message)

    # 3. 외부 직접 공개·다른 환경 포트 사용 차단. HTTPS 진입점은 별도 구성합니다.
    ports = api.get('ports', [])
    if not (len(ports) == 1 and ports[0].get('host_ip') == '127.0.0.1'
            and str(ports[0].get('published')) == policy['port']
            and ports[0].get('target') == 8000):
        errors.append('API 포트는 대상 환경의 loopback 전용 포트여야 합니다.')
    return errors


if __name__ == '__main__':
    # 4. CLI 진입: 비밀번호가 포함될 수 있는 입력·예외 원문을 로그에 노출하지 않습니다.
    if len(sys.argv) != 2:
        raise SystemExit('사용법: docker compose ... config --format json | python3 validate_environment.py dev|demo')
    try:
        data = json.load(sys.stdin)
        if not isinstance(data, dict):
            raise ValueError
        errors = validate(data, sys.argv[1])
    except (ValueError, TypeError, AttributeError, KeyError):
        raise SystemExit('Compose 해석 결과 형식이 올바르지 않습니다.') from None
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        raise SystemExit(1)
    print('배포 환경 분리 검사 통과: ' + sys.argv[1])
