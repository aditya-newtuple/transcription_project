from typing import Optional
from fastapi import Header, HTTPException, status

async def get_current_user(authorization: Optional[str] = Header(None)) -> int:
    """
    Dummy auth dependency that returns user ID=1 if Authorization header is present.
    In production, this would validate the token and return the actual user.
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header is required"
        )
    # For now, just return a dummy user ID
    return 1 