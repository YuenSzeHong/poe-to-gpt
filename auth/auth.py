import logging
from fastapi import APIRouter, HTTPException, Request
from database import (get_user, reset_api_key, get_db)



# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

router = APIRouter()

async def is_admin_user(request: Request) -> bool:
    """Check if the user is an admin based on the OAuth token."""
    oauth_token = request.headers.get("Authorization", "").replace("Bearer ", "")
    logger.info(f"Attempting to authenticate admin with OAuth token: {oauth_token[:10]}...")
    if not oauth_token:
        raise HTTPException(status_code=403, detail="需要管理员权限：缺少登录令牌")

    try:
        cursor = get_db().cursor()
        cursor.execute("SELECT * FROM users WHERE linuxdo_token = %s", (oauth_token,))
        user = cursor.fetchone()
        return bool(user and user[4] and user[8])  # user[4] is enabled, user[8] is is_admin
    except Exception as e:
        logger.error(f"Database error in is_admin_user: {e}")
        return False

@router.post("/auth/reset")
async def reset_api(request: Request):
    """Reset the API key for the current user."""
    api_key = request.headers.get("Authorization", "").replace("Bearer ", "")
    if not api_key:
        raise HTTPException(status_code=403, detail="Authorization header required")

    user = get_user(api_key=api_key)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if not user[4]:  # If user is disabled
        raise HTTPException(status_code=403, detail=f"User disabled: {user[5]}")

    user_id = user[0]
    new_key = reset_api_key(user_id)

    if not new_key:
        raise HTTPException(status_code=500, detail="Failed to reset API key")

    return { "apiKey": new_key }