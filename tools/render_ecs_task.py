"""파일 역할: ECS Task Definition 템플릿의 ${변수}를 환경변수로 채웁니다.

입력: 명령행의 템플릿 JSON 경로·출력 경로, GitHub Environment에서 전달한 환경변수.
출력: 변수 치환과 이미지 digest 검사를 통과한 JSON 파일.
실행 위치: CD의 AWS 인증 전 사전 검사 단계. AWS 접속·리소스 생성은 하지 않습니다.
전체 흐름: JSON 읽기 → 재귀적 변수 치환 → digest 검사 → JSON 저장.
"""
import json
import os
from pathlib import Path
import re
import sys


# 1. 템플릿 변환
# 문자열·배열·객체를 순회합니다. 누락/공백 값을 거부하고 오류에 실제 값을 노출하지 않습니다.
# JSON 구조에서 치환하므로 따옴표·역슬래시 값도 저장 시 안전하게 인코딩됩니다.
def render(template, values):
    """template: dict/list 구조, values: 환경변수 사전. 변환 결과를 반환합니다."""
    def visit(value):
        if isinstance(value, str):
            def replace(match):
                key = match.group(1)
                result = values.get(key, '')
                if not result or result.strip() != result:
                    raise ValueError(f'Missing or whitespace-padded configuration: {key}')
                return result
            return re.sub(r'\$\{([A-Z_]+)\}', replace, value)
        if isinstance(value, list):
            return [visit(item) for item in value]
        if isinstance(value, dict):
            return {key: visit(item) for key, item in value.items()}
        return value
    # 2. 결과 검증: 이동 태그를 거부하고 전체 sha256 digest 주소만 허용합니다.
    result = visit(template)
    image = result['containerDefinitions'][0]['image']
    if not re.fullmatch(r'[a-z0-9./:_-]+@sha256:[a-f0-9]{64}', image):
        raise ValueError('Image must be a complete repository@sha256:digest reference')
    return result


# 3. 명령행 실행: 입력 형식을 확인하고 변환 결과를 별도 파일에 저장합니다.
# 원본 템플릿은 유지하며 DB 비밀번호 대신 Secret ARN만 설정 파일에 담습니다.
if __name__ == '__main__':
    if len(sys.argv) != 3:
        raise SystemExit('Usage: render_ecs_task.py TEMPLATE OUTPUT')
    try:
        task = render(json.loads(Path(sys.argv[1]).read_text()), os.environ)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    Path(sys.argv[2]).write_text(json.dumps(task, ensure_ascii=False, indent=2) + '\n')
    print('ECS task definition rendered; no AWS resources created')
