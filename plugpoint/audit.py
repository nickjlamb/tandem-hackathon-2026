"""Append-only audit trail. Every entry says WHO did it:
AI (LLM), RULE (deterministic code), HUMAN (clinician), API (downstream system, mocked here),
SYSTEM (tracker/clock)."""

from __future__ import annotations

from datetime import date
from typing import Literal, Optional

Actor = Literal["AI", "RULE", "HUMAN", "API", "SYSTEM"]


class AuditLog:
    def __init__(self) -> None:
        self.entries: list[dict] = []
        self._seq = 0

    def record(self, today: date, actor: Actor, message: str, loop_id: Optional[str] = None,
               detail: Optional[dict] = None) -> dict:
        self._seq += 1
        entry = {
            "seq": self._seq,
            "date": today.isoformat(),
            "actor": actor,
            "message": message,
            "loop_id": loop_id,
            "detail": detail or {},
        }
        self.entries.append(entry)
        return entry

    def for_loop(self, loop_id: str) -> list[dict]:
        return [e for e in self.entries if e["loop_id"] == loop_id]
