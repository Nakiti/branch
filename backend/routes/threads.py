from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from db import get_db
from services.auth import get_current_user

router = APIRouter()


class CreateThreadBody(BaseModel):
    label: Optional[str] = "New Conversation"


@router.get("/threads")
async def list_root_threads(
    user_id: str = Depends(get_current_user),
) -> list[dict]:
    """Return all root threads (no fork source) for the current user, newest first."""
    db = await get_db()
    resp = (
        await db.table("threads")
        .select("*")
        .eq("owner_id", user_id)
        .is_("fork_source_message_id", "null")
        .order("created_at", desc=True)
        .execute()
    )
    return resp.data or []


@router.post("/threads")
async def create_thread(
    body: CreateThreadBody,
    user_id: str = Depends(get_current_user),
) -> dict:
    db = await get_db()
    try:
        resp = await db.table("threads").insert(
            {"owner_id": user_id, "label": body.label}
        ).execute()
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to create thread")
    return resp.data[0]


@router.get("/threads/{thread_id}/messages")
async def get_thread_messages(
    thread_id: str,
    user_id: str = Depends(get_current_user),
) -> list[dict]:
    """Return messages stored directly in this thread (not reconstructed context)."""
    db = await get_db()
    thread_resp = (
        await db.table("threads")
        .select("owner_id")
        .eq("id", thread_id)
        .execute()
    )
    if not thread_resp.data or thread_resp.data[0]["owner_id"] != user_id:
        raise HTTPException(status_code=404, detail="Thread not found")
    msgs = (
        await db.table("messages")
        .select("*")
        .eq("thread_id", thread_id)
        .order("created_at")
        .execute()
    )
    return msgs.data or []
