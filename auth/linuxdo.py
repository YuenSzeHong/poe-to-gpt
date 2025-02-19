import json
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from authlib.integrations.starlette_client import OAuth

import logging
# Import the database module and functions
from database import (create_user, get_user, update_linuxdo_token, is_admin)
import datetime
import uuid
from httpx import AsyncClient
from config import config

router = APIRouter()

# LinuxDO OAuth Configuration
base_url = config.get("base_url", "http://localhost:3700")  # Your application's base URL
LINUXDO_CLIENT_KEY = config.get("LINUXDO_CLIENT_KEY")
LINUXDO_CLIENT_SECRET = config.get("LINUXDO_CLIENT_SECRET")

# Setup OAuth
# config = Config({'LINUXDO_CLIENT_ID': LINUXDO_CLIENT_KEY, 'LINUXDO_CLIENT_SECRET': LINUXDO_CLIENT_SECRET})
oauth = OAuth()
oauth.register(
    name='linuxdo',
    authorize_url='https://connect.linux.do/oauth2/authorize',
    access_token_url='https://connect.linux.do/oauth2/token',
    client_id=LINUXDO_CLIENT_KEY,
    client_secret=LINUXDO_CLIENT_SECRET,
    client_kwargs={'scope': 'openid profile email'}
)

# Optionally define UserUrl
UserUrl = "https://connect.linux.do/api/user"

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Function to generate a secure API key
def generate_api_key():
    return f"sk-yn-{uuid.uuid4()}"

# Get trust level minimum from config - None means no requirement
LINUXDO_MIN_LEVEL = config.get("LINUXDO_MIN_LEVEL", None)

# OAuth routes
@router.get('/auth/linuxdo')
async def auth_linuxdo(request: Request, self: str = None):
    """Handle LinuxDO authentication."""
    redirect_uri = base_url + '/oauth/callback'  # This must match the registered redirect URI
    return await oauth.linuxdo.authorize_redirect(request, redirect_uri)

async def verify_linuxdo_token(access_token: str) -> dict:
    """Verify token with LinuxDO's API and return user info."""
    try:
        async with AsyncClient() as client:
            headers = {"Authorization": f"Bearer {access_token}"}
            response = await client.get(UserUrl, headers=headers)
            if response.status_code == 200:
                return response.json()
            return None
    except Exception as e:
        logger.error(f"Failed to verify token with LinuxDO: {e}")
        return None

@router.get('/oauth/callback')
async def authorize(request: Request):
    try:
        token = await oauth.linuxdo.authorize_access_token(request)
        logger.info("Received token response: %s", token)
        
        access_token = token.get('access_token')
        if not access_token:
            raise HTTPException(status_code=400, detail="未收到访问令牌")

        # Get initial user info
        user_info = await verify_linuxdo_token(access_token)
        if not user_info:
            raise HTTPException(status_code=401, detail="访问令牌验证失败")

        # Extract relevant user information
        username = user_info.get('username')
        user_id = user_info.get('id')
        
        # Check if user exists
        user = get_user(user_id=user_id)

        if not user:
            # Only check trust level for new users
            if LINUXDO_MIN_LEVEL is not None:
                trust_level = user_info.get('trust_level', 0)
                if trust_level < LINUXDO_MIN_LEVEL:
                    error_message = f"新用户需要LinuxDO信任等级≥{LINUXDO_MIN_LEVEL}"
                    return HTMLResponse(f"""
                        <!DOCTYPE html>
                        <html>
                        <head>
                            <title>登录失败</title>
                            <script>
                                if (window.opener) {{
                                    window.opener.postMessage({{"error": "{error_message}"}}, window.location.origin);
                                }}
                                window.close();
                            </script>
                        </head>
                        <body></body>
                        </html>
                    """)
            
            # Create new user if trust level check passes
            api_key = generate_api_key()
            create_user(api_key=api_key, username=username, linuxdo_token=access_token)
            user = get_user(api_key=api_key)
        else:
            # Update existing user's token
            update_linuxdo_token(user[0], access_token)
            api_key = user[1]

        # Handle disabled users as normal flow
        if not user[4]:  # user[4] is enabled status
            logger.warning(f"Disabled user attempted to login: {username}")
            error_message = f"用户已被禁用：{user[5]}" if user[5] else "用户已被禁用"
            return HTMLResponse(f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <title>登录失败</title>
                    <script>
                        if (window.opener) {{
                            window.opener.postMessage({{"error": "{error_message}"}}, window.location.origin);
                        }}
                        window.close();
                    </script>
                </head>
                <body></body>
                </html>
            """)

        # Get admin status using their OAuth token
        admin_status = is_admin(access_token)

        res = {
            "apiKey": api_key,
            "oauth_token": access_token,
            "admin": admin_status
        }

        return HTMLResponse(f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>登录成功</title>
                <script>
                    if (window.opener) {{
                        window.opener.postMessage({json.dumps(res)}, window.location.origin);
                    }}
                    window.close();
                </script>
            </head>
            <body></body>
            </html>
        """)

    except Exception as e:
        # Only handle actual errors here
        logger.error(f"OAuth authorization failed: {str(e)}")
        error_res = {"error": str(e)}
        return HTMLResponse(f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>登录失败</title>
                <script>
                    if (window.opener) {{
                        window.opener.postMessage({json.dumps(error_res)}, window.location.origin);
                    }}
                    window.close();
                </script>
            </head>
            <body></body>
            </html>
        """)