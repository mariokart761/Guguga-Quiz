"""
試卷管理路由（後台）
GET    /papers              - 取得所有試卷
GET    /papers/{id}         - 取得單一試卷
PATCH  /papers/{id}         - 更新試卷資訊
DELETE /papers/{id}         - 刪除試卷
POST   /papers/{id}/publish - 發布試卷
"""

from fastapi import APIRouter, Depends, HTTPException
from supabase import Client

from dependencies import get_supabase_admin, get_current_admin
from models.schemas import PaperUpdate

router = APIRouter(prefix="/papers", tags=["papers"])


@router.get("")
async def list_papers(
    published_only: bool = False,
    current_admin: dict = Depends(get_current_admin),
    supabase: Client = Depends(get_supabase_admin),
):
    query = supabase.schema("quiz").table("papers").select("*").order("created_at", desc=True)
    if published_only:
        query = query.eq("is_published", True)
    result = query.execute()
    return result.data


@router.get("/{paper_id}")
async def get_paper(
    paper_id: str,
    current_admin: dict = Depends(get_current_admin),
    supabase: Client = Depends(get_supabase_admin),
):
    result = (
        supabase.schema("quiz").table("papers")
        .select("*, questions(*)")
        .eq("id", paper_id)
        .single()
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Paper not found")
    return result.data


@router.patch("/{paper_id}")
async def update_paper(
    paper_id: str,
    body: PaperUpdate,
    current_admin: dict = Depends(get_current_admin),
    supabase: Client = Depends(get_supabase_admin),
):
    update_data = body.model_dump(exclude_none=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")

    result = (
        supabase.schema("quiz").table("papers")
        .update(update_data)
        .eq("id", paper_id)
        .execute()
    )
    return result.data[0] if result.data else {"message": "Updated"}


@router.post("/{paper_id}/publish")
async def publish_paper(
    paper_id: str,
    current_admin: dict = Depends(get_current_admin),
    supabase: Client = Depends(get_supabase_admin),
):
    result = (
        supabase.schema("quiz").table("papers")
        .update({"is_published": True})
        .eq("id", paper_id)
        .execute()
    )
    return {"message": "Paper published", "paper_id": paper_id}


@router.post("/{paper_id}/unpublish")
async def unpublish_paper(
    paper_id: str,
    current_admin: dict = Depends(get_current_admin),
    supabase: Client = Depends(get_supabase_admin),
):
    supabase.schema("quiz").table("papers").update(
        {"is_published": False}
    ).eq("id", paper_id).execute()
    return {"message": "Paper unpublished", "paper_id": paper_id}


@router.delete("/{paper_id}")
async def delete_paper(
    paper_id: str,
    current_admin: dict = Depends(get_current_admin),
    supabase: Client = Depends(get_supabase_admin),
):
    supabase.schema("quiz").table("papers").delete().eq("id", paper_id).execute()
    return {"message": "Deleted"}
