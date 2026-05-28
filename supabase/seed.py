#!/usr/bin/env python3
"""Apply seed.sql data to Supabase using the service key.

Mirrors the logic in seed.sql but replaces auth.uid() with a real user UUID
obtained via the Admin API. Skips silently if seed data already exists.

Usage (from repo root): python supabase/seed.py
"""

import asyncio
import os
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / "backend" / ".env")

from supabase import acreate_client, AsyncClient


async def get_owner_id(client: AsyncClient) -> str:
    """Return the first existing user's UUID, creating a dev seed user if needed."""
    resp = await client.auth.admin.list_users()
    users = resp if isinstance(resp, list) else getattr(resp, "users", resp)

    if users:
        user = users[0]
        uid = getattr(user, "id", user.get("id") if isinstance(user, dict) else None)
        return str(uid)

    # No users yet — create a dev-only seed account
    print("No users found — creating dev seed user (seed@branch.local) ...")
    create_resp = await client.auth.admin.create_user(
        {
            "email": "seed@branch.local",
            "password": "SeedPassword123!",
            "email_confirm": True,
        }
    )
    user = getattr(create_resp, "user", create_resp)
    uid = getattr(user, "id", user.get("id") if isinstance(user, dict) else None)
    print(f"Created seed user: seed@branch.local  (id: {uid})")
    return str(uid)


async def seed() -> None:
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_SERVICE_KEY"]
    client = await acreate_client(url, key)

    # Idempotency guard — matches the seed.sql DO $$ block
    existing = await client.table("threads").select("id").limit(1).execute()
    if existing.data:
        print("Seed data already present — skipping.")
        return

    owner_id = await get_owner_id(client)
    print(f"Seeding as user: {owner_id}")

    root_thread_id = str(uuid.uuid4())
    branch_thread_id = str(uuid.uuid4())
    fork_message_id = str(uuid.uuid4())

    # Root thread
    await client.table("threads").insert(
        {"id": root_thread_id, "owner_id": owner_id, "label": "Test Root Thread"}
    ).execute()

    # Root thread messages — second message is the fork point.
    # All rows get explicit UUIDs to avoid postgrest padding nulls in batch inserts.
    await client.table("messages").insert([
        {
            "id": str(uuid.uuid4()),
            "thread_id": root_thread_id,
            "role": "user",
            "content": "Explain transformer architecture",
        },
        {
            "id": fork_message_id,
            "thread_id": root_thread_id,
            "role": "assistant",
            "content": "Transformers use self-attention to process sequences in parallel...",
        },
        {
            "id": str(uuid.uuid4()),
            "thread_id": root_thread_id,
            "role": "user",
            "content": "How does training work?",
        },
        {
            "id": str(uuid.uuid4()),
            "thread_id": root_thread_id,
            "role": "assistant",
            "content": "Training uses backpropagation through the attention layers...",
        },
    ]).execute()

    # Branch thread (forked from the second message of the root thread)
    await client.table("threads").insert(
        {
            "id": branch_thread_id,
            "owner_id": owner_id,
            "label": "Attention deep dive",
            "fork_source_message_id": fork_message_id,
        }
    ).execute()

    # Branch thread messages
    await client.table("messages").insert([
        {
            "id": str(uuid.uuid4()),
            "thread_id": branch_thread_id,
            "role": "user",
            "content": "Go deeper on the attention mechanism",
        },
        {
            "id": str(uuid.uuid4()),
            "thread_id": branch_thread_id,
            "role": "assistant",
            "content": "Attention computes query, key, value matrices from the input...",
        },
    ]).execute()

    print("Seed complete.")
    print(f"  Root thread:   {root_thread_id}")
    print(f"  Branch thread: {branch_thread_id}")
    print(f"  Fork message:  {fork_message_id}")


if __name__ == "__main__":
    asyncio.run(seed())
