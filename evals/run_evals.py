"""Offline eval harness. Run: python -m evals.run_evals

Metrics (all computed from evals/dataset.jsonl, nothing hard-coded):
  tool_selection  - expected tools are a subset of the tools actually called
  retrieval       - top retrieved doc matches the expected source (where specified)
  task_completion - the final-turn side effect matches (ticket created iff expected)
"""
import json
import sys
from pathlib import Path

from app.agents.orchestrator import Orchestrator
from app.config import Settings
from app.memory.store import MemoryStore
from app.tools import registry

DATASET = Path(__file__).parent / "dataset.jsonl"


def run() -> dict:
    cases = [json.loads(line) for line in DATASET.read_text().splitlines() if line.strip()]
    tool_ok = ret_ok = ret_n = done_ok = 0
    failures = []
    for case in cases:
        registry.TICKETS.clear()
        orch = Orchestrator(Settings(), memory=MemoryStore(":memory:"))
        session, last = None, None
        called: list[str] = []
        for turn in case["turns"]:
            last = orch.handle(turn, session, case["customer"])
            session = last.session_id
            called += [c.name for c in last.tool_calls]
        t = set(case["expect_tools"]) <= set(called)
        tool_ok += t
        r = True
        if case["expect_source"]:
            ret_n += 1
            r = bool(last.sources) and last.sources[0].doc == case["expect_source"]
            ret_ok += r
        d = bool(registry.TICKETS) == case["expect_ticket"]
        done_ok += d
        if not (t and r and d):
            failures.append(case["id"])
    n = len(cases)
    return {
        "cases": n,
        "tool_selection_accuracy": round(tool_ok / n, 3),
        "retrieval_correctness": round(ret_ok / ret_n, 3) if ret_n else None,
        "task_completion_rate": round(done_ok / n, 3),
        "failed_case_ids": failures,
    }


if __name__ == "__main__":
    results = run()
    print(json.dumps(results, indent=2))
    Path(__file__).with_name("results.json").write_text(json.dumps(results, indent=2))
    sys.exit(1 if results["failed_case_ids"] else 0)
