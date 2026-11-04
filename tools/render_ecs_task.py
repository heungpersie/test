"""ECS 템플릿의 ${변수}를 환경변수로 채웁니다. AWS 접속·리소스 생성은 하지 않습니다."""
import json
import os
from pathlib import Path
import re
import sys


# 이미 JSON으로 읽은 구조를 처리하므로 따옴표·역슬래시를 포함한 값도 JSON 문법을 깨지 않습니다.
def render(template, values):
    """template: dict/list 구조, values: 환경변수 사전. 변환 결과를 반환합니다."""
    # 문자열·배열·객체를 재귀적으로 순회하고 숫자·boolean 값은 보존합니다.
    def visit(value):
        if isinstance(value, str):
            def replace(match):
                # ${DB_HOST}라면 DB_HOST를 추출합니다.
                key = match.group(1)
                result = values.get(key, '')
                # 누락 값이나 앞뒤 공백을 배포 전 오류로 처리합니다. 오류에는 실제 값을 출력하지 않습니다.
                if not result or result.strip() != result:
                    raise ValueError(f'Missing or whitespace-padded configuration: {key}')
                return result
            return re.sub(r'\$\{([A-Z_]+)\}', replace, value)
        if isinstance(value, list):
            return [visit(item) for item in value]
        if isinstance(value, dict):
            return {key: visit(item) for key, item in value.items()}
        return value
    result = visit(template)
    # latest 같은 이동 태그를 거부하고 전체 sha256 digest만 허용합니다.
    image = result['containerDefinitions'][0]['image']
    if not re.fullmatch(r'[a-z0-9./:_-]+@sha256:[a-f0-9]{64}', image):
        raise ValueError('Image must be a complete repository@sha256:digest reference')
    return result


if __name__ == '__main__':
    if len(sys.argv) != 3:
        raise SystemExit('Usage: render_ecs_task.py TEMPLATE OUTPUT')
    # 인수 1은 템플릿 경로, 인수 2는 출력 경로입니다. 실제 비밀번호 대신 Secret ARN만 담습니다.
    try:
        task = render(json.loads(Path(sys.argv[1]).read_text()), os.environ)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    # json.dumps가 특수문자를 올바르게 인코딩하며 원본 템플릿은 수정하지 않습니다.
    Path(sys.argv[2]).write_text(json.dumps(task, ensure_ascii=False, indent=2) + '\n')
    print('ECS task definition rendered; no AWS resources created')
