from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def json_loads_or_none(value: Any) -> Any | None:
    if value is None:
        return None
    if isinstance(value, (dict, list)):
        return value
    text = str(value).strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def extract_first_json_object(text: str) -> dict[str, Any]:
    """Parse strict JSON or extract the first balanced JSON object from text."""
    text = (text or "").strip()
    if not text:
        raise ValueError("empty text")
    try:
        value = json.loads(text)
        if isinstance(value, dict):
            return value
        raise ValueError("JSON root is not an object")
    except json.JSONDecodeError:
        pass

    start = text.find("{")
    if start < 0:
        raise ValueError("no JSON object start found")

    depth = 0
    in_string = False
    escape = False
    for idx in range(start, len(text)):
        ch = text[idx]
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return json.loads(text[start : idx + 1])
    raise ValueError("no balanced JSON object found")


def safe_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value != value:
        return ""
    return str(value).strip()


def slug_tokens(text: str) -> list[str]:
    return [t for t in re.split(r"[^A-Za-z0-9_\-\u4e00-\u9fff]+", text or "") if t]

