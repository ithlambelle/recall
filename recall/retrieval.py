from __future__ import annotations
from .models import Memory


def retrieve(store, tags: set[str], k: int = 6, exclude: set[str] = frozenset()) -> list[Memory]:
    """Tag-overlap retrieval, ties broken by recency. Deliberately simple and deterministic
    so attribution results are reproducible; swap in embeddings later if needed.
    `exclude` simulates the memory not existing: the next-best memory fills its slot."""
    scored = [(len(m.tags & tags), m.created_at, m) for m in store.active()
              if m.id not in exclude and m.tags & tags]
    scored.sort(key=lambda t: (t[0], t[1]), reverse=True)
    return [m for _, _, m in scored[:k]]
