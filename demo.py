"""90-second demo narrative in the terminal."""
import argparse
from recall.facade import preview
from recall.runtime import run_task, is_harmful
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
    args = ap.parse_args()
    st, agent, tasks = scenario.build(args.policy), make_agent(args.agent), scenario.TASKS

    show("1. Memory store after the agent read a spoofed vendor page", st)
    print("\n2. Agent runs this week's payables:")
    for t in tasks.values():
        d = run_task(st, agent, t)
        flag = "  <-- HARMFUL" if is_harmful(d, t) else ""
        print(f"  {t['id']} {t['supplier']:<10} -> {d['tool']} {d['args'].get('recipient', d['args'])}{flag}")

    print("\n3. Recall diagnoses harmful actions (counterfactual reruns):")
    diagnosed = set()
    for t in tasks.values():
        dg = diagnose(st, agent, t)
        if dg.harmful:
            print(f"  {t['id']}: leave-one-out {dg.loo}")
            print(f"      no single memory is causal -> {dg.method}: {dg.repair_set}" if not any(dg.loo.values())
                  else f"      causal memory: {dg.repair_set}")
            diagnosed |= set(dg.repair_set)
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
        ok = "OK" if not is_harmful(new, tasks[tid]) else "STILL HARMFUL"
        print(f"  replayed {old} ({tid}) -> {new['tool']} {new['args'].get('recipient')}  {ok}")
    untouched = len(st.actions) - len(rep.replayed) * 2
    print(f"  {len(st.active())} memories still active; replayed {len(rep.replayed)} actions "
          f"({rep.calls} calls), {untouched} actions left untouched")
    show("5. Memory store after repair", st)


if __name__ == "__main__":
    main()
