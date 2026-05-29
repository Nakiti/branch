"""
Generates eval dataset for the Branch merge synthesizer.

Usage:
    python eval/generate_dataset.py

Writes 8 JSON files to eval/dataset/eval_001.json through eval_008.json.
Does NOT overwrite existing files — delete manually if you want to regenerate.
"""

import asyncio
import json
import os
from anthropic import Anthropic

client = Anthropic()

# Each spec defines what conversations to generate
# The ideal_merge and key_conclusions are filled in AFTER generation (see Step 2)
DATASET_SPECS = [
    {
        "id": "eval_001",
        "description": "Branch explores attention mechanism deeper, parent asked about training",
        "parent_turns": [
            "Explain transformer architecture at a high level",
            "How does the training process work?",
        ],
        "fork_point_index": 1,  # fork happens after assistant turn 1 (0-indexed)
        "branch_turns": [
            "Go deeper on the attention mechanism specifically",
            "Why does multi-head attention help over single-head?",
        ],
    },
    {
        "id": "eval_002",
        "description": "Branch explores alternatives to transformers, parent discussing transformers",
        "parent_turns": [
            "What makes transformers so dominant in modern ML?",
            "What are their main weaknesses?",
        ],
        "fork_point_index": 1,
        "branch_turns": [
            "What are the most promising alternatives to transformers?",
            "How does Mamba compare specifically?",
        ],
    },
    {
        "id": "eval_003",
        "description": "Branch resolves LoRA vs full fine-tuning tradeoff",
        "parent_turns": [
            "I want to fine-tune an LLM for a specific task. Where do I start?",
            "What data do I need?",
        ],
        "fork_point_index": 1,
        "branch_turns": [
            "Should I use LoRA or full fine-tuning?",
            "What are the memory implications of each?",
            "When would full fine-tuning actually be worth it?",
        ],
    },
    {
        "id": "eval_004",
        "description": "Branch adds chain of thought as a specific prompting technique",
        "parent_turns": [
            "What are the basics of prompt engineering?",
            "How do I make prompts more reliable?",
        ],
        "fork_point_index": 1,
        "branch_turns": [
            "Tell me specifically about chain of thought prompting",
            "Does chain of thought help with all task types or just some?",
        ],
    },
    {
        "id": "eval_005",
        "description": "Branch dives into chunking strategies as a subtopic of RAG",
        "parent_turns": [
            "How do I design a RAG system from scratch?",
            "What vector database should I use?",
        ],
        "fork_point_index": 1,
        "branch_turns": [
            "Let's focus just on chunking strategies for the documents",
            "What is the impact of chunk size on retrieval quality?",
            "What is semantic chunking and when should I use it?",
        ],
    },
    {
        "id": "eval_006",
        "description": "Branch explores LLM-as-judge reliability, meta topic relevant to this eval",
        "parent_turns": [
            "How do you evaluate LLM outputs at scale?",
            "What metrics make sense for open-ended generation tasks?",
        ],
        "fork_point_index": 1,
        "branch_turns": [
            "How reliable is using an LLM as a judge for evaluating other LLM outputs?",
            "What are the known failure modes of LLM-as-judge?",
            "How do I calibrate a judge prompt to reduce bias?",
        ],
    },
    {
        "id": "eval_007",
        "description": "Short parent, long branch — tests that long branches summarize well",
        "parent_turns": [
            "What is RLHF?",
        ],
        "fork_point_index": 0,
        "branch_turns": [
            "Walk me through the full RLHF pipeline step by step",
            "How is the reward model trained?",
            "What are the risks of reward hacking?",
            "How does PPO work in this context?",
            "What does Constitutional AI do differently?",
        ],
    },
    {
        "id": "eval_008",
        "description": "Parent continued after fork AND branch contradicts parent assumption — hardest case",
        "parent_turns": [
            "Is scaling laws still the main driver of LLM progress?",
            "So we should expect GPT-5 to just be much bigger than GPT-4?",
        ],
        "fork_point_index": 1,
        "branch_turns": [
            "Are there signs that scaling is hitting diminishing returns?",
            "What evidence is there that we are approaching the limits of pretraining data?",
            "What approaches are people exploring beyond just scaling?",
        ],
        # NOTE: parent continued with assumption that scaling still works,
        # branch found evidence against that assumption — conflict scenario
        "parent_continuation_turns": [
            "What compute budget would be needed to train a model 10x bigger than GPT-4?",
        ],
    },
]


async def generate_conversation(turns: list[str], system: str = None) -> list[dict]:
    """Generate a realistic back-and-forth conversation from a list of user turns."""
    messages = []
    for user_turn in turns:
        messages.append({"role": "user", "content": user_turn})
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=400,
            system=system or "You are a knowledgeable AI assistant. Give accurate, substantive responses. Be specific and technical where appropriate. Keep responses to 3-5 sentences.",
            messages=messages,
        )
        assistant_content = response.content[0].text
        messages.append({"role": "assistant", "content": assistant_content})
    return messages


async def generate_example(spec: dict) -> dict:
    """Generate one eval example from a spec."""
    print(f"Generating {spec['id']}: {spec['description']}")

    # Generate parent conversation
    parent_messages = await generate_conversation(spec["parent_turns"])

    # Truncate parent at fork point (inclusive of fork_point_index assistant turn)
    # fork_point_index is 0-indexed into assistant turns
    # Each assistant turn is at position 2*i+1 in the messages list
    fork_at = (spec["fork_point_index"] * 2) + 1  # index of the fork assistant message
    parent_context = parent_messages[: fork_at + 1]

    # Generate branch conversation (seeded with parent context up to fork)
    branch_seed = parent_context.copy()
    branch_messages_full = await generate_conversation(
        spec["branch_turns"],
        system="You are a knowledgeable AI assistant. Give accurate, substantive responses. Be specific and technical. Keep responses to 3-5 sentences.",
    )
    # branch_context is just the branch turns, not the parent prefix
    branch_context = branch_messages_full

    # Generate parent continuation if specified (eval_008)
    parent_continuation = []
    if "parent_continuation_turns" in spec:
        continuation_seed = parent_messages  # full parent, not truncated
        continuation = await generate_conversation(
            spec["parent_continuation_turns"],
            system="You are a knowledgeable AI assistant. Continue this conversation assuming scaling laws are still working well. Be specific.",
        )
        parent_continuation = continuation

    return {
        "id": spec["id"],
        "description": spec["description"],
        "fork_point_index": spec["fork_point_index"],
        "parent_context": parent_context,
        "branch_context": branch_context,
        "parent_continuation": parent_continuation,
        # These are left empty — fill in manually in Step 2
        "ideal_merge": "",
        "key_conclusions": [],
    }


async def main():
    os.makedirs("eval/dataset", exist_ok=True)

    for spec in DATASET_SPECS:
        output_path = f"eval/dataset/{spec['id']}.json"

        if os.path.exists(output_path):
            print(f"Skipping {spec['id']} — already exists")
            continue

        example = await generate_example(spec)

        with open(output_path, "w") as f:
            json.dump(example, f, indent=2)

        print(f"  Written to {output_path}")
        print(f"  Parent context: {len(example['parent_context'])} messages")
        print(f"  Branch context: {len(example['branch_context'])} messages")
        print()

    print("Done. Now open each file and fill in ideal_merge and key_conclusions manually.")


if __name__ == "__main__":
    asyncio.run(main())
