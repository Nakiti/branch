from fastapi import APIRouter, Depends, HTTPException

from db import get_db
from services.auth import get_current_user

router = APIRouter()


def _build_tree(thread_id: str, threads_map: dict, children_map: dict) -> dict:
    thread = threads_map[thread_id]
    return {
        "thread": thread,
        "fork_message_id": thread.get("fork_source_message_id"),
        "children": [
            _build_tree(child_id, threads_map, children_map)
            for child_id in children_map.get(thread_id, [])
        ],
    }


@router.get("/tree")
async def get_tree(
    root_thread_id: str,
    user_id: str = Depends(get_current_user),
) -> dict:
    db = await get_db()

    # Ownership check on root thread
    root_resp = await db.table("threads").select("owner_id").eq("id", root_thread_id).execute()
    if not root_resp.data or root_resp.data[0]["owner_id"] != user_id:
        raise HTTPException(status_code=404, detail="Thread not found")

    # Fetch all threads for this user (for building the full subtree)
    all_resp = await db.table("threads").select("*").eq("owner_id", user_id).execute()
    all_threads: list[dict] = all_resp.data or []

    threads_map = {t["id"]: t for t in all_threads}

    # Batch-fetch which thread owns each fork_source_message_id
    fork_message_ids = [
        t["fork_source_message_id"]
        for t in all_threads
        if t.get("fork_source_message_id")
    ]

    msg_to_thread: dict[str, str] = {}
    if fork_message_ids:
        msgs_resp = (
            await db.table("messages")
            .select("id,thread_id")
            .in_("id", fork_message_ids)
            .execute()
        )
        msg_to_thread = {m["id"]: m["thread_id"] for m in (msgs_resp.data or [])}

    # Build parent → children mapping
    children_map: dict[str, list[str]] = {t["id"]: [] for t in all_threads}
    for thread in all_threads:
        fsm_id = thread.get("fork_source_message_id")
        if fsm_id and fsm_id in msg_to_thread:
            parent_id = msg_to_thread[fsm_id]
            if parent_id in children_map:
                children_map[parent_id].append(thread["id"])

    if root_thread_id not in threads_map:
        raise HTTPException(status_code=404, detail="Root thread not found")

    return _build_tree(root_thread_id, threads_map, children_map)
