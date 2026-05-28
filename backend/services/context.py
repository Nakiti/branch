"""Context Reconstructor — the critical service for building Claude API message lists.

Every Claude API call must use reconstruct_context(). Never query messages for a thread
directly without it — you will send the wrong context to the model.
"""

import os
import sys

# Ensure the backend root is on sys.path so `db` can be found when this file is
# executed directly (e.g. python3 services/context.py) as well as when it is
# imported as part of the package.
_BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BACKEND_ROOT not in sys.path:
    sys.path.insert(0, _BACKEND_ROOT)

from db import get_db


async def _fetch_thread(thread_id: str) -> dict:
    db = await get_db()
    resp = await db.table("threads").select("*").eq("id", thread_id).execute()
    if not resp.data:
        raise ValueError(f"Thread not found: {thread_id}")
    return resp.data[0]


async def _fetch_messages_for_thread(thread_id: str) -> list[dict]:
    db = await get_db()
    resp = (
        await db.table("messages")
        .select("*")
        .eq("thread_id", thread_id)
        .order("created_at")
        .execute()
    )
    return resp.data or []


async def _fetch_message(message_id: str) -> dict:
    db = await get_db()
    resp = await db.table("messages").select("id,thread_id").eq("id", message_id).execute()
    if not resp.data:
        raise ValueError(f"Message not found: {message_id}")
    return resp.data[0]


async def _reconstruct_core(
    thread_id: str,
    fetch_thread,
    fetch_messages,
    fetch_message,
    depth: int = 0,
) -> list[dict]:
    if depth >= 20:
        raise ValueError("Fork chain depth limit exceeded (max 20 levels)")

    thread = await fetch_thread(thread_id)
    own_messages = await fetch_messages(thread_id)

    fork_source_id = thread.get("fork_source_message_id")
    if fork_source_id is None:
        return own_messages

    fork_msg = await fetch_message(fork_source_id)
    parent_thread_id = fork_msg["thread_id"]

    parent_context = await _reconstruct_core(
        parent_thread_id, fetch_thread, fetch_messages, fetch_message, depth + 1
    )

    # Keep parent messages up to and including the fork point
    truncated: list[dict] = []
    for msg in parent_context:
        truncated.append(msg)
        if msg["id"] == fork_source_id:
            break

    return truncated + own_messages


async def reconstruct_context(thread_id: str) -> list[dict]:
    """Return the full ordered message list for thread_id.

    Walks the fork chain to the root, truncates each ancestor at its fork point,
    and appends the thread's own messages at the end.
    """
    return await _reconstruct_core(
        thread_id,
        _fetch_thread,
        _fetch_messages_for_thread,
        _fetch_message,
    )


if __name__ == "__main__":
    import asyncio
    import uuid

    # 3-level chain: A (root) → B (forked from A1) → C (forked from B1)
    tid_a = str(uuid.uuid4())
    tid_b = str(uuid.uuid4())
    tid_c = str(uuid.uuid4())

    mid_a1 = str(uuid.uuid4())
    mid_a2 = str(uuid.uuid4())
    mid_b1 = str(uuid.uuid4())
    mid_b2 = str(uuid.uuid4())
    mid_c1 = str(uuid.uuid4())
    mid_c2 = str(uuid.uuid4())

    threads_data = {
        tid_a: {"id": tid_a, "fork_source_message_id": None},
        tid_b: {"id": tid_b, "fork_source_message_id": mid_a1},
        tid_c: {"id": tid_c, "fork_source_message_id": mid_b1},
    }
    messages_data = {
        tid_a: [
            {"id": mid_a1, "thread_id": tid_a, "role": "user", "content": "A1"},
            {"id": mid_a2, "thread_id": tid_a, "role": "assistant", "content": "A2"},
        ],
        tid_b: [
            {"id": mid_b1, "thread_id": tid_b, "role": "user", "content": "B1"},
            {"id": mid_b2, "thread_id": tid_b, "role": "assistant", "content": "B2"},
        ],
        tid_c: [
            {"id": mid_c1, "thread_id": tid_c, "role": "user", "content": "C1"},
            {"id": mid_c2, "thread_id": tid_c, "role": "assistant", "content": "C2"},
        ],
    }
    msg_parent_data = {
        mid_a1: {"id": mid_a1, "thread_id": tid_a},
        mid_a2: {"id": mid_a2, "thread_id": tid_a},
        mid_b1: {"id": mid_b1, "thread_id": tid_b},
        mid_b2: {"id": mid_b2, "thread_id": tid_b},
        mid_c1: {"id": mid_c1, "thread_id": tid_c},
        mid_c2: {"id": mid_c2, "thread_id": tid_c},
    }

    async def mock_fetch_thread(tid: str) -> dict:
        return threads_data[tid]

    async def mock_fetch_messages(tid: str) -> list[dict]:
        return messages_data[tid]

    async def mock_fetch_message(mid: str) -> dict:
        return msg_parent_data[mid]

    async def run_test() -> None:
        result = await _reconstruct_core(
            tid_c, mock_fetch_thread, mock_fetch_messages, mock_fetch_message
        )

        # Expected: [A1, B1, C1, C2]
        # A2 is excluded (comes after fork point A1 in thread A)
        # B2 is excluded (comes after fork point B1 in thread B)
        assert len(result) == 4, f"Expected 4 messages, got {len(result)}: {[m['content'] for m in result]}"
        assert result[0]["id"] == mid_a1, f"pos 0: expected A1, got {result[0]['content']}"
        assert result[1]["id"] == mid_b1, f"pos 1: expected B1, got {result[1]['content']}"
        assert result[2]["id"] == mid_c1, f"pos 2: expected C1, got {result[2]['content']}"
        assert result[3]["id"] == mid_c2, f"pos 3: expected C2, got {result[3]['content']}"
        print(f"All tests passed. Context: {[m['content'] for m in result]}")

    asyncio.run(run_test())
