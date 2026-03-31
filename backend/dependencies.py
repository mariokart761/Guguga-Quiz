from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from supabase import create_client, Client
from config import settings

bearer_scheme = HTTPBearer()

def get_supabase_admin() -> Client:
    """回傳使用 service_role 的 Supabase client（後端專用）"""
    return create_client(settings.supabase_url, settings.supabase_service_role_key)


def get_supabase_anon() -> Client:
    """回傳使用 anon key 的 Supabase client（驗證 JWT 用）"""
    return create_client(settings.supabase_url, settings.supabase_anon_key)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    supabase: Client = Depends(get_supabase_anon),
) -> dict:
    """從 Authorization Bearer token 取得目前使用者"""
    token = credentials.credentials
    try:
        response = supabase.auth.get_user(token)
        if response.user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
            )
        return {"id": response.user.id, "email": response.user.email}
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )


async def get_current_admin(
    current_user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_admin),
) -> dict:
    """確認目前使用者具有 quiz admin 角色"""
    result = (
        supabase.schema("quiz")
        .table("user_roles")
        .select("role")
        .eq("user_id", current_user["id"])
        .single()
        .execute()
    )
    if not result.data or result.data.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user
