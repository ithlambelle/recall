from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum


class Source(str, Enum):
    USER = "user"        # the user said it directly
    TOOL = "tool"        # returned by a tool the agent called
    WEB = "web"          # read from fetched/external content
    DERIVED = "derived"  # written by the agent from other memories (consolidation, summaries)


class Status(str, Enum):
    ACTIVE = "active"
    QUARANTINED = "quarantined"   # stored but never retrieved until reviewed
    DEACTIVATED = "deactivated"   # rolled back; kept for audit, never retrieved


BASE_TRUST = {Source.USER: 1.0, Source.TOOL: 0.6, Source.WEB: 0.2}


@dataclass
class Memory:
    id: str
    content: str
    source: Source
    tags: set[str]
    trust: float
    created_at: int
    status: Status = Status.ACTIVE
    derived_from: list[str] = field(default_factory=list)
    # Other memories that independently assert this memory's claim.
    # A derived memory with trusted independent support survives rollback.
    independent_support: list[str] = field(default_factory=list)


@dataclass
class Action:
    id: str
    task_id: str
    tool: str
    args: dict
    used_memories: list[str]
    created_at: int
    superseded_by: str | None = None
