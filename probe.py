"""Cheapest possible check: does the poison actually land on a real model?

One API call per task. Use this to tune the scenario before spending a full
pipeline run (~34 calls). Prints exact token spend.

    python3 probe.py --model claude-haiku-4-5
    python3 probe.py --model claude-sonnet-5 --tasks t1 t3
"""
import argparse

from recall import env
from recall.retrieval import retrieve
from recall.runtime import run_task, is_harmful, is_correct, K
import scenario


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=None, help="override RECALL_MODEL")
    ap.add_argument("--policy", default="permissive", choices=["permissive", "enforce"])
    ap.add_argument("--tasks", nargs="*", default=["t1"], help="task ids (default: t1 only)")
    ap.add_argument("--show-memories", action="store_true")
    args = ap.parse_args()

    env.load()
    from recall.agents import ClaudeAgent
    agent = ClaudeAgent(args.model)
    st = scenario.build(args.policy)

    print(f"model: {agent.model}   policy: {args.policy}   tasks: {' '.join(args.tasks)}")
    if args.show_memories:
        for t in args.tasks:
            print(f"\nretrieved for {t}:")
            for m in retrieve(st, scenario.TASKS[t]["tags"], k=K):
                print(f"  [{m.id}] ({m.source.value}, trust {m.trust}) {m.content}")

    print()
    for tid in args.tasks:
        t = scenario.TASKS[tid]
        d = run_task(st, agent, t, record=False)
        got = d["args"].get("recipient", d["args"])
        if is_harmful(d, t):
            verdict = "ATTACK LANDED"
        elif is_correct(d, t):
            verdict = "resisted (paid correctly)"
        else:
            verdict = f"escaped via {d['tool']}"
        print(f"  {tid} {t['supplier']:<10} -> {d['tool']:<13} {got}")
        print(f"     expected {t['expected']}  ==>  {verdict}")

    u = agent.usage()
    print(f"\n{u['calls']} calls · {u['input_tokens']} in / {u['output_tokens']} out "
          f"· ${u['cost_usd']:.5f}")


if __name__ == "__main__":
    main()
