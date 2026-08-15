from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class Action(StrEnum):
    ADD = "ADD"
    REMOVE = "REMOVE"


class SourceMode(StrEnum):
    AUTO = "auto"
    REACTIONS = "reactions"
    POLL = "poll"


@dataclass(frozen=True, slots=True)
class Candidate:
    user_id: int
    display_name: str


@dataclass(slots=True)
class SyncSummary:
    matched: int = 0
    changed: int = 0
    would_change: int = 0
    skipped: int = 0
    failed: int = 0

    @property
    def exit_code(self) -> int:
        return 1 if self.failed else 0
