-- ============================================================
-- Guguga Quiz - RLS Policies Migration 002
-- 所有 quiz schema exposed 表都必須啟用 RLS
-- ============================================================

-- ============================================================
-- 輔助函式：判斷是否為 quiz admin
-- ============================================================

CREATE OR REPLACE FUNCTION quiz.is_quiz_admin(uid uuid DEFAULT auth.uid())
RETURNS boolean
LANGUAGE sql SECURITY DEFINER STABLE AS $$
  SELECT EXISTS (
    SELECT 1 FROM quiz.user_roles
    WHERE user_id = uid
      AND role = 'admin'
  );
$$;

CREATE OR REPLACE FUNCTION quiz.can_manage_questions(uid uuid DEFAULT auth.uid())
RETURNS boolean
LANGUAGE sql SECURITY DEFINER STABLE AS $$
  SELECT EXISTS (
    SELECT 1 FROM quiz.user_roles
    WHERE user_id = uid
      AND (role = 'admin' OR can_manage_questions = true)
  );
$$;

-- ============================================================
-- quiz.user_roles RLS
-- ============================================================

ALTER TABLE quiz.user_roles ENABLE ROW LEVEL SECURITY;

CREATE POLICY "使用者可讀自己的角色"
  ON quiz.user_roles FOR SELECT
  USING (user_id = auth.uid());

CREATE POLICY "admin 可讀所有角色"
  ON quiz.user_roles FOR SELECT
  USING (quiz.is_quiz_admin());

CREATE POLICY "admin 可管理角色"
  ON quiz.user_roles FOR ALL
  USING (quiz.is_quiz_admin());

-- ============================================================
-- quiz.papers RLS
-- ============================================================

ALTER TABLE quiz.papers ENABLE ROW LEVEL SECURITY;

CREATE POLICY "已登入使用者可讀已發布試卷"
  ON quiz.papers FOR SELECT
  USING (is_published = true AND auth.role() = 'authenticated');

CREATE POLICY "admin 可讀所有試卷"
  ON quiz.papers FOR SELECT
  USING (quiz.is_quiz_admin());

CREATE POLICY "有管理權限者可新增試卷"
  ON quiz.papers FOR INSERT
  WITH CHECK (quiz.can_manage_questions());

CREATE POLICY "有管理權限者可更新試卷"
  ON quiz.papers FOR UPDATE
  USING (quiz.can_manage_questions());

CREATE POLICY "admin 可刪除試卷"
  ON quiz.papers FOR DELETE
  USING (quiz.is_quiz_admin());

-- ============================================================
-- quiz.question_groups RLS
-- ============================================================

ALTER TABLE quiz.question_groups ENABLE ROW LEVEL SECURITY;

CREATE POLICY "已登入使用者可讀已發布試卷的題組"
  ON quiz.question_groups FOR SELECT
  USING (
    auth.role() = 'authenticated' AND
    EXISTS (
      SELECT 1 FROM quiz.papers
      WHERE id = paper_id AND is_published = true
    )
  );

CREATE POLICY "admin 可讀所有題組"
  ON quiz.question_groups FOR SELECT
  USING (quiz.is_quiz_admin());

CREATE POLICY "有管理權限者可管理題組"
  ON quiz.question_groups FOR ALL
  USING (quiz.can_manage_questions());

-- ============================================================
-- quiz.questions RLS
-- ============================================================

ALTER TABLE quiz.questions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "已登入使用者可讀已發布試卷的題目"
  ON quiz.questions FOR SELECT
  USING (
    auth.role() = 'authenticated' AND
    EXISTS (
      SELECT 1 FROM quiz.papers
      WHERE id = paper_id AND is_published = true
    )
  );

CREATE POLICY "admin 可讀所有題目"
  ON quiz.questions FOR SELECT
  USING (quiz.is_quiz_admin());

CREATE POLICY "有管理權限者可管理題目"
  ON quiz.questions FOR ALL
  USING (quiz.can_manage_questions());

-- ============================================================
-- quiz.question_options RLS
-- ============================================================

ALTER TABLE quiz.question_options ENABLE ROW LEVEL SECURITY;

CREATE POLICY "已登入使用者可讀已發布試卷的選項"
  ON quiz.question_options FOR SELECT
  USING (
    auth.role() = 'authenticated' AND
    EXISTS (
      SELECT 1 FROM quiz.questions q
      JOIN quiz.papers p ON p.id = q.paper_id
      WHERE q.id = question_id AND p.is_published = true
    )
  );

CREATE POLICY "admin 可讀所有選項"
  ON quiz.question_options FOR SELECT
  USING (quiz.is_quiz_admin());

CREATE POLICY "有管理權限者可管理選項"
  ON quiz.question_options FOR ALL
  USING (quiz.can_manage_questions());

-- ============================================================
-- quiz.question_assets RLS
-- ============================================================

ALTER TABLE quiz.question_assets ENABLE ROW LEVEL SECURITY;

CREATE POLICY "已登入使用者可讀資源"
  ON quiz.question_assets FOR SELECT
  USING (auth.role() = 'authenticated');

CREATE POLICY "有管理權限者可管理資源"
  ON quiz.question_assets FOR ALL
  USING (quiz.can_manage_questions());

-- ============================================================
-- quiz.attempts RLS
-- ============================================================

ALTER TABLE quiz.attempts ENABLE ROW LEVEL SECURITY;

CREATE POLICY "使用者只能讀自己的作答批次"
  ON quiz.attempts FOR SELECT
  USING (user_id = auth.uid());

CREATE POLICY "使用者可建立自己的作答批次"
  ON quiz.attempts FOR INSERT
  WITH CHECK (user_id = auth.uid());

CREATE POLICY "使用者可更新自己的作答批次"
  ON quiz.attempts FOR UPDATE
  USING (user_id = auth.uid());

CREATE POLICY "admin 可讀所有作答批次"
  ON quiz.attempts FOR SELECT
  USING (quiz.is_quiz_admin());

-- ============================================================
-- quiz.attempt_answers RLS
-- ============================================================

ALTER TABLE quiz.attempt_answers ENABLE ROW LEVEL SECURITY;

CREATE POLICY "使用者只能讀自己的作答明細"
  ON quiz.attempt_answers FOR SELECT
  USING (
    EXISTS (
      SELECT 1 FROM quiz.attempts
      WHERE id = attempt_id AND user_id = auth.uid()
    )
  );

CREATE POLICY "使用者可建立自己的作答明細"
  ON quiz.attempt_answers FOR INSERT
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM quiz.attempts
      WHERE id = attempt_id AND user_id = auth.uid()
    )
  );

-- ============================================================
-- quiz.bookmarks RLS
-- ============================================================

ALTER TABLE quiz.bookmarks ENABLE ROW LEVEL SECURITY;

CREATE POLICY "使用者只能讀自己的收藏"
  ON quiz.bookmarks FOR SELECT
  USING (user_id = auth.uid());

CREATE POLICY "使用者可管理自己的收藏"
  ON quiz.bookmarks FOR ALL
  USING (user_id = auth.uid());

-- ============================================================
-- quiz.wrong_question_stats RLS
-- ============================================================

ALTER TABLE quiz.wrong_question_stats ENABLE ROW LEVEL SECURITY;

CREATE POLICY "使用者只能讀自己的錯題統計"
  ON quiz.wrong_question_stats FOR SELECT
  USING (user_id = auth.uid());

CREATE POLICY "使用者可管理自己的錯題統計"
  ON quiz.wrong_question_stats FOR ALL
  USING (user_id = auth.uid());

-- ============================================================
-- Storage RLS policies（需要在 Supabase Dashboard 建立 buckets 後執行）
-- ============================================================

-- quiz-assets：已登入使用者可讀，admin 可寫
CREATE POLICY "已登入使用者可讀 quiz-assets"
  ON storage.objects FOR SELECT
  USING (
    bucket_id = 'quiz-assets' AND
    auth.role() = 'authenticated'
  );

CREATE POLICY "admin 可上傳至 quiz-assets"
  ON storage.objects FOR INSERT
  WITH CHECK (
    bucket_id = 'quiz-assets' AND
    quiz.is_quiz_admin()
  );

CREATE POLICY "admin 可更新 quiz-assets"
  ON storage.objects FOR UPDATE
  USING (
    bucket_id = 'quiz-assets' AND
    quiz.is_quiz_admin()
  );

CREATE POLICY "admin 可刪除 quiz-assets"
  ON storage.objects FOR DELETE
  USING (
    bucket_id = 'quiz-assets' AND
    quiz.is_quiz_admin()
  );

-- quiz-imports：只有 admin 可存取
CREATE POLICY "admin 可讀寫 quiz-imports"
  ON storage.objects FOR ALL
  USING (
    bucket_id = 'quiz-imports' AND
    quiz.is_quiz_admin()
  );

-- ============================================================
-- 讓前端可以使用 quiz schema（在 Supabase Dashboard 的 API 設定中加入）
-- 或執行以下 SQL：
-- ALTER ROLE authenticator SET search_path = public, quiz;
-- ============================================================

-- ============================================================
-- 自動新增使用者角色（當新使用者透過 Auth 註冊時）
-- ============================================================

CREATE OR REPLACE FUNCTION quiz.handle_new_user()
RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER AS $$
BEGIN
  INSERT INTO quiz.user_roles (user_id, role, can_manage_questions)
  VALUES (NEW.id, 'member', false)
  ON CONFLICT (user_id) DO NOTHING;
  RETURN NEW;
END;
$$;

CREATE OR REPLACE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION quiz.handle_new_user();

-- ============================================================
-- 更新錯題統計的 function（當作答完成時呼叫）
-- ============================================================

CREATE OR REPLACE FUNCTION quiz.upsert_wrong_stat(
  p_user_id    uuid,
  p_question_id uuid,
  p_is_correct  boolean
)
RETURNS void LANGUAGE plpgsql SECURITY DEFINER AS $$
BEGIN
  IF p_is_correct THEN
    UPDATE quiz.wrong_question_stats
    SET last_correct_at = now()
    WHERE user_id = p_user_id AND question_id = p_question_id;
  ELSE
    INSERT INTO quiz.wrong_question_stats (user_id, question_id, wrong_count, last_wrong_at)
    VALUES (p_user_id, p_question_id, 1, now())
    ON CONFLICT (user_id, question_id) DO UPDATE
    SET wrong_count   = quiz.wrong_question_stats.wrong_count + 1,
        last_wrong_at = now();
  END IF;
END;
$$;
