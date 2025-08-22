from typing import Optional
from fastapi import Header, HTTPException, status

async def get_current_user() -> int:
    """
    Development-only dependency that always returns user ID=1.
    No authorization checks are performed.
    """
    return 1  # Always return default user ID 