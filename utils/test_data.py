import json
from functools import lru_cache
from typing import Any

from utils.config import PROJECT_ROOT


@lru_cache(maxsize=1)
def load_test_data() -> dict[str, Any]:
    path = PROJECT_ROOT / "data" / "test_data.json"
    with path.open(encoding="utf-8") as data_file:
        data: Any = json.load(data_file)

    if not isinstance(data, dict):
        raise ValueError(f"Test data must be a JSON object: {path}")
    return data
