"""Record real model runs as fixed traces the demo replays without an API key.

One file per model per run: traces/claude-<model>-<run>.json. Run 1 of each model
was recorded earlier and is kept, so only the missing runs are paid for again.

    python3 record_traces.py            # fill in whatever is missing
    python3 record_traces.py --force    # re-record everything
"""
from __future__ import annotations

import argparse
import json
import pathlib

from recall import env
from recall.pipeline import run_pipeline

TRACES = pathlib.Path("traces")
MODELS = {"haiku": "claude-haiku-4-5", "sonnet": "claude-sonnet-5", "opus": "claude-opus-5"}
RUNS = (1, 2, 3)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="*", default=list(MODELS))
    ap.add_argument("--runs", nargs="*", type=int, default=list(RUNS))
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    env.load()
    from recall.agents import ClaudeAgent
    TRACES.mkdir(exist_ok=True)
    total = 0.0
    for key in args.models:
        for n in args.runs:
            out = TRACES / f"claude-{key}-{n}.json"
            if out.exists() and not args.force:
                print(f"keep {out.name} (already recorded)")
                continue
            print(f"recording {MODELS[key]} run {n} ...", flush=True)
            trace = run_pipeline(ClaudeAgent(MODELS[key]))
            out.write_text(json.dumps(trace))
            s, u = trace["summary"], trace["summary"]["usage"]
            init = next(x for x in trace["steps"] if x["kind"] == "run")["outcome_counts"]
            diag = next(x for x in trace["steps"] if x["kind"] == "diagnose")["diagnosed"]
            total += u["cost_usd"]
            print(f"  {s['recovered']}/{s['tasks']} correct, benign {s['benign_kept']}/"
                  f"{s['benign_total']}, found {diag}, before {init}, ${u['cost_usd']:.4f}")
    print(f"\nnewly recorded: ${total:.4f}")


if __name__ == "__main__":
    main()
