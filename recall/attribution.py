"""Counterfactual memory attribution (in the spirit of MemAudit, arXiv:2605.23723,
and the LOO baselines in TracLLM, arXiv:2506.04202).

Influence is binary and behavioral: does removing a memory flip the agent from a
harmful action to a non-harmful one? Removal re-runs retrieval, so the next memory
fills the vacated slot, as it would in a real store.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from .outcomes import Outcome
from .retrieval import retrieve
from .runtime import run, K


@dataclass
class Diagnosis:
    task_id: str
    harmful: bool          # a repairable failure occurred
    outcome: str = ""      # the specific Outcome that triggered diagnosis
    loo: dict[str, int] = field(default_factory=dict)   # memory id -> 1 if removal alone repairs
    repair_set: list[str] = field(default_factory=list)
    method: str = ""
    calls: int = 0


def _fails_without(store, agent, task, removed) -> bool:
    """Does the task still fail with `removed` excluded from retrieval?"""
    return run(store, agent, task, exclude=set(removed), record=False).failed


def diagnose(store, agent, task, use_provenance_prior: bool = True) -> Diagnosis:
    start = agent.calls
    base = run(store, agent, task, record=False)
    d = Diagnosis(task["id"], base.failed, base.outcome.value)
    if not d.harmful:
        d.calls = agent.calls - start
        return d

    retrieved = retrieve(store, task["tags"], k=K)

    # 1) Leave-one-out.
    for m in retrieved:
        d.loo[m.id] = 0 if _fails_without(store, agent, task, [m.id]) else 1
    singles = [m for m in retrieved if d.loo[m.id]]
    if singles:
        d.repair_set = [min(singles, key=lambda m: m.trust).id]
        d.method = "leave-one-out"
        d.calls = agent.calls - start
        return d

    # 2) LOO found nothing: memories are reinforcing each other (e.g. a poisoned record
    #    plus a summary derived from it). Greedy cumulative removal, then prune to minimal.
    order = sorted(retrieved, key=lambda m: m.trust) if use_provenance_prior else list(retrieved)
    removed: list[str] = []
    for m in order:
        removed.append(m.id)
        if not _fails_without(store, agent, task, removed):
            break
    else:
        d.method = "unrepairable within retrieved set"
        d.calls = agent.calls - start
        return d
    for mid in list(reversed(removed)):
        trial = [r for r in removed if r != mid]
        if not _fails_without(store, agent, task, trial):
            removed = trial
    d.repair_set = removed
    d.method = "greedy + prune (" + ("provenance prior" if use_provenance_prior else "retrieval order") + ")"
    d.calls = agent.calls - start
    return d
