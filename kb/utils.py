import json
from datetime import datetime
from typing import Any

from kb.config import timezone


def now_iso() -> str:
    return datetime.now(timezone()).isoformat()


def json_dumps(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, sort_keys=True)


def normalize_text(value: str | None) -> str:
    return (value or "").replace("\x00", " ").strip()
