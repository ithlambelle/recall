from __future__ import annotations
from .models import Source, Status, BASE_TRUST, Memory


class WritePolicy:
    """Decides trust by *where a write came from*, not by what it says.

    Derived memories inherit the minimum trust of their parents (taint propagation),
    so an agent summarizing a poisoned record cannot launder it into a trusted one.

    mode="permissive" stores everything as ACTIVE (how most memory systems behave today).
    mode="enforce" quarantines writes below `threshold`.
    """

    def __init__(self, mode: str = "permissive", threshold: float = 0.5):
        self.mode, self.threshold = mode, threshold

    def trust_for(self, source: Source, parents: list[Memory]) -> float:
        if source == Source.DERIVED:
            return min((p.trust for p in parents), default=0.0)
        return BASE_TRUST[source]

    def decide(self, source: Source, parents: list[Memory]) -> tuple[Status, float]:
        trust = self.trust_for(source, parents)
        if self.mode == "enforce" and trust < self.threshold:
            return Status.QUARANTINED, trust
        return Status.ACTIVE, trust
