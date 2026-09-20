"""Load a local .env if present, so the key never has to live in shell history.

Deliberately dependency-free and non-destructive: real environment variables
always win, which is what hosted deployments rely on.
"""
from __future__ import annotations
import os
import pathlib

ENV_FILE = pathlib.Path(__file__).resolve().parent.parent / ".env"


def load(path: pathlib.Path = ENV_FILE) -> None:
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key, val = key.strip(), val.strip().strip("'\"")
        os.environ.setdefault(key, val)  # never override a real env var
