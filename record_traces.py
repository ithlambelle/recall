"""Record real model runs as fixed traces the demo can replay without an API key.

Each trace is a genuine pipeline run, kept verbatim. Re-run this only when the
scenario or pipeline changes; the demo should otherwise replay what is committed.
"""
import json, pathlib, sys
from recall import env
from recall.pipeline import run_pipeline

TRACES = pathlib.Path("traces")
MODELS = {"haiku": "claude-haiku-4-5", "sonnet": "claude-sonnet-5", "opus": "claude-opus-5"}


def main():
    env.load()
    from recall.agents import ClaudeAgent
    TRACES.mkdir(exist_ok=True)
    wanted = sys.argv[1:] or list(MODELS)
    total = 0.0
    for key in wanted:
        model = MODELS[key]
        print(f"recording {model} ...", flush=True)
        agent = ClaudeAgent(model)
        trace = run_pipeline(agent)
        (TRACES / f"claude-{key}.json").write_text(json.dumps(trace))
        u, s = trace["summary"]["usage"], trace["summary"]
        init = next(x for x in trace["steps"] if x["kind"] == "run")["outcome_counts"]
        diag = next(x for x in trace["steps"] if x["kind"] == "diagnose")["diagnosed"]
        total += u["cost_usd"]
        print(f"  {s['recovered']}/{s['tasks']} correct · benign {s['benign_kept']}/{s['benign_total']}"
              f" · diagnosed {diag} · before: {init} · ${u['cost_usd']:.4f}")
    print(f"\ntotal ${total:.4f}")


if __name__ == "__main__":
    main()
