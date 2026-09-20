# Recall

Causal diagnosis and dependency-guided rollback for agent memory.

When a memory-augmented agent does something harmful, Recall finds which stored
memories actually caused it (counterfactual reruns), traces everything derived from
them, rolls back only that branch, and replays only the affected actions.

## Run

```bash
python3 demo.py                      # 90-second narrative, offline, deterministic
python3 experiment.py                # delete-source vs reset vs Recall
python3 demo.py --policy enforce     # provenance write policy quarantines the poison up front
ANTHROPIC_API_KEY=... python3 demo.py --agent claude   # real LLM backend
```

## Layout

| File | Role |
|---|---|
| `recall/models.py` | `Memory` (source, trust, status, `derived_from`, `independent_support`) and `Action` |
| `recall/policy.py` | Provenance write policy. Trust comes from *where* a write came from; derived memories inherit min parent trust (taint) |
| `recall/store.py` | `MemoryStore` interface + in-memory implementation. Backend adapters go here |
| `recall/retrieval.py` | Deterministic tag retrieval (swap for embeddings later) |
| `recall/agents.py` | `RuleAgent` (offline stand-in) and `ClaudeAgent` (JSON-constrained) |
| `recall/runtime.py` | Runs tasks, logs which memories each action consumed; harm oracle |
| `recall/attribution.py` | Leave-one-out, then greedy + prune when memories reinforce each other |
| `recall/rollback.py` | Descendant closure, preserve independently supported memories, selective replay |
| `recall/facade.py` | 17x9 frame renderer + terminal preview for the Green Building simulator |
| `scenario.py` | Accounts-payable scenario with a MINJA-style poisoned write |

## Current results (RuleAgent)

| Strategy | Recovered | Harmful | Benign kept | Poison left | Repair calls |
|---|---|---|---|---|---|
| Delete source only | 2/4 | 2 | 14/14 | 2 | 0 |
| Full reset | 0/4 | 0 | 0/14 | 0 | 0 |
| Recall | 4/4 | 0 | 14/14 | 0 | 26 |

Deleting the poisoned source leaves the agent's derived "supplier profile" active, so
payments still go to the attacker. This is the failure mode described in the rollback paper.

## Builds on

- MemAudit, arXiv:2605.23723 — counterfactual memory influence for post-hoc auditing
- Dependency-guided rollback repair, arXiv:2608.10502 — typed provenance graph, selective replay
- TracLLM, arXiv:2506.04202 — context traceback; LOO/Shapley baselines
- MINJA, arXiv:2503.03704 — query-only memory injection threat model

We could not find public implementations of the first two. Recall chains them:
MemAudit-style diagnosis feeds rollback, which assumes diagnosis is given.

## Honest caveats

- `RuleAgent` is deterministic and hand-built; the consolidation step that creates the
  derived profile is scripted. Results must be re-run with `--agent claude` before quoting.
- The harm oracle uses expected recipients. In deployment it would be a policy check
  (vendor master file), not labels.
- Evaluation-only ground truth lives in `scenario.py`; Recall never reads it.
- Facade endpoint and FPS limits come from Hack 140 repos; confirm at the event.
