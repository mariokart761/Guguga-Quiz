-- ============================================================
-- Guguga Quiz - Storage Buckets Migration 003
-- 建立 Storage buckets（需要 service_role 或在 Dashboard 手動建立）
-- ============================================================

-- 注意：Storage bucket 通常在 Supabase Dashboard 建立，
-- 或透過 Storage API。以下是使用 SQL 建立的方式（需要 service_role）。

INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES
  (
    'quiz-assets',
    'quiz-assets',
    false,
    10485760,  -- 10MB
    ARRAY['image/jpeg', 'image/png', 'image/gif', 'image/webp', 'image/svg+xml']
  ),
  (
    'quiz-imports',
    'quiz-imports',
    false,
    52428800,  -- 50MB
    ARRAY[
      'text/html',
      'application/zip',
      'application/x-zip-compressed',
      'application/json',
      'text/markdown',
      'text/x-markdown'
    ]
  )
ON CONFLICT (id) DO NOTHING;
