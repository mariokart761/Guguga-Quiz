"""
匯入管理路由

POST /imports/upload         - 上傳 HTML 試卷
POST /imports/upload-json    - 上傳 JSON 試卷（yamol_parser 格式）
GET  /imports                - 取得匯入任務列表
GET  /imports/{job_id}       - 取得單一任務詳情
POST /imports/{job_id}/process - 觸發解析
POST /imports/{job_id}/publish - 發布到正式題庫
DELETE /imports/{job_id}     - 刪除任務
"""

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from supabase import Client
from postgrest.exceptions import APIError

from dependencies import get_supabase_admin, get_current_admin
from services.html_parser import parse_quiz_html, ParsedPaper
from services.json_parser import parse_quiz_json
from services.storage_service import upload_import_file, download_and_upload_image


router = APIRouter(prefix="/imports", tags=["imports"])


# ── 工具 ──────────────────────────────────────────────────────────────────────


def _raise_if_schema_error(e: Exception):
    if isinstance(e, APIError):
        if "PGRST106" in str(e) or "schema must be one of" in str(e):
            raise HTTPException(
                status_code=500,
                detail=(
                    "quiz_private schema 尚未加入 Supabase Exposed Schemas。"
                    "請前往 Dashboard → Project Settings → API → Exposed schemas，加入 quiz_private。"
                ),
            )
    raise HTTPException(status_code=500, detail=str(e))


# ── 背景任務：解析 ─────────────────────────────────────────────────────────────


async def _process_import_job(job_id: str, supabase: Client):
    """背景任務：解析匯入的試卷（HTML 或 JSON）"""
    try:
        supabase.schema("quiz_private").table("import_jobs").update(
            {"status": "processing"}
        ).eq("id", job_id).execute()

        job = (
            supabase.schema("quiz_private").table("import_jobs")
            .select("*").eq("id", job_id).single().execute()
        ).data
        if not job:
            return

        file_bytes = supabase.storage.from_("quiz-imports").download(
            job["source_file_path"]
        )
        content = file_bytes.decode("utf-8", errors="replace")

        # 依副檔名選擇解析器
        suffix = Path(job["source_file_path"]).suffix.lower()
        if suffix == ".json":
            paper = parse_quiz_json(content)
        else:
            paper = parse_quiz_html(content)

        # 清除舊的 raw_items
        supabase.schema("quiz_private").table("import_raw_items").delete().eq(
            "import_job_id", job_id
        ).execute()

        # paper_meta
        supabase.schema("quiz_private").table("import_raw_items").insert({
            "import_job_id": job_id,
            "item_type": "paper_meta",
            "normalized_json": {
                "title": paper.title,
                "subject": paper.subject,
                "exam_year": paper.exam_year,
                "term": paper.term,
                "total_questions": len(paper.questions),
            },
        }).execute()

        # 題組
        for g in paper.groups:
            uploaded_images = []
            for idx, img_url in enumerate(g.image_urls):
                if img_url.startswith("http"):
                    path = await download_and_upload_image(
                        supabase, img_url, job_id, f"group{g.group_no}", idx
                    )
                    if path:
                        uploaded_images.append({"original": img_url, "path": path})

            supabase.schema("quiz_private").table("import_raw_items").insert({
                "import_job_id": job_id,
                "item_type": "group",
                "raw_html": g.intro_html,
                "normalized_json": {
                    "group_no": g.group_no,
                    "intro_html": g.intro_html,
                    "intro_text": g.intro_text,
                    "start_no": g.start_no,
                    "end_no": g.end_no,
                    "images": uploaded_images,
                },
            }).execute()

        # 題目
        for q in paper.questions:
            uploaded_images = []
            for idx, img_url in enumerate(q.image_urls):
                if img_url.startswith("http"):
                    path = await download_and_upload_image(
                        supabase, img_url, job_id, f"q{q.question_no}", idx
                    )
                    if path:
                        uploaded_images.append({"original": img_url, "path": path})

            supabase.schema("quiz_private").table("import_raw_items").insert({
                "import_job_id": job_id,
                "item_type": "question",
                "raw_html": q.stem_html,
                "normalized_json": {
                    "question_no": q.question_no,
                    "question_type": q.question_type,
                    "stem_html": q.stem_html,
                    "stem_text": q.stem_text,
                    "group_ref": q.group_ref,        # 題組編號（group_no）
                    "options": [
                        {"key": o.key, "html": o.html, "text": o.text}
                        for o in q.options
                    ],
                    "answer_raw": paper.answers.get(q.question_no, ""),
                    "images": uploaded_images,
                },
            }).execute()

        supabase.schema("quiz_private").table("import_jobs").update(
            {"status": "review"}
        ).eq("id", job_id).execute()

    except Exception as e:
        supabase.schema("quiz_private").table("import_jobs").update(
            {"status": "failed", "error_message": str(e)[:500]}
        ).eq("id", job_id).execute()


# ── 上傳端點 ──────────────────────────────────────────────────────────────────


@router.post("/upload")
async def upload_import(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    auto_process: bool = True,
    current_admin: dict = Depends(get_current_admin),
    supabase: Client = Depends(get_supabase_admin),
):
    """上傳 HTML 試卷，建立匯入任務"""
    if not file.filename or not file.filename.lower().endswith(".html"):
        raise HTTPException(status_code=400, detail="只接受 .html 檔案")

    file_bytes = await file.read()
    if len(file_bytes) > 50 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="檔案過大（上限 50MB）")

    return await _create_import_job(
        supabase, file_bytes, file.filename, current_admin["id"],
        background_tasks, auto_process
    )


@router.post("/upload-json")
async def upload_import_json(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    auto_process: bool = True,
    current_admin: dict = Depends(get_current_admin),
    supabase: Client = Depends(get_supabase_admin),
):
    """上傳 JSON 試卷（yamol_parser schema_version 1.0.0），建立匯入任務"""
    if not file.filename or not file.filename.lower().endswith(".json"):
        raise HTTPException(status_code=400, detail="只接受 .json 檔案")

    file_bytes = await file.read()
    if len(file_bytes) > 50 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="檔案過大（上限 50MB）")

    return await _create_import_job(
        supabase, file_bytes, file.filename, current_admin["id"],
        background_tasks, auto_process
    )


async def _create_import_job(
    supabase: Client,
    file_bytes: bytes,
    filename: str,
    user_id: str,
    background_tasks: BackgroundTasks,
    auto_process: bool,
) -> dict:
    try:
        object_path = await upload_import_file(supabase, file_bytes, filename, user_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Storage 上傳失敗：{e}")

    try:
        job = supabase.schema("quiz_private").table("import_jobs").insert({
            "uploaded_by": user_id,
            "source_file_path": object_path,
            "status": "pending",
        }).execute()
    except Exception as e:
        _raise_if_schema_error(e)

    job_id = job.data[0]["id"]

    if auto_process:
        background_tasks.add_task(_process_import_job, job_id, supabase)

    return {"job_id": job_id, "status": "pending", "message": "上傳成功"}


# ── 查詢端點 ──────────────────────────────────────────────────────────────────


@router.get("")
async def list_imports(
    current_admin: dict = Depends(get_current_admin),
    supabase: Client = Depends(get_supabase_admin),
):
    try:
        result = (
            supabase.schema("quiz_private").table("import_jobs")
            .select("*").order("created_at", desc=True).limit(50).execute()
        )
        return result.data
    except Exception as e:
        _raise_if_schema_error(e)


@router.get("/{job_id}")
async def get_import_job(
    job_id: str,
    current_admin: dict = Depends(get_current_admin),
    supabase: Client = Depends(get_supabase_admin),
):
    try:
        job = (
            supabase.schema("quiz_private").table("import_jobs")
            .select("*").eq("id", job_id).single().execute()
        )
        if not job.data:
            raise HTTPException(status_code=404, detail="Job not found")

        items = (
            supabase.schema("quiz_private").table("import_raw_items")
            .select("*").eq("import_job_id", job_id).order("created_at").execute()
        )
        return {"job": job.data, "items": items.data}
    except HTTPException:
        raise
    except Exception as e:
        _raise_if_schema_error(e)


# ── 操作端點 ──────────────────────────────────────────────────────────────────


@router.post("/{job_id}/process")
async def trigger_process(
    job_id: str,
    background_tasks: BackgroundTasks,
    current_admin: dict = Depends(get_current_admin),
    supabase: Client = Depends(get_supabase_admin),
):
    try:
        job = (
            supabase.schema("quiz_private").table("import_jobs")
            .select("status").eq("id", job_id).single().execute()
        )
    except Exception as e:
        _raise_if_schema_error(e)

    if not job.data:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.data["status"] == "published":
        raise HTTPException(status_code=400, detail="Already published")

    background_tasks.add_task(_process_import_job, job_id, supabase)
    return {"message": "Processing started"}


@router.post("/{job_id}/publish")
async def publish_import(
    job_id: str,
    current_admin: dict = Depends(get_current_admin),
    supabase: Client = Depends(get_supabase_admin),
):
    """將解析結果發布到正式 quiz schema，包含題組與圖片"""
    try:
        job = (
            supabase.schema("quiz_private").table("import_jobs")
            .select("*").eq("id", job_id).single().execute()
        )
        if not job.data:
            raise HTTPException(status_code=404, detail="Job not found")
        if job.data["status"] != "review":
            raise HTTPException(status_code=400, detail="Job must be in 'review' status to publish")

        items = (
            supabase.schema("quiz_private").table("import_raw_items")
            .select("*").eq("import_job_id", job_id).execute()
        )
    except HTTPException:
        raise
    except Exception as e:
        _raise_if_schema_error(e)

    meta = next((i for i in items.data if i["item_type"] == "paper_meta"), None)
    if not meta:
        raise HTTPException(status_code=400, detail="No paper meta found in job")

    paper_meta = meta["normalized_json"]
    group_items = sorted(
        [i for i in items.data if i["item_type"] == "group"],
        key=lambda i: i["normalized_json"].get("group_no", 0),
    )
    question_items = sorted(
        [i for i in items.data if i["item_type"] == "question"],
        key=lambda i: i["normalized_json"].get("question_no", 0),
    )

    # ── 建立試卷 ──────────────────────────────────────────────────────────────
    paper_result = supabase.schema("quiz").table("papers").insert({
        "title": paper_meta.get("title", "未命名試卷"),
        "source_type": "html_import",
        "exam_year": paper_meta.get("exam_year"),
        "term": paper_meta.get("term"),
        "subject": paper_meta.get("subject"),
        "total_questions": len(question_items),
        "is_published": False,
        "created_by": current_admin["id"],
    }).execute()

    paper_id = paper_result.data[0]["id"]

    # ── 建立題組；group_no → uuid 對照表 ─────────────────────────────────────
    group_no_to_uuid: dict[int, str] = {}

    for item in group_items:
        g = item["normalized_json"]
        group_no: int = g.get("group_no", 0)

        group_result = supabase.schema("quiz").table("question_groups").insert({
            "paper_id": paper_id,
            "group_no": group_no,
            "intro_html": g.get("intro_html"),
            "intro_text": g.get("intro_text"),
            "start_no": g.get("start_no"),
            "end_no": g.get("end_no"),
        }).execute()

        group_uuid = group_result.data[0]["id"]
        group_no_to_uuid[group_no] = group_uuid

        # 題組圖片
        for img in g.get("images", []):
            if img.get("path"):
                supabase.schema("quiz").table("question_assets").insert({
                    "group_id": group_uuid,
                    "asset_type": "image",
                    "bucket_name": "quiz-assets",
                    "object_path": img["path"],
                    "source_url": img.get("original"),
                }).execute()

    # ── 建立題目 ──────────────────────────────────────────────────────────────
    for item in question_items:
        q = item["normalized_json"]

        group_ref: int | None = q.get("group_ref")
        group_uuid = group_no_to_uuid.get(group_ref) if group_ref else None

        q_result = supabase.schema("quiz").table("questions").insert({
            "paper_id": paper_id,
            "group_id": group_uuid,
            "question_no": q["question_no"],
            "question_type": q["question_type"],
            "stem_html": q["stem_html"],
            "stem_text": q.get("stem_text"),
            "source_answer_raw": q.get("answer_raw"),
        }).execute()

        question_uuid = q_result.data[0]["id"]

        # 選項
        answer_keys = set(q.get("answer_raw", "").upper().split(","))
        options_to_insert = [
            {
                "question_id": question_uuid,
                "option_key": opt["key"],
                "option_html": opt["html"],
                "option_text": opt.get("text"),
                "sort_order": idx,
                "is_correct": opt["key"] in answer_keys,
            }
            for idx, opt in enumerate(q.get("options", []))
        ]
        if options_to_insert:
            supabase.schema("quiz").table("question_options").insert(options_to_insert).execute()

        # 題目圖片
        for img in q.get("images", []):
            if img.get("path"):
                supabase.schema("quiz").table("question_assets").insert({
                    "question_id": question_uuid,
                    "asset_type": "image",
                    "bucket_name": "quiz-assets",
                    "object_path": img["path"],
                    "source_url": img.get("original"),
                }).execute()

    # ── 更新 import_job ────────────────────────────────────────────────────────
    supabase.schema("quiz_private").table("import_jobs").update({
        "status": "published",
        "paper_id": paper_id,
    }).eq("id", job_id).execute()

    return {
        "paper_id": paper_id,
        "groups_created": len(group_no_to_uuid),
        "questions_created": len(question_items),
        "message": "Published successfully",
    }


@router.delete("/{job_id}")
async def delete_import_job(
    job_id: str,
    current_admin: dict = Depends(get_current_admin),
    supabase: Client = Depends(get_supabase_admin),
):
    try:
        supabase.schema("quiz_private").table("import_jobs").delete().eq("id", job_id).execute()
    except Exception as e:
        _raise_if_schema_error(e)
    return {"message": "Deleted"}
