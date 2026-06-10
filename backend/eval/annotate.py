"""
Interactive annotation tool for filling in ideal_merge and key_conclusions.

Usage:
    python eval/annotate.py

For each unannotated example, prints the conversations and prompts you to write
the ideal merge and key conclusions interactively.
"""

import json
import os


def print_messages(messages: list[dict], label: str):
    print(f"\n{'='*60}")
    print(f"  {label}")
    print(f"{'='*60}")
    for m in messages:
        role = "USER" if m["role"] == "user" else "ASSISTANT"
        print(f"\n[{role}]\n{m['content']}")


def _read_until_end(prompt: str) -> str:
    print(prompt)
    lines = []
    while True:
        line = input()
        if line.strip() == "END":
            break
        lines.append(line)
    return "\n".join(lines).strip()


def _read_list(prompt: str) -> list[str]:
    print(prompt)
    items = []
    while True:
        line = input()
        if line.strip() == "END":
            break
        if line.strip():
            items.append(line.strip())
    return items


def _is_annotated(example: dict) -> bool:
    if not example.get("ideal_merge"):
        return False
    kc = example.get("key_conclusions")
    if not kc:
        return False
    # Multi-branch key_conclusions are dicts; single-branch are lists
    if isinstance(kc, dict):
        return any(kc.get(k) for k in ("consensus", "branch_a_unique", "branch_b_unique", "contradictions"))
    return bool(kc)


def annotate_single(example: dict):
    print_messages(example["parent_context"], "PARENT CONTEXT (up to fork point)")
    print_messages(example["branch_context"], "BRANCH EXPLORATION")

    if example.get("parent_continuation"):
        print_messages(example["parent_continuation"], "PARENT CONTINUATION (after fork)")

    print(f"\n{'='*60}")
    print("  YOUR TASK: Write the ideal merge message (2-4 sentences)")
    print(f"{'='*60}\n")

    example["ideal_merge"] = _read_until_end("Enter ideal_merge (type END on a new line when done):")

    example["key_conclusions"] = _read_list(
        "\nEnter key_conclusions — one per line, facts that MUST appear in any good merge. Type END when done:"
    )


def annotate_multi(example: dict):
    print_messages(example["parent_context"], "PARENT CONTEXT (up to fork point)")
    for b in example.get("branches", []):
        print_messages(b["context"], f"BRANCH: {b['label']}")

    print(f"\n{'='*60}")
    print("  YOUR TASK: Write the ideal multi-branch synthesis")
    print("  Use brief headers (## Consensus, ## Divergence, etc.)")
    print(f"{'='*60}\n")

    example["ideal_merge"] = _read_until_end("Enter ideal_merge (type END on a new line when done):")

    print("\nNow enter structured key_conclusions (one item per line, END to finish each section):")

    kc: dict = {}
    kc["consensus"] = _read_list("\nConsensus — conclusions BOTH branches agree on:")
    kc["branch_a_unique"] = _read_list("\nBranch A unique — insights only Branch A reached:")
    kc["branch_b_unique"] = _read_list("\nBranch B unique — insights only Branch B reached:")
    kc["contradictions"] = _read_list("\nContradictions — where branches directly disagree:")

    example["key_conclusions"] = kc


def annotate_example(path: str):
    with open(path) as f:
        example = json.load(f)

    if _is_annotated(example):
        print(f"Skipping {example['id']} — already annotated")
        return

    print(f"\n\n{'#'*60}")
    print(f"  EXAMPLE: {example['id']}")
    print(f"  {example['description']}")
    print(f"{'#'*60}")

    if example.get("type") == "multi_branch":
        annotate_multi(example)
    else:
        annotate_single(example)

    with open(path, "w") as f:
        json.dump(example, f, indent=2)

    print(f"\nSaved {example['id']}")


def main():
    dataset_dir = "eval/dataset"
    files = sorted(f for f in os.listdir(dataset_dir) if f.endswith(".json"))

    if not files:
        print("No dataset files found. Run generate_dataset.py first.")
        return

    for filename in files:
        annotate_example(os.path.join(dataset_dir, filename))

    print("\n\nAll examples annotated.")


if __name__ == "__main__":
    main()
