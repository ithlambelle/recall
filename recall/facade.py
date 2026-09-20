"""17x9 renderer for the MIT Green Building facade (one window per memory).
Frame format per Sundai Hack 140 starter repos: [[[r,g,b] x 9] x 17], row-major, row 0 top.
Confirm the endpoint and FPS limits at the event. Cap at ~12 FPS."""
from __future__ import annotations
import time
from .models import Status

ROWS, COLS = 17, 9
OFF = [0, 0, 0]


def color(m, flagged: set[str]):
    if m.id in flagged:
        return [255, 30, 30]
    if m.status == Status.DEACTIVATED:
        return [25, 25, 25]
    if m.status == Status.QUARANTINED:
        return [40, 90, 255]
    return [40, 220, 80] if m.trust >= 0.5 else [255, 170, 0]


def frame(store, flagged: set[str] = frozenset()):
    grid = [[OFF[:] for _ in range(COLS)] for _ in range(ROWS)]
    for i, m in enumerate(sorted(store.all(), key=lambda m: m.created_at)[: ROWS * COLS]):
        grid[i // COLS][i % COLS] = color(m, flagged)
    return grid


def preview(store, flagged: set[str] = frozenset()) -> str:
    ch = {(255, 30, 30): "X", (25, 25, 25): ".", (40, 90, 255): "Q", (40, 220, 80): "o", (255, 170, 0): "~"}
    rows = frame(store, flagged)
    used = (len(store.all()) + COLS - 1) // COLS
    return "\n".join(" ".join(ch.get(tuple(c), " ") for c in r) for r in rows[:max(used, 1)])


def post(grid, url: str, last=[0.0], min_interval: float = 1 / 12):
    import requests
    wait = min_interval - (time.time() - last[0])
    if wait > 0:
        time.sleep(wait)
    requests.post(url, json=grid, timeout=2)
    last[0] = time.time()
