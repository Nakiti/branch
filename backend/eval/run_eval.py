"""Eval harness. Run with: python eval/run_eval.py"""

import asyncio
import glob
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from judge import score_synthesis


async def run_eval(dataset_dir: str | None = None) -> list[dict]:
    if dataset_dir is None:
        dataset_dir = os.path.join(os.path.dirname(__file__), "dataset")

    pattern = os.path.join(dataset_dir, "*.json")
    cases = sorted(glob.glob(pattern))

    if not cases:
        print(f"No eval cases found in {dataset_dir}", file=sys.stderr)
        return []

    results = []
    for filepath in cases:
        with open(filepath) as f:
            case = json.load(f)

        print(f"Evaluating {case['id']} ...", file=sys.stderr)

        # Placeholder: in production, call the merge service to get a real synthesis.
        # For offline eval, the dataset JSON can include a "candidate_merge" field.
        synthesis = case.get("candidate_merge", "")

        scores = await score_synthesis(
            case["parent_context"],
            case["branch_context"],
            synthesis,
            case["ideal_merge"],
        )

        results.append({"id": case["id"], "scores": scores})

    avg = {
        "coverage": sum(r["scores"]["coverage"] for r in results) / len(results),
        "precision": sum(r["scores"]["precision"] for r in results) / len(results),
        "coherence": sum(r["scores"]["coherence"] for r in results) / len(results),
    }

    return {"results": results, "averages": avg}


if __name__ == "__main__":
    output = asyncio.run(run_eval())
    print(json.dumps(output, indent=2))
