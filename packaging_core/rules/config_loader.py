from pathlib import Path

import yaml


RULES_DIR = Path(__file__).resolve().parent


def load_yaml_config(relative_path: str) -> dict:
    path = RULES_DIR / relative_path
    with path.open("r", encoding="utf-8") as file:
        config = yaml.safe_load(file)
    return config or {}
