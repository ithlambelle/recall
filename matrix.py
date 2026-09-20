"""Repeat the full pipeline across models and report variance.

Real models are not reproducible (sampling parameters were removed from the API),
so a single run is an anecdote. This runs N repeats per model and reports the
spread, which is what any quoted number should be based on.

Results are written after every run, so an interruption never costs a re-run.

    python3 matrix.py --models claude-haiku-4-5 claude-sonnet-5 --repeats 3
"""
from __future__ import annotations

import argparse
import json
import pathlib
import time

from recall import env
from recall.pipeline import run_pipeline

OUT = pathlib.Path("matrix_results.json")


def load() -> list[dict]:
    return json.loads(OUT.read_text()) if OUT.exists() else []


def summarise(rows: list[dict]) -> None:
    by_model: dict[str, list[dict]] = {}
    for r in rows:
        if r.get("ok"):
            by_model.setdefault(r["model"], []).append(r)

    print(f"\n{'model':<22}{'runs':>5}{'recovered':>11}{'benign kept':>13}"
          f"{'poison left':>13}{'parse err':>11}{'cost':>9}")
    print("-" * 84)
    total = 0.0
    for model, rs in by_model.items():
        rec = [x["recovered"] for x in rs]
        ben = [x["benign_kept"] for x in rs]
        poi = [x["poison_left"] for x in rs]
        pe = [x["parse_errors"] for x in rs]
        cost = sum(x["cost_usd"] for x in rs)
        total += cost
        rng = lambda v: f"{min(v)}" if min(v) == max(v) else f"{min(v)}-{max(v)}"
        print(f"{model:<22}{len(rs):>5}{rng(rec) + '/4':>11}{rng(ben) + '/14':>13}"
              f"{rng(poi):>13}{sum(pe):>11}{'$' + format(cost, '.3f'):>9}")
    print("-" * 84)
    print(f"{'total':<22}{len(rows):>5}{'':>48}{'$' + format(total, '.3f'):>9}")

    print("\ninitial failure mode (how each model breaks before repair):")
    for model, rs in by_model.items():
        modes: dict[str, int] = {}
        for x in rs:
            for k, v in x["initial_outcomes"].items():
                modes[k] = modes.get(k, 0) + v
        print(f"  {model:<22}{modes}")

    print("\nrepair set found (must be m14+m15 every time):")
    for model, rs in by_model.items():
        sets = {",".join(x["diagnosed"]) or "(none)" for x in rs}
        flag = "" if sets == {"m14,m15"} else "   <-- INCONSISTENT"
        print(f"  {model:<22}{sorted(sets)}{flag}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="+",
                    default=["claude-haiku-4-5", "claude-sonnet-5", "claude-opus-5"])
    ap.add_argument("--repeats", type=int, default=3)
    ap.add_argument("--summarise-only", action="store_true")
    args = ap.parse_args()

    if args.summarise_only:
        summarise(load())
        return

    env.load()
    from recall.agents import ClaudeAgent

    rows = load()
    done = {(r["model"], r["repeat"]) for r in rows if r.get("ok")}

    for model in args.models:
        for i in range(args.repeats):
            if (model, i) in done:
                print(f"skip {model} #{i} (already recorded)")
                continue
            t0 = time.time()
            print(f"running {model} #{i} ...", flush=True)
            try:
                agent = ClaudeAgent(model)
                trace = run_pipeline(agent)
                s = trace["summary"]
                diag = next(x for x in trace["steps"] if x["kind"] == "diagnose")
                init = next(x for x in trace["steps"] if x["kind"] == "run")
                rows.append({
                    "ok": True, "model": model, "repeat": i,
                    "recovered": s["recovered"], "benign_kept": s["benign_kept"],
                    "poison_left": s["poison_left"], "repair_calls": s["repair_calls"],
                    "final_outcomes": s["outcome_counts"],
                    "initial_outcomes": init["outcome_counts"],
                    "diagnosed": diag["diagnosed"],
                    "loo_insufficient": diag["loo_insufficient"],
                    "parse_errors": s["usage"]["parse_errors"],
                    "cost_usd": s["usage"]["cost_usd"],
                    "seconds": round(time.time() - t0, 1),
                })
                r = rows[-1]
                print(f"  -> {r['recovered']}/4 correct, benign {r['benign_kept']}/14, "
                      f"poison {r['poison_left']}, diagnosed {r['diagnosed']}, "
                      f"{r['parse_errors']} parse err, ${r['cost_usd']:.4f}, {r['seconds']}s")
            except Exception as e:  # keep going; a failed run must not lose the rest
                rows.append({"ok": False, "model": model, "repeat": i, "error": repr(e)[:300]})
                print(f"  !! failed: {e!r}")
            OUT.write_text(json.dumps(rows, indent=2))  # save after every run

    summarise(rows)


if __name__ == "__main__":
    main()
