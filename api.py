"""Minimal HTTP surface over the Recall pipeline.

The backend is authoritative: this module adds no diagnosis or rollback logic of
its own, it only runs `recall.pipeline.run_pipeline` and serves the result.
"""
from __future__ import annotations

import json
import os
import pathlib
import threading

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from recall import env
from recall.agents import RuleAgent
from recall.pipeline import run_pipeline

env.load()

ROOT = pathlib.Path(__file__).parent
STATIC = ROOT / "static"
FALLBACK = ROOT / "last_trace.json"

app = FastAPI(title="Recall", docs_url="/api/docs")
_lock = threading.Lock()  # one pipeline at a time; runs are short and CPU-light


class RunRequest(BaseModel):
    agent: str = "rule"
    policy: str = "permissive"
    use_provenance_prior: bool = True


def _make_agent(kind: str):
    if kind == "claude":
        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise HTTPException(503, "ANTHROPIC_API_KEY is not configured on the server")
        from recall.agents import ClaudeAgent
        return ClaudeAgent()
    if kind != "rule":
        raise HTTPException(400, f"unknown agent {kind!r}")
    return RuleAgent()


@app.get("/api/health")
def health():
    return {
        "ok": True,
        "claude_available": bool(os.environ.get("ANTHROPIC_API_KEY")),
        "model": os.environ.get("RECALL_MODEL", "claude-haiku-4-5"),
        "fallback_trace": FALLBACK.exists(),
    }


@app.post("/api/run")
def run(req: RunRequest):
    if req.policy not in ("permissive", "enforce"):
        raise HTTPException(400, f"unknown policy {req.policy!r}")
    agent = _make_agent(req.agent)
    with _lock:
        trace = run_pipeline(agent, req.policy, req.use_provenance_prior)
    # Keep the most recent successful run as the offline fallback for the demo.
    try:
        FALLBACK.write_text(json.dumps(trace))
    except OSError:
        pass  # read-only filesystem on some hosts; the live path still works
    return trace


@app.get("/api/fallback")
def fallback():
    """Last successful trace, for demoing if the network or the API is down."""
    if not FALLBACK.exists():
        raise HTTPException(404, "no recorded trace yet")
    return json.loads(FALLBACK.read_text())


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


app.mount("/static", StaticFiles(directory=STATIC), name="static")
