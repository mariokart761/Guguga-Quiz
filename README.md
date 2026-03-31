# Guguga Quiz 線上測驗平台

可自行快速搭建的測驗平台，可拓展多種格式試卷匯入。

## 技術架構

| 層級 | 技術 |
|------|------|
| 前端 | Nuxt 3 + Vue 3 + Pinia + Tailwind CSS |
| 後端 | FastAPI (Python) |
| 資料庫 / Auth / Storage | Supabase |
| 前端部署 | Vercel |
| 後端部署 | Railway / Render |

## 專案結構

```
Guguga Quiz/
├── frontend/          # Nuxt 3 前端
├── backend/           # FastAPI 後端
├── supabase/
│   └── migrations/    # SQL 資料庫 migrations
└── README.md
```

## 快速開始

### 1. Supabase 設定

1. 在 [Supabase Dashboard](https://supabase.com) 建立或選擇現有 project
2. 依序執行 migrations：
   ```sql
   -- 在 SQL Editor 中執行（需 service_role）
   -- 001_quiz_schema.sql
   -- 002_rls_policies.sql
   -- 003_storage_buckets.sql
   -- ...
   ```
3. 在 Dashboard > API Settings 中，將 `quiz` 加入 **Exposed schemas**
4. 建立 Storage buckets（若 003 migration 失敗，請在 Dashboard > Storage 手動建立）：
   - `quiz-assets`（private）
   - `quiz-imports`（private）

### 2. 設定第一個 Admin

在 SQL Editor 中執行：
```sql
-- 將 user_id 換成你的 auth.users.id
UPDATE quiz.user_roles
SET role = 'admin', can_manage_questions = true
WHERE user_id = 'your-user-uuid-here';
```

### 3. 後端啟動

```bash
cd backend
cp .env.example .env
# 填入 .env 中的 SUPABASE_URL 和 SUPABASE_SERVICE_ROLE_KEY

pip install -r requirements.txt
uvicorn main:app --reload
```

### 4. 前端啟動

```bash
cd frontend
cp .env.example .env
# 填入 .env 中的 SUPABASE_URL 和 SUPABASE_ANON_KEY

npm install
npm run dev
```

前端預設在 `http://localhost:3000`，後端在 `http://localhost:8000`。

---

## 功能說明

### 使用者端

| 功能 | 路徑 |
|------|------|
| 登入（Email OTP / Google） | `/login` |
| 試卷列表 | `/papers` |
| 試卷詳情 + 選擇模式 | `/papers/[id]` |
| 練習 / 模擬考作答 | `/practice/[attemptId]` |
| 作答結果 | `/result/[attemptId]` |
| 錯題本 | `/wrong-book` |
| 收藏題目 | `/bookmarks` |
| 個人資料 / 成績 | `/profile` |

### 後台（Admin）

| 功能 | 路徑 |
|------|------|
| 後台首頁 | `/admin` |
| 上傳 HTML 試卷 | `/admin/imports` |
| 匯入預覽 / 發布 | `/admin/imports/[jobId]` |
| 試卷管理 | `/admin/papers` |
| 題目編輯 | `/admin/questions` |

### 後端 API

| 方法 | 路徑 | 說明 |
|------|------|------|
| POST | `/api/imports/upload` | 上傳 HTML 試卷 |
| GET | `/api/imports` | 取得匯入任務列表 |
| GET | `/api/imports/{id}` | 取得任務詳情與預覽 |
| POST | `/api/imports/{id}/process` | 重新觸發解析 |
| POST | `/api/imports/{id}/publish` | 發布到正式題庫 |
| GET | `/api/papers` | 取得試卷列表 |
| POST | `/api/papers/{id}/publish` | 發布試卷 |
| GET | `/api/questions` | 取得題目列表 |
| PATCH | `/api/questions/{id}` | 編輯題目 |

---

## 資料庫 Schema

### `quiz` schema（前端可存取）
- `user_roles` — 使用者角色
- `papers` — 試卷
- `question_groups` — 題組
- `questions` — 題目
- `question_options` — 選項
- `question_assets` — 圖片資源
- `attempts` — 作答批次
- `attempt_answers` — 每題作答紀錄
- `bookmarks` — 收藏
- `wrong_question_stats` — 錯題統計

### `quiz_private` schema（僅後端）
- `import_jobs` — 匯入任務
- `import_raw_items` — 原始解析暫存

---

## 部署

### 前端（Vercel）

```bash
cd frontend
# 在 Vercel Dashboard 設定環境變數：
# SUPABASE_URL, SUPABASE_ANON_KEY, NUXT_PUBLIC_API_BASE
```

### 後端（Railway / Render）

```bash
cd backend
# 設定環境變數：
# SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, ALLOWED_ORIGINS
# 啟動命令：uvicorn main:app --host 0.0.0.0 --port $PORT
```

---

## HTML 試卷格式說明

匯入器支援常見的台灣考試 HTML 格式：

- 題號以 `1.`、`1、`、`1．` 等形式開頭
- 選項以 `(A)`、`A.`、`Ａ.` 等形式開頭
- 答案區塊包含「答案」、「解答」等關鍵字
- 年份以民國或西元標注
- 圖片支援外部 URL（匯入時自動下載至 Storage）
