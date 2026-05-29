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


def annotate_example(path: str):
    with open(path) as f:
        example = json.load(f)

    if example["ideal_merge"] and example["key_conclusions"]:
        print(f"Skipping {example['id']} — already annotated")
        return

    print(f"\n\n{'#'*60}")
    print(f"  EXAMPLE: {example['id']}")
    print(f"  {example['description']}")
    print(f"{'#'*60}")

    print_messages(example["parent_context"], "PARENT CONTEXT (up to fork point)")
    print_messages(example["branch_context"], "BRANCH EXPLORATION")

    if example.get("parent_continuation"):
        print_messages(example["parent_continuation"], "PARENT CONTINUATION (after fork)")

    print(f"\n{'='*60}")
    print("  YOUR TASK: Write the ideal merge message")
    print("  This should be 2-4 sentences that capture the most")
    print("  important insight from the branch, framed to be useful")
    print("  for continuing the main conversation.")
    print(f"{'='*60}\n")

    print("Enter ideal_merge (type END on a new line when done):")
    lines = []
    while True:
        line = input()
        if line.strip() == "END":
            break
        lines.append(line)
    ideal_merge = "\n".join(lines).strip()

    print("\nEnter key_conclusions — one per line, these are facts that MUST")
    print("appear in any good merge. Type END when done:")
    conclusions = []
    while True:
        line = input()
        if line.strip() == "END":
            break
        if line.strip():
            conclusions.append(line.strip())

    example["ideal_merge"] = ideal_merge
    example["key_conclusions"] = conclusions

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
