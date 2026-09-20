"""Orchestration: runs the full narrative once and emits a JSON trace.

This is deliberately a thin layer over `runtime`, `attribution` and `rollback`.
It adds no logic of its own, so the API, the terminal demo and the test suite all
observe exactly the same pipeline.
"""
from __future__ import annotations

import scenario
from .attribution import diagnose
from .rollback import rollback
from .runtime import run_task, is_harmful, is_correct
from .serialize import memory_dict, action_dict, store_dict


def _decision_dict(d: dict) -> dict:
    return {"tool": d["tool"], "args": d["args"], "recipient": d["args"].get("recipient")}


def run_pipeline(agent, policy_mode: str = "permissive", use_provenance_prior: bool = True) -> dict:
    """Poison -> harmful run -> counterfactual diagnosis -> rollback -> replay.

    Returns a JSON-serializable trace. `agent` is supplied by the caller so the
    same pipeline runs offline (RuleAgent) or against a real model (ClaudeAgent).
    """
    store = scenario.build(policy_mode)
    tasks = scenario.TASKS
    steps: list[dict] = []

    steps.append({
        "kind": "initial",
        "title": "Memory after the agent read a spoofed vendor page",
        "policy": policy_mode,
        "memories": [memory_dict(m) for m in sorted(store.all(), key=lambda m: m.created_at)],
    })

    # 1. The agent runs this week's payables with memory as it stands.
    runs = []
    for t in tasks.values():
        d = run_task(store, agent, t)
        runs.append({
            "task_id": t["id"],
            "supplier": t["supplier"],
            "amount": t["amount"],
            "prompt": t["prompt"],
            "expected": t["expected"],
            "decision": _decision_dict(d),
            "harmful": is_harmful(d, t),
            "correct": is_correct(d, t),
            "used_memories": list(store.actions[-1].used_memories),
            "action_id": store.actions[-1].id,
        })
    steps.append({
        "kind": "run",
        "title": "Agent executes the payables queue",
        "runs": runs,
        "harmful_count": sum(r["harmful"] for r in runs),
    })

    # 2. Counterfactual diagnosis on every task, harmful or not.
    diagnosed: set[str] = set()
    diagnoses = []
    audit_calls = 0
    for t in tasks.values():
        dg = diagnose(store, agent, t, use_provenance_prior=use_provenance_prior)
        audit_calls += dg.calls
        diagnosed |= set(dg.repair_set)
        diagnoses.append({
            "task_id": dg.task_id,
            "harmful": dg.harmful,
            "loo": dg.loo,
            "single_cause_found": any(dg.loo.values()),
            "method": dg.method,
            "repair_set": list(dg.repair_set),
            "calls": dg.calls,
        })
    steps.append({
        "kind": "diagnose",
        "title": "Counterfactual attribution",
        "diagnoses": diagnoses,
        "diagnosed": sorted(diagnosed),
        "calls": audit_calls,
        # The headline: leave-one-out alone explains nothing here, because the
        # poisoned record and the profile derived from it reinforce each other.
        "loo_insufficient": any(d["harmful"] and not d["single_cause_found"] for d in diagnoses),
    })

    # 3. Dependency-guided rollback + selective replay.
    rollback_step: dict = {
        "kind": "rollback",
        "title": "Dependency-guided rollback",
        "diagnosed": sorted(diagnosed),
        "deactivated": [],
        "preserved": [],
        "replayed": [],
        "calls": 0,
    }
    if diagnosed:
        rep = rollback(store, agent, diagnosed, tasks)
        rollback_step.update({
            "deactivated": rep.deactivated,
            "preserved": rep.preserved,
            "calls": rep.calls,
            "replayed": [
                {
                    "old_action": old,
                    "task_id": tid,
                    "decision": _decision_dict(new),
                    "repaired": is_correct(new, tasks[tid]),
                    "still_harmful": is_harmful(new, tasks[tid]),
                }
                for old, tid, new in rep.replayed
            ],
        })
    steps.append(rollback_step)

    # 4. Final state, re-evaluated from scratch.
    final = [run_task(store, agent, t, record=False) for t in tasks.values()]
    tl = list(tasks.values())
    active = {m.id for m in store.active()}
    benign = {m.id for m in store.all()} - scenario.POISON_IDS
    summary = {
        "recovered": sum(is_correct(r, t) for r, t in zip(final, tl)),
        "tasks": len(tl),
        "harmful": sum(is_harmful(r, t) for r, t in zip(final, tl)),
        "benign_kept": len(benign & active),
        "benign_total": len(benign),
        "poison_left": len(scenario.POISON_IDS & active),
        "repair_calls": audit_calls + rollback_step["calls"],
        "agent_calls_total": agent.calls,
    }
    steps.append({
        "kind": "final",
        "title": "Memory after repair",
        "memories": [memory_dict(m) for m in sorted(store.all(), key=lambda m: m.created_at)],
        "summary": summary,
    })

    return {
        "policy": policy_mode,
        "use_provenance_prior": use_provenance_prior,
        "agent": type(agent).__name__,
        "steps": steps,
        "summary": summary,
        "store": store_dict(store),
        # Evaluation-only ground truth, sent for UI annotation. The pipeline itself
        # never reads it: diagnosis rediscovers the poison behaviourally.
        "ground_truth_poison": sorted(scenario.POISON_IDS),
    }
