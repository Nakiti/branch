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


def _fmt(messages: list[dict]) -> str:
    return "\n".join(f"{m['role'].upper()}: {m['content']}" for m in messages)


async def score_synthesis(
    parent_context: list[dict],
    branch_context: list[dict],
    synthesis: str,
    ideal: str,
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

    return json.loads(response.content[0].text)
