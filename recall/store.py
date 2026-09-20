from __future__ import annotations
import copy
from typing import Iterable, Protocol
from .models import Memory, Action, Source, Status
from .policy import WritePolicy


class MemoryStore(Protocol):
    """Interface so a different backend (e.g. whatever the Substrate workshop uses)
    can be dropped in as an adapter without touching attribution or rollback."""
    def write(self, content: str, source: Source, tags: Iterable[str],
              derived_from: Iterable[str] = (), independent_support: Iterable[str] = ()) -> Memory: ...
    def get(self, mid: str) -> Memory: ...
    def all(self) -> list[Memory]: ...
    def active(self) -> list[Memory]: ...
    def set_status(self, mid: str, status: Status) -> None: ...
    def log_action(self, task_id: str, tool: str, args: dict, used: list[str]) -> Action: ...


class InMemoryStore:
    def __init__(self, policy: WritePolicy | None = None):
        self.policy = policy or WritePolicy()
        self._mem: dict[str, Memory] = {}
        self.actions: list[Action] = []
        self._clock = 0

    def _tick(self) -> int:
        self._clock += 1
        return self._clock

    def write(self, content, source, tags, derived_from=(), independent_support=(), mid=None):
        parents = [self._mem[p] for p in derived_from]
        status, trust = self.policy.decide(source, parents)
        mid = mid or f"m{len(self._mem) + 1:02d}"
        m = Memory(mid, content, source, set(tags), trust, self._tick(), status,
                   list(derived_from), list(independent_support))
        self._mem[mid] = m
        return m

    def get(self, mid): return self._mem[mid]
    def all(self): return list(self._mem.values())
    def active(self): return [m for m in self._mem.values() if m.status == Status.ACTIVE]
    def set_status(self, mid, status): self._mem[mid].status = status

    def children(self, mid: str) -> list[Memory]:
        return [m for m in self._mem.values() if mid in m.derived_from]

    def log_action(self, task_id, tool, args, used):
        a = Action(f"a{len(self.actions) + 1:02d}", task_id, tool, args, used, self._tick())
        self.actions.append(a)
        return a

    def snapshot(self) -> "InMemoryStore":
        return copy.deepcopy(self)
