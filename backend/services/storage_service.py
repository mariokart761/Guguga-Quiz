"""
Supabase Storage 操作服務
負責上傳圖片、產生簽名 URL 等
"""

import httpx
import uuid
from pathlib import Path
from supabase import Client


QUIZ_ASSETS_BUCKET = "quiz-assets"
QUIZ_IMPORTS_BUCKET = "quiz-imports"


async def download_and_upload_image(
    supabase: Client,
    source_url: str,
    import_job_id: str,
    label: str,
    img_index: int,
) -> str | None:
    """
    下載外部圖片並上傳到 quiz-assets bucket。
    label 可以是 "q5"（第 5 題）或 "group1"（題組 1）等任意識別字串。
    回傳 Storage object path，失敗則回傳 None。
    """
    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            resp = await client.get(source_url)
            resp.raise_for_status()
            content = resp.content
            content_type = resp.headers.get("content-type", "image/jpeg")
    except Exception:
        return None

    ext = _guess_extension(content_type, source_url)
    object_path = f"imports/{import_job_id}/{label}_{img_index}{ext}"

    try:
        supabase.storage.from_(QUIZ_ASSETS_BUCKET).upload(
            path=object_path,
            file=content,
            file_options={"content-type": content_type},
        )
        return object_path
    except Exception:
        return None


def _guess_extension(content_type: str, url: str) -> str:
    mapping = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/gif": ".gif",
        "image/webp": ".webp",
        "image/svg+xml": ".svg",
    }
    if content_type in mapping:
        return mapping[content_type]
    suffix = Path(url.split("?")[0]).suffix
    return suffix if suffix else ".jpg"


def get_signed_url(supabase: Client, bucket: str, object_path: str, expires_in: int = 3600) -> str | None:
    """產生 signed URL，expires_in 單位為秒"""
    try:
        result = supabase.storage.from_(bucket).create_signed_url(object_path, expires_in)
        return result.get("signedURL")
    except Exception:
        return None


def _sanitize_filename(filename: str) -> str:
    """
    將檔名轉成 Supabase Storage 接受的 ASCII-only key。
    Supabase Storage 不接受中文、全形符號、空格等非 ASCII 字元。
    保留原始副檔名，其餘部分替換為 URL-safe 的 ASCII。
    """
    import re
    stem = Path(filename).stem
    suffix = Path(filename).suffix or ".html"
    # 只保留 ASCII 英數字、連字號、底線和點
    safe_stem = re.sub(r"[^\w\-]", "_", stem.encode("ascii", errors="ignore").decode())
    safe_stem = re.sub(r"_+", "_", safe_stem).strip("_") or "file"
    return f"{safe_stem}{suffix}"


async def upload_import_file(
    supabase: Client,
    file_bytes: bytes,
    filename: str,
    uploaded_by: str,
) -> str:
    """上傳試卷檔案（HTML 或 JSON）到 quiz-imports bucket，回傳 object path。
    object path 使用 UUID 避免中文/特殊字元造成的 InvalidKey 錯誤。
    """
    file_uuid = uuid.uuid4().hex
    safe_name = _sanitize_filename(filename)
    object_path = f"{uploaded_by}/{file_uuid}_{safe_name}"

    suffix = Path(filename).suffix.lower()
    content_type = "application/json" if suffix == ".json" else "text/html"

    supabase.storage.from_(QUIZ_IMPORTS_BUCKET).upload(
        path=object_path,
        file=file_bytes,
        file_options={"content-type": content_type},
    )
    return object_path
