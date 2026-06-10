"""Eval harness. Run with: python eval/run_eval.py"""

import asyncio
import glob
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from judge import score_synthesis, score_multi_synthesis


def _avg(results: list[dict], dims: list[str]) -> dict:
    if not results:
        return {}
    return {
        dim: round(sum(r["scores"][dim] for r in results if dim in r["scores"]) / len(results), 2)
        for dim in dims
    }


async def run_eval(dataset_dir: str | None = None) -> dict:
    if dataset_dir is None:
        dataset_dir = os.path.join(os.path.dirname(__file__), "dataset")

    pattern = os.path.join(dataset_dir, "*.json")
    cases = sorted(glob.glob(pattern))

    if not cases:
        print(f"No eval cases found in {dataset_dir}", file=sys.stderr)
        return {}

    results = []
    for filepath in cases:
        with open(filepath) as f:
            case = json.load(f)

        case_type = case.get("type", "single_branch")
        print(f"Evaluating {case['id']} ({case_type}) ...", file=sys.stderr)

        synthesis = case.get("candidate_merge", "")

        if case_type == "multi_branch":
            scores = await score_multi_synthesis(
                case["parent_context"],
                case["branches"],
                synthesis,
                case["ideal_merge"],
                case.get("key_conclusions"),
            )
        else:
            scores = await score_synthesis(
                case["parent_context"],
                case["branch_context"],
                synthesis,
                case["ideal_merge"],
                case.get("key_conclusions"),
            )

        results.append({"id": case["id"], "type": case_type, "scores": scores})

    single = [r for r in results if r["type"] != "multi_branch"]
    multi = [r for r in results if r["type"] == "multi_branch"]

    single_dims = ["coverage", "precision", "coherence", "recall"]
    multi_dims = ["consensus", "divergence", "per_branch_insight", "precision", "coherence", "recall"]

    return {
        "results": results,
        "averages": {
            "single_branch": _avg(single, single_dims),
            "multi_branch": _avg(multi, multi_dims),
        },
    }


if __name__ == "__main__":
    output = asyncio.run(run_eval())
    print(json.dumps(output, indent=2))
