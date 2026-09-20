"""90-second demo narrative in the terminal."""
import argparse
from recall.facade import preview
from recall.runtime import run, run_task, is_harmful
from recall.attribution import diagnose
from recall.rollback import rollback
from experiment import make_agent
import scenario


def show(title, st, flagged=frozenset()):
    print(f"\n{title}   (o trusted  ~ low-trust  X flagged  . rolled back  Q quarantined)")
    print(preview(st, set(flagged)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--agent", default="rule", choices=["rule", "claude"])
    ap.add_argument("--policy", default="permissive", choices=["permissive", "enforce"])
    ap.add_argument("--jev", action="store_true", help="use Jev to prioritize counterfactual tests")
    args = ap.parse_args()
    st, agent, tasks = scenario.build(args.policy), make_agent(args.agent), scenario.TASKS
    triage = None
    if args.jev:
        from recall import env
        env.load()
        from recall.jev import JevTriage
        triage = JevTriage()

    show("1. Memory store after the agent read a spoofed vendor page", st)
    print("\n2. Agent runs this week's payables:")
    for t in tasks.values():
        r = run(st, agent, t)
        d = r.decision
        print(f"  {t['id']} {t['supplier']:<10} -> {d['tool']:<13} "
              f"{d['args'].get('recipient', '')}  [{r.outcome.value}]")

    print("\n3. Recall diagnoses harmful actions (counterfactual reruns):")
    diagnosed = set()
    for t in tasks.values():
        dg = diagnose(st, agent, t, triage=triage)
        if dg.harmful:
            print(f"  {t['id']}: leave-one-out {dg.loo}")
            print(f"      no single memory is causal -> {dg.method}: {dg.repair_set}" if not any(dg.loo.values())
                  else f"      causal memory: {dg.repair_set}")
            diagnosed |= set(dg.repair_set)
            if dg.triage:
                ranked = ", ".join(f"{x['memory_id']}={x['suspicious_probability']:.2f}"
                                   for x in dg.triage)
                print(f"      Jev priority: {ranked}")
            if dg.triage_error:
                print(f"      Jev unavailable; used provenance fallback ({dg.triage_error})")
    show("   Diagnosed memories", st, diagnosed)
    for mid in sorted(diagnosed):
        print(f"   {mid} [{st.get(mid).source.value}, trust {st.get(mid).trust}]: {st.get(mid).content}")

    if not diagnosed:
        print("  no harmful actions -- nothing to repair")
        return
    print("\n4. Dependency-guided rollback:")
    rep = rollback(st, agent, diagnosed, tasks)
    print(f"  deactivated {rep.deactivated}  (includes descendants never retrieved by any task)")
    print(f"  preserved   {rep.preserved}  (independent trusted support)")
    for old, tid, new in rep.replayed:
        print(f"  replayed {old} ({tid}) -> {new.decision['tool']} "
              f"{new.decision['args'].get('recipient')}  [{new.outcome.value}]")
    untouched = len(st.actions) - len(rep.replayed) * 2
    print(f"  {len(st.active())} memories still active; replayed {len(rep.replayed)} actions "
          f"({rep.calls} calls), {untouched} actions left untouched")
    show("5. Memory store after repair", st)
    if triage:
        print(f"\nJev: {triage.calls} batched calls, {len(triage.failures)} failures")


if __name__ == "__main__":
    main()
