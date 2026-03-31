from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID
from datetime import datetime


# ============================================================
# Paper schemas
# ============================================================

class PaperCreate(BaseModel):
    title: str
    source_type: str = "html_import"
    exam_year: Optional[int] = None
    term: Optional[str] = None
    subject: Optional[str] = None
    description: Optional[str] = None
    is_published: bool = False


class PaperUpdate(BaseModel):
    title: Optional[str] = None
    exam_year: Optional[int] = None
    term: Optional[str] = None
    subject: Optional[str] = None
    description: Optional[str] = None
    total_questions: Optional[int] = None
    is_published: Optional[bool] = None


class PaperResponse(BaseModel):
    id: UUID
    title: str
    source_type: str
    exam_year: Optional[int]
    term: Optional[str]
    subject: Optional[str]
    description: Optional[str]
    total_questions: int
    is_published: bool
    created_by: Optional[UUID]
    created_at: datetime
    updated_at: datetime


# ============================================================
# Question schemas
# ============================================================

class QuestionOptionCreate(BaseModel):
    option_key: str
    option_html: str
    option_text: Optional[str] = None
    sort_order: int = 0
    is_correct: bool = False


class QuestionCreate(BaseModel):
    paper_id: UUID
    group_id: Optional[UUID] = None
    question_no: int
    question_type: str = "single"
    stem_html: str
    stem_text: Optional[str] = None
    explanation_html: Optional[str] = None
    difficulty: Optional[str] = None
    source_answer_raw: Optional[str] = None
    options: list[QuestionOptionCreate] = []


class QuestionUpdate(BaseModel):
    group_id: Optional[UUID] = None
    question_type: Optional[str] = None
    stem_html: Optional[str] = None
    stem_text: Optional[str] = None
    explanation_html: Optional[str] = None
    difficulty: Optional[str] = None
    source_answer_raw: Optional[str] = None


# ============================================================
# Import schemas
# ============================================================

class ImportJobCreate(BaseModel):
    source_file_path: str


class ImportJobResponse(BaseModel):
    id: UUID
    uploaded_by: UUID
    source_file_path: str
    status: str
    paper_id: Optional[UUID]
    error_message: Optional[str]
    created_at: datetime
    updated_at: datetime


class PublishImportRequest(BaseModel):
    job_id: UUID
    paper_meta: dict


# ============================================================
# Group schemas
# ============================================================

class QuestionGroupCreate(BaseModel):
    paper_id: UUID
    group_no: int
    intro_html: Optional[str] = None
    intro_text: Optional[str] = None
    image_path: Optional[str] = None
    start_no: Optional[int] = None
    end_no: Optional[int] = None
