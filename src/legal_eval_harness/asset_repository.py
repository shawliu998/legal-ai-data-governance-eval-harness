from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable, TypeVar

from pydantic import BaseModel


T = TypeVar("T", bound=BaseModel)


class JsonlRepository:
    """Append-only JSONL repository with key-based idempotency."""

    def __init__(self, path: str | Path, model: type[T], key_field: str) -> None:
        self.path = Path(path)
        self.model = model
        self.key_field = key_field

    def all(self) -> list[T]:
        if not self.path.exists():
            return []
        rows: list[T] = []
        with self.path.open("r", encoding="utf-8") as fh:
            for line in fh:
                if line.strip():
                    rows.append(self.model.model_validate_json(line))
        return rows

    def get(self, key: str) -> T | None:
        return next((item for item in reversed(self.all()) if str(getattr(item, self.key_field)) == key), None)

    def append(self, item: T) -> bool:
        key = str(getattr(item, self.key_field))
        existing = self.get(key)
        if existing is not None:
            if existing.model_dump(mode="json") != item.model_dump(mode="json"):
                raise ValueError(f"duplicate key with different payload in {self.path}: {key}")
            return False
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(item.model_dump_json() + "\n")
        return True

    def replace_all(self, items: Iterable[T]) -> None:
        materialized = list(items)
        keys = [str(getattr(item, self.key_field)) for item in materialized]
        if len(keys) != len(set(keys)):
            raise ValueError(f"duplicate keys for {self.path}")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = "".join(item.model_dump_json() + "\n" for item in materialized)
        self.path.write_text(payload, encoding="utf-8")


def load_jsonl_dicts(path: str | Path) -> list[dict[str, Any]]:
    source = Path(path)
    if not source.exists():
        return []
    return [json.loads(line) for line in source.read_text(encoding="utf-8").splitlines() if line.strip()]
