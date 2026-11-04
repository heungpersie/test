"""Render ECS JSON safely; never prints DB credentials or connects to AWS."""
import json
import os
from pathlib import Path
import re
import sys


def render(template, values):
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
    result = visit(template)
    image = result['containerDefinitions'][0]['image']
    if not re.fullmatch(r'[a-z0-9./:_-]+@sha256:[a-f0-9]{64}', image):
        raise ValueError('Image must be a complete repository@sha256:digest reference')
    return result


if __name__ == '__main__':
    if len(sys.argv) != 3:
        raise SystemExit('Usage: render_ecs_task.py TEMPLATE OUTPUT')
    try:
        task = render(json.loads(Path(sys.argv[1]).read_text()), os.environ)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    Path(sys.argv[2]).write_text(json.dumps(task, ensure_ascii=False, indent=2) + '\n')
    print('ECS task definition rendered; no AWS resources created')
