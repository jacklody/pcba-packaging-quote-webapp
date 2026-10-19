import json


def to_json(result: dict) -> str:
    return json.dumps(result, ensure_ascii=False, indent=2)
