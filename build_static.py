"""Build a static copy of the demo into docs/ for GitHub Pages.

The page works either way: against the live API when one is present, and against
these precomputed traces when it is not. The offline agent is deterministic, so
its recorded trace is identical to running it live. The Claude trace is a real
recorded run, committed rather than generated here so that publishing the site
never spends money.
"""
from __future__ import annotations

import json
import pathlib
import shutil

from recall.agents import RuleAgent
from recall.pipeline import run_pipeline

ROOT = pathlib.Path(__file__).parent
DOCS = ROOT / "docs"
TRACES = DOCS / "traces"


def main() -> None:
    TRACES.mkdir(parents=True, exist_ok=True)
    shutil.copy(ROOT / "static" / "index.html", DOCS / "index.html")
    (DOCS / ".nojekyll").write_text("")  # keep Pages from mangling the tree

    for policy in ("permissive", "enforce"):
        trace = run_pipeline(RuleAgent(), policy)
        out = TRACES / f"rule-{policy}.json"
        out.write_text(json.dumps(trace))
        print(f"{out.relative_to(ROOT)}  {out.stat().st_size:,} bytes  "
              f"recovered {trace['summary']['recovered']}/{trace['summary']['tasks']}")

    # Recorded real-model runs, committed verbatim so publishing never spends money.
    recorded = sorted((ROOT / "traces").glob("claude-*.json"))
    if not recorded:
        print("WARNING: no recorded model traces; the Claude options will have no data")
    for src in recorded:
        shutil.copy(src, TRACES / src.name)
        t = json.loads(src.read_text())
        before = next(x for x in t["steps"] if x["kind"] == "run")["outcome_counts"]
        print(f"traces/{src.name}  {t['summary']['usage']['model']}  "
              f"recovered {t['summary']['recovered']}/{t['summary']['tasks']}  before={before}")

    # The matrix is derived from the recorded traces, so the table and the graphs
    # are always describing the same runs rather than two separate sets.
    rows = []
    for src in sorted((ROOT / "traces").glob("claude-*-[0-9].json")):
        t = json.loads(src.read_text())
        key, run = src.stem.rsplit("-", 1)
        summ = t["summary"]
        diag = next(x for x in t["steps"] if x["kind"] == "diagnose")
        init = next(x for x in t["steps"] if x["kind"] == "run")
        rows.append({
            "ok": True, "model": summ["usage"]["model"], "run": int(run),
            "trace": src.stem,
            "recovered": summ["recovered"], "tasks": summ["tasks"],
            "benign_kept": summ["benign_kept"], "benign_total": summ["benign_total"],
            "poison_left": summ["poison_left"], "repair_calls": summ["repair_calls"],
            "diagnosed": diag["diagnosed"], "initial_outcomes": init["outcome_counts"],
            "parse_errors": summ["usage"]["parse_errors"], "cost_usd": summ["usage"]["cost_usd"],
        })
    order = {"claude-haiku-4-5": 0, "claude-sonnet-5": 1, "claude-opus-5": 2}
    rows.sort(key=lambda r: (order.get(r["model"], 9), r["run"]))
    (TRACES / "matrix.json").write_text(json.dumps(rows))
    print(f"traces/matrix.json  {len(rows)} runs, derived from the traces themselves")

    first = ROOT / "traces" / "claude-haiku.json"
    if first.exists():
        (DOCS / "api").mkdir(parents=True, exist_ok=True)
        shutil.copy(first, DOCS / "api" / "fallback")

    print(f"\nstatic site in {DOCS.relative_to(ROOT)}/ -- serve it with:")
    print("  python3 -m http.server -d docs 8099")


if __name__ == "__main__":
    main()
