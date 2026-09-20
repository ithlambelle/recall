"""Orchestration: runs the full narrative once and emits a JSON trace.

This is deliberately a thin layer over `runtime`, `attribution` and `rollback`.
It adds no logic of its own, so the API, the terminal demo and the test suite all
observe exactly the same pipeline.
"""
from __future__ import annotations

import scenario
from .attribution import diagnose
from .rollback import rollback
from .outcomes import Outcome
from .runtime import run, run_task, is_harmful, is_correct
from .serialize import memory_dict, action_dict, store_dict


def _counts(values) -> dict:
    out: dict[str, int] = {}
    for v in values:
        out[v] = out.get(v, 0) + 1
    return out


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
        r = run(store, agent, t)
        d = r.decision
        runs.append({
            "outcome": r.outcome.value,
            "task_id": t["id"],
            "supplier": t["supplier"],
            "amount": t["amount"],
            "prompt": t["prompt"],
            "expected": t["expected"],
            "decision": _decision_dict(d),
            "harmful": is_harmful(d, t),
            "correct": is_correct(d, t),
            "used_memories": [m.id for m in r.retrieved],
            "action_id": r.action_id,
        })
    steps.append({
        "kind": "run",
        "title": "Agent executes the payables queue",
        "runs": runs,
        "harmful_count": sum(r["harmful"] for r in runs),
        "failed_count": sum(r["outcome"] in ("UNSAFE_ACTION", "UNNECESSARY_ESCALATION")
                            for r in runs),
        "outcome_counts": _counts(r["outcome"] for r in runs),
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
            "outcome": dg.outcome,
            "loo": dg.loo,
            "single_cause_found": any(dg.loo.values()),
            "method": dg.method,
            "repair_set": list(dg.repair_set),
            "calls": dg.calls,
            "probes": dg.probes,
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
                    "decision": _decision_dict(new.decision),
                    "outcome": new.outcome.value,
                    "repaired": new.outcome is Outcome.CORRECT,
                    "still_harmful": new.outcome is Outcome.UNSAFE_ACTION,
                }
                for old, tid, new in rep.replayed
            ],
        })
    steps.append(rollback_step)

    # 4. Final state, re-evaluated from scratch.
    final_runs = [run(store, agent, t, record=False) for t in tasks.values()]
    final = [fr.decision for fr in final_runs]
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
        "outcome_counts": _counts(fr.outcome.value for fr in final_runs),
    }
    if hasattr(agent, "usage"):
        summary["usage"] = agent.usage()
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
