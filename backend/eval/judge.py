import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import anthropic

JUDGE_PROMPT = """Score this merge synthesis on three dimensions (1-5 each):

PARENT CONTEXT: {parent_context}
BRANCH CONTEXT: {branch_context}
SYNTHESIS TO SCORE: {synthesis}
IDEAL SYNTHESIS: {ideal}

Score:
1. Coverage: Did it capture the key conclusions from the branch? (1=missed most, 5=captured all)
2. Precision: Did it avoid injecting noise or irrelevant content? (1=lots of noise, 5=clean)
3. Coherence: Would this flow naturally in the main conversation? (1=jarring, 5=seamless)

Respond in JSON: {{"coverage": N, "precision": N, "coherence": N, "reasoning": "..."}}"""

MULTI_JUDGE_PROMPT = """Score this multi-branch merge synthesis on five dimensions (1-5 each):

PARENT CONTEXT (up to fork point): {parent_context}

BRANCH EXPLORATIONS:
{branches}

SYNTHESIS TO SCORE: {synthesis}
IDEAL SYNTHESIS: {ideal}

Score:
1. Consensus Identification: Did it correctly identify what both branches agreed on? (1=missed all consensus, 5=fully identified)
2. Divergence Flagging: Did it clearly surface where branches reached different or contradictory conclusions? (1=ignored divergence, 5=clearly flagged with explanation)
3. Per-Branch Insight: Did it surface at least one distinct insight unique to each branch? (1=no unique insights per branch, 5=one strong unique insight per branch)
4. Precision: Did it avoid injecting noise or content not supported by the branches? (1=lots of fabrication, 5=clean)
5. Coherence: Would this flow naturally as an artifact in the main conversation? (1=jarring, 5=seamless)

Respond in JSON: {{"consensus": N, "divergence": N, "per_branch_insight": N, "precision": N, "coherence": N, "reasoning": "..."}}"""


def _parse_json(text: str) -> dict:
    """Parse JSON from Claude response, stripping markdown code fences if present."""
    text = text.strip()
    if text.startswith("```"):
        # Strip opening fence (```json or ```) and closing fence
        lines = text.splitlines()
        text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
    return json.loads(text.strip())


def _fmt(messages: list[dict]) -> str:
    return "\n".join(f"{m['role'].upper()}: {m['content']}" for m in messages)


def _fmt_branches(branches: list[dict]) -> str:
    parts = []
    for b in branches:
        label = b.get("label", "Branch")
        ctx = _fmt(b.get("context", []))
        parts.append(f"--- Branch: {label} ---\n{ctx}")
    return "\n\n".join(parts)


def _recall_score(synthesis: str, key_conclusions: list[str]) -> int:
    """Keyword-hit recall: what fraction of key conclusions appear in the synthesis (scored 1-5)."""
    if not key_conclusions:
        return 5
    synthesis_lower = synthesis.lower()
    hits = sum(
        1 for c in key_conclusions
        if any(word in synthesis_lower for word in c.lower().split()[:5])
    )
    return max(1, round(hits / len(key_conclusions) * 5))


def _recall_score_multi(synthesis: str, key_conclusions: dict) -> int:
    """Recall across all structured key_conclusions categories."""
    all_facts = (
        key_conclusions.get("consensus", [])
        + key_conclusions.get("branch_a_unique", [])
        + key_conclusions.get("branch_b_unique", [])
        + key_conclusions.get("contradictions", [])
    )
    return _recall_score(synthesis, all_facts)


async def score_synthesis(
    parent_context: list[dict],
    branch_context: list[dict],
    synthesis: str,
    ideal: str,
    key_conclusions: list[str] | None = None,
) -> dict:
    client = anthropic.AsyncAnthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    prompt = JUDGE_PROMPT.format(
        parent_context=_fmt(parent_context),
        branch_context=_fmt(branch_context),
        synthesis=synthesis,
        ideal=ideal,
    )

    response = await client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=512,
        messages=[{"role": "user", "content": prompt}],
    )

    scores = _parse_json(response.content[0].text)

    if key_conclusions:
        scores["recall"] = _recall_score(synthesis, key_conclusions)

    return scores


async def score_multi_synthesis(
    parent_context: list[dict],
    branches: list[dict],
    synthesis: str,
    ideal: str,
    key_conclusions: dict | None = None,
) -> dict:
    client = anthropic.AsyncAnthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    prompt = MULTI_JUDGE_PROMPT.format(
        parent_context=_fmt(parent_context),
        branches=_fmt_branches(branches),
        synthesis=synthesis,
        ideal=ideal,
    )

    response = await client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=512,
        messages=[{"role": "user", "content": prompt}],
    )

    scores = _parse_json(response.content[0].text)

    if key_conclusions:
        scores["recall"] = _recall_score_multi(synthesis, key_conclusions)

    return scores
