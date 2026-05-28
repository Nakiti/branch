import os
import anthropic
from supabase import AsyncClient, acreate_client

_supabase: AsyncClient | None = None
_anthropic_client: anthropic.AsyncAnthropic | None = None


async def get_db() -> AsyncClient:
    global _supabase
    if _supabase is None:
        url = os.environ["SUPABASE_URL"]
        key = os.environ["SUPABASE_SERVICE_KEY"]
        _supabase = await acreate_client(url, key)
    return _supabase


def get_anthropic() -> anthropic.AsyncAnthropic:
    global _anthropic_client
    if _anthropic_client is None:
        _anthropic_client = anthropic.AsyncAnthropic(
            api_key=os.environ["ANTHROPIC_API_KEY"]
        )
    return _anthropic_client
