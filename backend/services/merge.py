import json
from db import get_anthropic

MERGE_PROMPT = """You are synthesizing insights from a side conversation branch back into a main thread.

MAIN CONVERSATION (up to current point):
{parent_context}

BRANCH EXPLORATION (started from the main conversation, explored independently):
{branch_context}

Task: Write a single concise message (2-4 sentences) that captures the most important insight or conclusion from the branch exploration, framed in a way that's useful for continuing the main conversation. Focus on what the main conversation would benefit most from knowing. Do not summarize the branch exhaustively — identify the single most valuable takeaway."""

MULTI_MERGE_PROMPT = """You are synthesizing insights from multiple parallel explorations back into a main thread.

MAIN CONVERSATION (context up to the fork point):
{parent_context}

BRANCH EXPLORATIONS:
{branches}

Task: Write a structured synthesis (use brief headers) that:
1. Identifies conclusions that appeared across multiple branches (consensus)
2. Identifies where branches reached different conclusions (divergence)
3. Surfaces the single strongest unique insight from each branch

Keep it concise — this will be injected into the main conversation as a reference point."""


def _format_context(messages: list[dict]) -> str:
    lines = []
    for m in messages:
        role = m["role"].upper()
        lines.append(f"{role}: {m['content']}")
    return "\n\n".join(lines)


async def synthesize_merge(
    parent_context: list[dict],
    branch_context: list[dict],
) -> str:
    """Call Claude to synthesize a branch back into the parent conversation."""
    client = get_anthropic()

    prompt = MERGE_PROMPT.format(
        parent_context=_format_context(parent_context),
        branch_context=_format_context(branch_context),
    )

    response = await client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=512,
        messages=[{"role": "user", "content": prompt}],
    )

    return response.content[0].text


async def synthesize_multi_merge(
    parent_context: list[dict],
    branches: list[tuple[str, list[dict]]],
) -> str:
    """Synthesize multiple branches back into a parent conversation."""
    client = get_anthropic()

    formatted_branches = "\n".join(
        f"--- Branch: {label} ---\n{_format_context(ctx)}\n"
        for label, ctx in branches
    )

    prompt = MULTI_MERGE_PROMPT.format(
        parent_context=_format_context(parent_context),
        branches=formatted_branches,
    )

    response = await client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )

    return response.content[0].text
