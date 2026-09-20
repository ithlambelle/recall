"""Dependency-guided rollback (in the spirit of arXiv:2608.10502).

Deleting only the diagnosed memory leaves derived memories and past actions that
depend on it. We deactivate the diagnosed set plus its descendants in the
derived-from graph, preserve descendants with independent trusted support, and
replay only the actions that consumed deactivated memories.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from .models import Status
from .runtime import run


@dataclass
class RollbackReport:
    diagnosed: list[str]
    deactivated: list[str] = field(default_factory=list)
    preserved: list[str] = field(default_factory=list)
    replayed: list[tuple[str, str, object]] = field(default_factory=list)  # (old action, task, TaskRun)
    calls: int = 0


def descendants(store, roots: set[str]) -> set[str]:
    seen, stack = set(), list(roots)
    while stack:
        for c in store.children(stack.pop()):
            if c.id not in seen:
                seen.add(c.id)
                stack.append(c.id)
    return seen - roots


def rollback(store, agent, diagnosed: set[str], tasks: dict[str, dict], trust_floor: float = 0.5):
    rep = RollbackReport(sorted(diagnosed))
    affected = diagnosed | descendants(store, diagnosed)
    for mid in sorted(affected):
        m = store.get(mid)
        support = [s for s in m.independent_support
                   if s not in affected and store.get(s).trust >= trust_floor]
        if mid not in diagnosed and support:
            rep.preserved.append(mid)
        else:
            store.set_status(mid, Status.DEACTIVATED)
            rep.deactivated.append(mid)

    dead = set(rep.deactivated)
    start = agent.calls
    for a in list(store.actions):
        if a.superseded_by is None and dead & set(a.used_memories):
            new = run(store, agent, tasks[a.task_id])
            a.superseded_by = new.action_id
            rep.replayed.append((a.id, a.task_id, new))
    rep.calls = agent.calls - start
    return rep
