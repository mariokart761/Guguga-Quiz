"""
題目管理路由（後台）
GET    /questions               - 列出題目
GET    /questions/{id}          - 取得單一題目
PATCH  /questions/{id}          - 更新題目
DELETE /questions/{id}          - 刪除題目
POST   /questions/{id}/options  - 更新選項
"""

from fastapi import APIRouter, Depends, HTTPException
from supabase import Client

from dependencies import get_supabase_admin, get_current_admin
from models.schemas import QuestionUpdate, QuestionOptionCreate

router = APIRouter(prefix="/questions", tags=["questions"])


@router.get("")
async def list_questions(
    paper_id: str | None = None,
    current_admin: dict = Depends(get_current_admin),
    supabase: Client = Depends(get_supabase_admin),
):
    query = (
        supabase.schema("quiz").table("questions")
        .select("*, question_options(*)")
        .order("question_no")
    )
    if paper_id:
        query = query.eq("paper_id", paper_id)
    result = query.execute()
    return result.data


@router.get("/{question_id}")
async def get_question(
    question_id: str,
    current_admin: dict = Depends(get_current_admin),
    supabase: Client = Depends(get_supabase_admin),
):
    result = (
        supabase.schema("quiz").table("questions")
        .select("*, question_options(*), question_assets(*)")
        .eq("id", question_id)
        .single()
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Question not found")
    return result.data


@router.patch("/{question_id}")
async def update_question(
    question_id: str,
    body: QuestionUpdate,
    current_admin: dict = Depends(get_current_admin),
    supabase: Client = Depends(get_supabase_admin),
):
    update_data = body.model_dump(exclude_none=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")

    # group_id 要轉成 str
    if "group_id" in update_data and update_data["group_id"] is not None:
        update_data["group_id"] = str(update_data["group_id"])

    result = (
        supabase.schema("quiz").table("questions")
        .update(update_data)
        .eq("id", question_id)
        .execute()
    )
    return result.data[0] if result.data else {"message": "Updated"}


@router.put("/{question_id}/options")
async def replace_options(
    question_id: str,
    options: list[QuestionOptionCreate],
    current_admin: dict = Depends(get_current_admin),
    supabase: Client = Depends(get_supabase_admin),
):
    """完整取代題目的選項"""
    # 刪除舊選項
    supabase.schema("quiz").table("question_options").delete().eq(
        "question_id", question_id
    ).execute()

    # 建立新選項
    if options:
        new_opts = [
            {
                "question_id": question_id,
                "option_key": o.option_key,
                "option_html": o.option_html,
                "option_text": o.option_text,
                "sort_order": o.sort_order,
                "is_correct": o.is_correct,
            }
            for o in options
        ]
        supabase.schema("quiz").table("question_options").insert(new_opts).execute()

    return {"message": "Options updated"}


@router.delete("/{question_id}")
async def delete_question(
    question_id: str,
    current_admin: dict = Depends(get_current_admin),
    supabase: Client = Depends(get_supabase_admin),
):
    supabase.schema("quiz").table("questions").delete().eq("id", question_id).execute()
    return {"message": "Deleted"}
