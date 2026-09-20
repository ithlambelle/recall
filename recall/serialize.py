"""JSON projections of the domain objects. Pure read-only views: nothing here
changes behaviour, so the API and the terminal demo observe the same pipeline."""
from __future__ import annotations
from .models import Memory, Action


def memory_dict(m: Memory) -> dict:
    return {
        "id": m.id,
        "content": m.content,
        "source": m.source.value,
        "trust": m.trust,
        "status": m.status.value,
        "tags": sorted(m.tags),
        "created_at": m.created_at,
        "derived_from": list(m.derived_from),
        "independent_support": list(m.independent_support),
    }


def action_dict(a: Action) -> dict:
    return {
        "id": a.id,
        "task_id": a.task_id,
        "tool": a.tool,
        "args": a.args,
        "used_memories": list(a.used_memories),
        "created_at": a.created_at,
        "superseded_by": a.superseded_by,
    }


def store_dict(store) -> dict:
    return {
        "memories": [memory_dict(m) for m in sorted(store.all(), key=lambda m: m.created_at)],
        "actions": [action_dict(a) for a in store.actions],
    }
