"""Run the 10 known-answer questions through the agent and score them.

This calls the Claude API and costs money (roughly a few cents per question).

    python -m evals.run_evals            # all questions
    python -m evals.run_evals Q01 Q07    # some questions
"""

from __future__ import annotations

import asyncio
import json
import re
import sys
from datetime import datetime
from pathlib import Path

from handover.main import run

HERE = Path(__file__).resolve().parent
ANSWER_SCHEMA = {
    "type": "json_schema",
    "schema": {
        "type": "object",
        "properties": {
            "answer": {"type": "string", "description": "Short answer in one or two sentences."},
            "value": {"type": ["number", "null"], "description": "The key number, without unit, if the question asks for one."},
        },
        "required": ["answer", "value"],
        "additionalProperties": False,
    },
}


def grade(q: dict, answer: str, value: float | None) -> bool:
    text = answer.lower()
    if q["type"] == "number":
        if value is None:
            nums = [float(n) for n in re.findall(r"-?\d+(?:\.\d+)?", answer)]
            return any(abs(n - q["expected"]) <= q["tolerance"] for n in nums)
        return abs(value - q["expected"]) <= q["tolerance"]
    ok = True
    if "any_of" in q:
        ok &= any(k.lower() in text for k in q["any_of"])
    if "all_of" in q:
        ok &= all(k.lower() in text for k in q["all_of"])
    if "none_of" in q:
        ok &= not any(k.lower() in text for k in q["none_of"])
    return ok


async def main(ids: list[str]) -> int:
    questions = json.loads((HERE / "questions.json").read_text(encoding="utf-8"))
    if ids:
        questions = [q for q in questions if q["id"] in ids]
    rows, total_cost = [], 0.0
    for q in questions:
        result = await run(q["question"], mode="qa", output_format=ANSWER_SCHEMA, verbose=False)
        out = (result.structured_output if result else None) or {"answer": (result.result if result else "") or "", "value": None}
        passed = grade(q, out.get("answer", ""), out.get("value"))
        cost = (result.total_cost_usd or 0.0) if result else 0.0
        total_cost += cost
        rows.append({**q, "got": out, "passed": passed, "cost_usd": cost})
        print(f"{q['id']} {'PASS' if passed else 'FAIL'}  ${cost:.3f}  {q['question']}\n      -> {out.get('answer')}")

    score = sum(r["passed"] for r in rows)
    print(f"\nScore: {score}/{len(rows)}  |  total cost: ${total_cost:.2f}")
    out_dir = HERE / "results"
    out_dir.mkdir(exist_ok=True)
    path = out_dir / f"{datetime.now():%Y%m%d_%H%M%S}.json"
    path.write_text(json.dumps({"score": score, "n": len(rows), "cost_usd": total_cost, "rows": rows}, indent=2))
    print(f"Saved {path.relative_to(HERE.parent)}")
    return 0 if score == len(rows) else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main(sys.argv[1:])))
