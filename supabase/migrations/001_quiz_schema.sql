-- ============================================================
-- Guguga Quiz - Schema Migration 001
-- 建立 quiz 與 quiz_private 兩個 schema 及所有核心資料表
-- ============================================================

-- 建立自訂 schema
CREATE SCHEMA IF NOT EXISTS quiz;
CREATE SCHEMA IF NOT EXISTS quiz_private;

-- ============================================================
-- QUIZ SCHEMA：公開資料表
-- ============================================================

-- 使用者角色
CREATE TABLE quiz.user_roles (
  user_id              uuid PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  role                 text NOT NULL DEFAULT 'member' CHECK (role IN ('admin', 'member')),
  can_manage_questions boolean NOT NULL DEFAULT false,
  created_at           timestamptz NOT NULL DEFAULT now()
);

-- 試卷主表
CREATE TABLE quiz.papers (
  id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  title            text NOT NULL,
  source_type      text NOT NULL DEFAULT 'html_import',
  exam_year        int,
  term             text,
  subject          text,
  description      text,
  total_questions  int NOT NULL DEFAULT 0,
  is_published     boolean NOT NULL DEFAULT false,
  created_by       uuid REFERENCES auth.users(id),
  created_at       timestamptz NOT NULL DEFAULT now(),
  updated_at       timestamptz NOT NULL DEFAULT now()
);

-- 題組
CREATE TABLE quiz.question_groups (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  paper_id    uuid NOT NULL REFERENCES quiz.papers(id) ON DELETE CASCADE,
  group_no    int NOT NULL,
  intro_html  text,
  intro_text  text,
  image_path  text,
  start_no    int,
  end_no      int,
  created_at  timestamptz NOT NULL DEFAULT now()
);

-- 題目
CREATE TABLE quiz.questions (
  id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  paper_id          uuid NOT NULL REFERENCES quiz.papers(id) ON DELETE CASCADE,
  group_id          uuid REFERENCES quiz.question_groups(id) ON DELETE SET NULL,
  question_no       int NOT NULL,
  question_type     text NOT NULL DEFAULT 'single' CHECK (question_type IN ('single', 'multiple')),
  stem_html         text NOT NULL,
  stem_text         text,
  explanation_html  text,
  difficulty        text CHECK (difficulty IN ('easy', 'medium', 'hard')),
  source_answer_raw text,
  created_at        timestamptz NOT NULL DEFAULT now(),
  updated_at        timestamptz NOT NULL DEFAULT now()
);

-- 選項
CREATE TABLE quiz.question_options (
  id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  question_id  uuid NOT NULL REFERENCES quiz.questions(id) ON DELETE CASCADE,
  option_key   text NOT NULL,
  option_html  text NOT NULL,
  option_text  text,
  sort_order   int NOT NULL DEFAULT 0,
  is_correct   boolean NOT NULL DEFAULT false
);

-- 題目圖片資源
CREATE TABLE quiz.question_assets (
  id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  question_id  uuid REFERENCES quiz.questions(id) ON DELETE CASCADE,
  group_id     uuid REFERENCES quiz.question_groups(id) ON DELETE CASCADE,
  asset_type   text NOT NULL DEFAULT 'image',
  bucket_name  text NOT NULL DEFAULT 'quiz-assets',
  object_path  text NOT NULL,
  source_url   text,
  created_at   timestamptz NOT NULL DEFAULT now(),
  CHECK (question_id IS NOT NULL OR group_id IS NOT NULL)
);

-- 作答批次
CREATE TABLE quiz.attempts (
  id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id          uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  paper_id         uuid NOT NULL REFERENCES quiz.papers(id) ON DELETE CASCADE,
  mode             text NOT NULL CHECK (mode IN ('practice', 'mock_exam', 'wrong_review')),
  started_at       timestamptz NOT NULL DEFAULT now(),
  submitted_at     timestamptz,
  score            numeric,
  correct_count    int NOT NULL DEFAULT 0,
  wrong_count      int NOT NULL DEFAULT 0,
  duration_seconds int
);

-- 每題作答
CREATE TABLE quiz.attempt_answers (
  id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  attempt_id       uuid NOT NULL REFERENCES quiz.attempts(id) ON DELETE CASCADE,
  question_id      uuid NOT NULL REFERENCES quiz.questions(id) ON DELETE CASCADE,
  selected_answers jsonb NOT NULL DEFAULT '[]',
  is_correct       boolean NOT NULL DEFAULT false,
  answered_at      timestamptz NOT NULL DEFAULT now()
);

-- 收藏題
CREATE TABLE quiz.bookmarks (
  user_id     uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  question_id uuid NOT NULL REFERENCES quiz.questions(id) ON DELETE CASCADE,
  created_at  timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (user_id, question_id)
);

-- 錯題統計
CREATE TABLE quiz.wrong_question_stats (
  user_id         uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  question_id     uuid NOT NULL REFERENCES quiz.questions(id) ON DELETE CASCADE,
  wrong_count     int NOT NULL DEFAULT 1,
  last_wrong_at   timestamptz NOT NULL DEFAULT now(),
  last_correct_at timestamptz,
  PRIMARY KEY (user_id, question_id)
);

-- ============================================================
-- QUIZ_PRIVATE SCHEMA：內部處理資料表
-- ============================================================

-- 匯入任務
CREATE TABLE quiz_private.import_jobs (
  id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  uploaded_by      uuid NOT NULL REFERENCES auth.users(id),
  source_file_path text NOT NULL,
  status           text NOT NULL DEFAULT 'pending'
                   CHECK (status IN ('pending', 'processing', 'review', 'published', 'failed')),
  paper_id         uuid,
  error_message    text,
  created_at       timestamptz NOT NULL DEFAULT now(),
  updated_at       timestamptz NOT NULL DEFAULT now()
);

-- 原始匯入內容
CREATE TABLE quiz_private.import_raw_items (
  id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  import_job_id    uuid NOT NULL REFERENCES quiz_private.import_jobs(id) ON DELETE CASCADE,
  item_type        text NOT NULL CHECK (item_type IN ('paper_meta', 'group', 'question', 'option')),
  raw_html         text,
  normalized_json  jsonb,
  created_at       timestamptz NOT NULL DEFAULT now()
);

-- ============================================================
-- 索引
-- ============================================================

CREATE INDEX idx_questions_paper_id ON quiz.questions(paper_id);
CREATE INDEX idx_questions_group_id ON quiz.questions(group_id);
CREATE INDEX idx_question_options_question_id ON quiz.question_options(question_id);
CREATE INDEX idx_attempts_user_id ON quiz.attempts(user_id);
CREATE INDEX idx_attempts_paper_id ON quiz.attempts(paper_id);
CREATE INDEX idx_attempt_answers_attempt_id ON quiz.attempt_answers(attempt_id);
CREATE INDEX idx_attempt_answers_question_id ON quiz.attempt_answers(question_id);
CREATE INDEX idx_wrong_stats_user_id ON quiz.wrong_question_stats(user_id);
CREATE INDEX idx_import_raw_items_job_id ON quiz_private.import_raw_items(import_job_id);

-- ============================================================
-- updated_at 自動更新 trigger
-- ============================================================

CREATE OR REPLACE FUNCTION quiz.update_updated_at()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$;

CREATE TRIGGER papers_updated_at
  BEFORE UPDATE ON quiz.papers
  FOR EACH ROW EXECUTE FUNCTION quiz.update_updated_at();

CREATE TRIGGER questions_updated_at
  BEFORE UPDATE ON quiz.questions
  FOR EACH ROW EXECUTE FUNCTION quiz.update_updated_at();

CREATE OR REPLACE FUNCTION quiz_private.update_updated_at()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$;

CREATE TRIGGER import_jobs_updated_at
  BEFORE UPDATE ON quiz_private.import_jobs
  FOR EACH ROW EXECUTE FUNCTION quiz_private.update_updated_at();
