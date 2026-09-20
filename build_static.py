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

    recorded = ROOT / "recorded_trace.json"
    if recorded.exists():
        for name in ("claude-haiku.json", "../api/fallback"):
            dest = TRACES / name if name.endswith(".json") else DOCS / "api" / "fallback"
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(recorded.read_text())
        t = json.loads(recorded.read_text())
        print(f"traces/claude-haiku.json  real run: {t['summary']['usage']['model']}, "
              f"recovered {t['summary']['recovered']}/{t['summary']['tasks']}")
    else:
        print("WARNING: recorded_trace.json missing; the Claude option will have no trace")

    print(f"\nstatic site in {DOCS.relative_to(ROOT)}/ -- serve it with:")
    print("  python3 -m http.server -d docs 8099")


if __name__ == "__main__":
    main()
