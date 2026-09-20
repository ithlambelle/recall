"""Optional Jev triage for ordering expensive counterfactual tests.

Jev is advisory: it can change investigation order, but a memory enters the
repair set only when a real agent rerun reaches CORRECT without it.
"""
from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class TriageScore:
    memory_id: str
    suspicious_probability: float
    choice: str
    confidence: float


class JevTriage:
    def __init__(self, api_key=None, model="jev-latest", client=None):
        if client is None:
            from typesafe_sdk import TypeSafeClient
            client = TypeSafeClient(api_key=api_key) if api_key else TypeSafeClient()
        self.client, self.model = client, model
        self.calls = 0
        self.failures: list[str] = []

    def rank(self, task, outcome, memories):
        from typesafe_sdk import Choice
        state = {
            "task": task["prompt"],
            "observed_outcome": outcome,
            "memories": [{"id": m.id, "content": m.content, "source": m.source.value,
                          "trust": m.trust, "derived_from": m.derived_from}
                         for m in memories],
        }
        questions = {
            f"memory_{m.id}": Choice(
                instructions=f"How should memory {m.id} be prioritized when investigating this task failure?",
                criteria={
                    "suspected_cause": "Likely contributed to the failure; test it early",
                    "related": "Relevant context but not clearly causal",
                    "unlikely": "Unlikely to have contributed to this failure",
                },
            ) for m in memories
        }
        self.calls += 1
        response = self.client.system_one(state=state, questions=questions, model=self.model)
        scores = []
        for memory in memories:
            answer = response.answers[f"memory_{memory.id}"]
            probabilities = dict(answer.probabilities)
            scores.append(TriageScore(memory.id,
                                      float(probabilities.get("suspected_cause", 0.0)),
                                      answer.choice, float(answer.confidence)))
        return sorted(scores, key=lambda score: score.suspicious_probability, reverse=True)


class StaticTriage:
    """Deterministic test adapter; no network or SDK required."""
    def __init__(self, priorities):
        self.priorities, self.calls, self.failures = priorities, 0, []

    def rank(self, task, outcome, memories):
        self.calls += 1
        return [TriageScore(m.id, float(self.priorities.get(m.id, 0)), "suspected_cause", 1.0)
                for m in sorted(memories,
                                key=lambda item: self.priorities.get(item.id, 0), reverse=True)]
