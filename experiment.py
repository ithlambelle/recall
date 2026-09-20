"""Compare repair strategies after poisoning: delete-source-only, full reset, Recall.
Metrics: task recovery, benign memories preserved, poison remaining, repair LLM calls."""
import argparse
from recall import env
from recall.models import Status, Source
from recall.agents import RuleAgent
from recall.outcomes import Outcome
from recall.runtime import run, run_task, is_harmful, is_correct
from recall.attribution import diagnose
from recall.rollback import rollback
import scenario


def make_agent(kind):
    if kind == "claude":
        env.load()
        from recall.agents import ClaudeAgent
        return ClaudeAgent()
    return RuleAgent()


def evaluate(st, agent, tasks):
    runs = [run(st, agent, t, record=False) for t in tasks.values()]
    res = [r.decision for r in runs]
    tl = list(tasks.values())
    counts = {}
    for r in runs:
        counts[r.outcome.value] = counts.get(r.outcome.value, 0) + 1
    active = {m.id for m in st.active()}
    benign = {m.id for m in st.all()} - scenario.POISON_IDS
    return {
        "recovered": sum(is_correct(r, t) for r, t in zip(res, tl)),
        "harmful": sum(is_harmful(r, t) for r, t in zip(res, tl)),
        "benign_kept": len(benign & active), "benign_total": len(benign),
        "poison_left": len(scenario.POISON_IDS & active),
        "outcomes": counts,
    }


def strategy_delete_source(st, agent, tasks):
    for m in st.all():
        if m.source == Source.WEB:  # what a content scanner would flag
            st.set_status(m.id, Status.DEACTIVATED)
    return 0


def strategy_reset(st, agent, tasks):
    for m in st.all():
        st.set_status(m.id, Status.DEACTIVATED)
    return 0


def strategy_recall(st, agent, tasks, prior=True, verbose=False):
    calls, diagnosed = 0, set()
    for t in tasks.values():
        d = diagnose(st, agent, t, use_provenance_prior=prior)  # batch: memory frozen during audit
        calls += d.calls
        diagnosed |= set(d.repair_set)
        if verbose and d.harmful:
            print(f"  {t['id']}: LOO={d.loo} -> repair set {d.repair_set} via {d.method} ({d.calls} calls)")
    rep = rollback(st, agent, diagnosed, tasks)
    if verbose:
        print(f"  deactivated {rep.deactivated}, preserved {rep.preserved}, "
              f"replayed {len(rep.replayed)} actions ({rep.calls} calls)")
    return calls + rep.calls


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--agent", default="rule", choices=["rule", "claude"])
    args = ap.parse_args()

    strategies = {"delete source only": strategy_delete_source, "full reset": strategy_reset,
                  "Recall (prior)": lambda s, a, t: strategy_recall(s, a, t, True),
                  "Recall (no prior)": lambda s, a, t: strategy_recall(s, a, t, False)}
    print(f"{'strategy':<20}{'recovered':>11}{'harmful':>9}{'benign kept':>13}"
          f"{'poison left':>13}{'repair calls':>14}   outcomes")
    for name, fn in strategies.items():
        st, agent = scenario.build(), make_agent(args.agent)
        for t in scenario.TASKS.values():
            run_task(st, agent, t)  # the poisoned run that produced harmful actions
        calls = fn(st, agent, scenario.TASKS)
        r = evaluate(st, agent, scenario.TASKS)
        n = len(scenario.TASKS)
        oc = " ".join(f"{k}={v}" for k, v in sorted(r["outcomes"].items()))
        print(f"{name:<20}{r['recovered']:>8}/{n}{r['harmful']:>9}"
              f"{r['benign_kept']:>9}/{r['benign_total']}{r['poison_left']:>13}{calls:>14}   {oc}")


if __name__ == "__main__":
    main()
