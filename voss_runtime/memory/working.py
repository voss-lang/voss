from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class WorkingMemory:
    store: dict[str, Any] = field(default_factory=dict)

    def set(self, key: str, value: Any) -> None:
        self.store[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        return self.store.get(key, default)

    def clear(self) -> None:
        self.store.clear()

    def keys(self):
        return self.store.keys()

    def __contains__(self, key: str) -> bool:
        return key in self.store
