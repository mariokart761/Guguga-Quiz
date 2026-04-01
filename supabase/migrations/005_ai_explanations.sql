-- ============================================================
-- Guguga Quiz - Schema Migration 005
-- AI 詳解快取表
-- ============================================================

CREATE TABLE quiz.question_explanations (
  id                    uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  question_id           uuid        NOT NULL REFERENCES quiz.questions(id) ON DELETE CASCADE,
  prompt_version        text        NOT NULL DEFAULT 'v1',
  model_provider        text        NOT NULL DEFAULT 'openai',
  model_name            text        NOT NULL,
  language              text        NOT NULL DEFAULT 'zh-TW',

  question_content_hash text        NOT NULL,
  prompt_input          jsonb       NOT NULL DEFAULT '{}',
  explanation_text      text        NOT NULL DEFAULT '',
  explanation_json      jsonb,

  status                text        NOT NULL DEFAULT 'completed'
                        CHECK (status IN ('pending', 'completed', 'failed')),
  token_input           integer,
  token_output          integer,
  cost_estimate         numeric(12,6),

  created_at            timestamptz NOT NULL DEFAULT now(),
  updated_at            timestamptz NOT NULL DEFAULT now(),

  UNIQUE (question_id, prompt_version, model_provider, model_name, language, question_content_hash)
);

-- 常用查詢索引
CREATE INDEX idx_question_explanations_question_id
  ON quiz.question_explanations(question_id);

CREATE INDEX idx_question_explanations_status
  ON quiz.question_explanations(status);

-- updated_at 自動更新 trigger
CREATE TRIGGER question_explanations_updated_at
  BEFORE UPDATE ON quiz.question_explanations
  FOR EACH ROW EXECUTE FUNCTION quiz.update_updated_at();

-- ============================================================
-- RLS Policies
-- ============================================================

ALTER TABLE quiz.question_explanations ENABLE ROW LEVEL SECURITY;

-- 已登入使用者可以讀取詳解快取
CREATE POLICY "Authenticated users can read explanations"
  ON quiz.question_explanations
  FOR SELECT
  TO authenticated
  USING (true);

-- 前端不允許直接寫入（透過 Edge Function + service role 寫入）
-- 不建立 INSERT / UPDATE / DELETE policy，讓 RLS 預設阻擋

-- 授予 authenticated role SELECT 權限
GRANT SELECT ON quiz.question_explanations TO authenticated;
