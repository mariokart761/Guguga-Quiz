-- ============================================================
-- Guguga Quiz - Migration 004
-- 授予 quiz schema 的存取權限給 Supabase 內建角色
--
-- 重要：PostgreSQL 建立 schema 後，預設 anon/authenticated 角色
-- 沒有 USAGE 權限，必須明確 GRANT。
-- RLS policies 負責行級別的存取控管，GRANT 只是允許「進門」。
-- ============================================================

-- 授予 schema 使用權
GRANT USAGE ON SCHEMA quiz TO anon, authenticated, service_role;
GRANT USAGE ON SCHEMA quiz_private TO service_role;

-- 授予所有現有資料表的操作權限
-- RLS policies 會在 row 層級再進行管控
GRANT SELECT ON ALL TABLES IN SCHEMA quiz TO anon, authenticated;
GRANT INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA quiz TO authenticated;
GRANT ALL ON ALL TABLES IN SCHEMA quiz TO service_role;
GRANT ALL ON ALL TABLES IN SCHEMA quiz_private TO service_role;

-- 授予 sequence 使用權（uuid 不需要，但若有 serial 欄位則需要）
GRANT USAGE ON ALL SEQUENCES IN SCHEMA quiz TO authenticated;
GRANT ALL ON ALL SEQUENCES IN SCHEMA quiz_private TO service_role;

-- 設定未來新增資料表的預設權限
ALTER DEFAULT PRIVILEGES IN SCHEMA quiz
  GRANT SELECT ON TABLES TO anon, authenticated;

ALTER DEFAULT PRIVILEGES IN SCHEMA quiz
  GRANT INSERT, UPDATE, DELETE ON TABLES TO authenticated;

ALTER DEFAULT PRIVILEGES IN SCHEMA quiz
  GRANT ALL ON TABLES TO service_role;

ALTER DEFAULT PRIVILEGES IN SCHEMA quiz_private
  GRANT ALL ON TABLES TO service_role;
