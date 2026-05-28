from fastapi import Request, HTTPException
from db import get_db


async def get_current_user(request: Request) -> str:
    """Extract and validate Supabase JWT, return user_id as a string.

    Raises 401 if the Authorization header is missing or the token is invalid.
    Use as a FastAPI dependency: user_id: str = Depends(get_current_user)
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

    token = auth_header.removeprefix("Bearer ").strip()
    if not token:
        raise HTTPException(status_code=401, detail="Missing token")

    db = await get_db()
    try:
        response = await db.auth.get_user(token)
        user = response.user
        if user is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return str(user.id)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")
