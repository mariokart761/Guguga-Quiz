// @deprecated: v1已不再使用，僅供參考。v2 版已經改用多模態（文字+圖片）。
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'

const CORS_HEADERS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
  'Access-Control-Allow-Methods': 'POST, OPTIONS',
}

const PROMPT_VERSION = 'v1'
const MODEL_PROVIDER = 'openai'
const MODEL_NAME = 'gpt-4o-mini'
const ALLOWED_LANGUAGES = ['zh-TW', 'en']

function jsonResponse(data: unknown, status = 200): Response {
  return new Response(JSON.stringify(data), {
    status,
    headers: { ...CORS_HEADERS, 'Content-Type': 'application/json' },
  })
}

async function sha256Hex(input: string): Promise<string> {
  const buffer = await crypto.subtle.digest(
    'SHA-256',
    new TextEncoder().encode(input),
  )
  return [...new Uint8Array(buffer)]
    .map((b) => b.toString(16).padStart(2, '0'))
    .join('')
}

Deno.serve(async (req) => {
  if (req.method === 'OPTIONS') {
    return new Response(null, { headers: CORS_HEADERS })
  }

  if (req.method !== 'POST') {
    return jsonResponse({ error: 'Method not allowed' }, 405)
  }

  // ── 驗證使用者身份 ─────────────────────────────────────────
  const authHeader = req.headers.get('Authorization')
  if (!authHeader) {
    return jsonResponse({ error: 'Unauthorized' }, 401)
  }

  const userClient = createClient(
    Deno.env.get('SUPABASE_URL')!,
    Deno.env.get('SUPABASE_ANON_KEY')!,
    { global: { headers: { Authorization: authHeader } } },
  )

  const { data: { user }, error: authError } = await userClient.auth.getUser()
  if (authError || !user) {
    return jsonResponse({ error: 'Unauthorized' }, 401)
  }

  // ── 解析並驗證 request body（白名單參數）─────────────────
  let body: Record<string, unknown>
  try {
    body = await req.json()
  } catch {
    return jsonResponse({ error: 'Invalid JSON body' }, 400)
  }

  const questionId = body.question_id
  const language = (body.language as string) ?? 'zh-TW'

  if (!questionId || typeof questionId !== 'string') {
    return jsonResponse({ error: 'question_id is required' }, 400)
  }
  if (!ALLOWED_LANGUAGES.includes(language)) {
    return jsonResponse({ error: `language must be one of: ${ALLOWED_LANGUAGES.join(', ')}` }, 400)
  }

  // ── 使用 service role client 查詢資料庫 ───────────────────
  const adminClient = createClient(
    Deno.env.get('SUPABASE_URL')!,
    Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!,
  )

  const { data: question, error: qError } = await adminClient
    .schema('quiz')
    .from('questions')
    .select('id, stem_text, stem_html, explanation_html, question_type, difficulty, question_options(option_key, option_text, option_html, sort_order, is_correct)')
    .eq('id', questionId)
    .single()

  if (qError || !question) {
    return jsonResponse({ error: 'Question not found' }, 404)
  }

  const options: Array<{ option_key: string; option_text: string | null; sort_order: number; is_correct: boolean }> =
    [...(question.question_options as any[])].sort((a, b) => a.sort_order - b.sort_order)

  const correctKeys = options.filter((o) => o.is_correct).map((o) => o.option_key)

  // ── 計算 question_content_hash ────────────────────────────
  const promptInput = {
    stem: question.stem_text ?? '',
    options: options.map((o) => `${o.option_key}. ${o.option_text ?? ''}`),
    correct_answers: correctKeys.sort(),
    question_type: question.question_type ?? 'single',
    language,
    prompt_version: PROMPT_VERSION,
  }
  const contentHash = await sha256Hex(JSON.stringify(promptInput))

  // ── 查快取 ────────────────────────────────────────────────
  const { data: cached } = await adminClient
    .schema('quiz')
    .from('question_explanations')
    .select('explanation_text')
    .eq('question_id', questionId)
    .eq('prompt_version', PROMPT_VERSION)
    .eq('model_provider', MODEL_PROVIDER)
    .eq('model_name', MODEL_NAME)
    .eq('language', language)
    .eq('question_content_hash', contentHash)
    .eq('status', 'completed')
    .maybeSingle()

  if (cached?.explanation_text) {
    return jsonResponse({ explanation: cached.explanation_text, cached: true })
  }

  // ── 呼叫 OpenAI ───────────────────────────────────────────
  const openaiKey = Deno.env.get('GUGUGA_OPENAI_API_KEY')
  if (!openaiKey) {
    return jsonResponse({ error: 'AI service not configured' }, 503)
  }

  const isTw = language === 'zh-TW'

  const systemPrompt = isTw
    ? `你是一個專業的教學助理，協助學生理解測驗題目。
請根據提供的題目、選項與正確答案，撰寫清楚、深入且適合學生閱讀的詳解。
詳解應包含：
1. 正確答案的完整說明（為什麼這個答案是對的）
2. 錯誤選項的辨析（說明為什麼其他選項不正確）
3. 相關知識點的補充說明
請用繁體中文回應，語氣親切、條理清晰。不要重複題目原文，直接提供深入的解析。`
    : `You are a professional educational assistant helping students understand quiz questions.
Based on the question, options, and correct answer provided, write a clear and insightful explanation.
Include: 1. Why the correct answer is right, 2. Why other options are incorrect, 3. Key concepts to remember.
Be concise and student-friendly.`

  const optionLines = options.map((o) => `${o.option_key}. ${o.option_text ?? ''}`)
  const existingExplanation = question.explanation_html
    ? `\n\n參考解析：${(question.explanation_html as string).replace(/<[^>]*>/g, '')}`
    : ''

  const userPrompt = isTw
    ? `題目：${question.stem_text ?? ''}
選項：
${optionLines.join('\n')}
正確答案：${correctKeys.join('、')}${existingExplanation}

請提供完整詳解。`
    : `Question: ${question.stem_text ?? ''}
Options:
${optionLines.join('\n')}
Correct answer: ${correctKeys.join(', ')}${existingExplanation}

Please provide a complete explanation.`

  let openaiRes: Response
  try {
    openaiRes = await fetch('https://api.openai.com/v1/chat/completions', {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${openaiKey}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        model: MODEL_NAME,
        messages: [
          { role: 'system', content: systemPrompt },
          { role: 'user', content: userPrompt },
        ],
        temperature: 0.3,
        max_tokens: 1200,
      }),
    })
  } catch (e) {
    console.error('OpenAI fetch error:', e)
    return jsonResponse({ error: 'AI service unavailable' }, 502)
  }

  if (!openaiRes.ok) {
    const errText = await openaiRes.text()
    console.error('OpenAI error response:', errText)
    return jsonResponse({ error: 'AI service error' }, 502)
  }

  const openaiData = await openaiRes.json()
  const explanationText: string = openaiData.choices?.[0]?.message?.content ?? ''
  const tokenInput: number | null = openaiData.usage?.prompt_tokens ?? null
  const tokenOutput: number | null = openaiData.usage?.completion_tokens ?? null

  if (!explanationText) {
    return jsonResponse({ error: 'Empty response from AI' }, 502)
  }

  // ── 存入快取（upsert 防止重複寫入）────────────────────────
  const { error: upsertError } = await adminClient
    .schema('quiz')
    .from('question_explanations')
    .upsert(
      {
        question_id: questionId,
        prompt_version: PROMPT_VERSION,
        model_provider: MODEL_PROVIDER,
        model_name: MODEL_NAME,
        language,
        question_content_hash: contentHash,
        prompt_input: promptInput,
        explanation_text: explanationText,
        status: 'completed',
        token_input: tokenInput,
        token_output: tokenOutput,
      },
      {
        onConflict: 'question_id,prompt_version,model_provider,model_name,language,question_content_hash',
      },
    )

  if (upsertError) {
    console.error('Cache upsert error:', upsertError)
    // 即使快取寫入失敗，仍回傳結果給使用者
  }

  return jsonResponse({ explanation: explanationText, cached: false })
})
