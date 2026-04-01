<script setup lang="ts">
definePageMeta({ middleware: 'auth' })

const route = useRoute()
const quizStore = useQuizStore()
const authStore = useAuthStore()
const supabase = useSupabaseClient()

const attemptId = route.params.attemptId as string

// 載入 attempt 資料
const { data: attempt } = await useAsyncData('attempt', async () => {
  const { data } = await supabase
    .schema('quiz')
    .from('attempts')
    .select('*, papers(*)')
    .eq('id', attemptId)
    .single()
  return data
})

if (!attempt.value || attempt.value.user_id !== authStore.user?.id) {
  throw createError({ statusCode: 404 })
}

// wrong_review 模式題目可能跨多試卷，SSR 先略過，onMounted 依 IDs 載入
// practice / mock_exam 模式依 paper_id 載入全部題目
const { data: rawQuestions } = await useAsyncData('attempt-questions', async () => {
  if (attempt.value?.mode === 'wrong_review') return []
  const { data } = await supabase
    .schema('quiz')
    .from('questions')
    .select('*, question_options(*), question_assets(*)')
    .eq('paper_id', attempt.value!.paper_id)
    .order('question_no')
  return data
})

// ── 題組導言 & 圖片 ───────────────────────────────────────────────────────────
// 以 group_id 為 key：{ intro_html, imageUrls[] }
const groupDataMap = ref<Record<string, { intro_html: string; imageUrls: string[] }>>({})

async function signedUrl(bucket: string, path: string): Promise<string | null> {
  const { data } = await supabase.storage.from(bucket).createSignedUrl(path, 3600)
  return data?.signedUrl ?? null
}

async function loadGroupsAndImages(questions: any[]) {
  // 載入題組（從題目的 group_id 反查 question_groups）
  const groupIds = [...new Set(
    questions.map((q: any) => q.group_id).filter(Boolean),
  )] as string[]

  if (!groupIds.length) return

  const { data: groups } = await supabase
    .schema('quiz')
    .from('question_groups')
    .select('id, intro_html, question_assets(*)')
    .in('id', groupIds)

  if (!groups) return

  for (const g of groups as any[]) {
    const assets: any[] = g.question_assets ?? []
    const imageUrls: string[] = []
    for (const a of assets) {
      const url = await signedUrl(a.bucket_name, a.object_path)
      if (url) imageUrls.push(url)
    }
    groupDataMap.value[g.id] = { intro_html: g.intro_html ?? '', imageUrls }
  }
}

onMounted(async () => {
  if (attempt.value?.mode === 'wrong_review') {
    const stored = sessionStorage.getItem(`attempt_qids_${attemptId}`)
    if (!stored) return
    const ids = JSON.parse(stored) as string[]
    if (!ids.length) return
    const { data } = await supabase
      .schema('quiz')
      .from('questions')
      .select('*, question_options(*), question_assets(*)')
      .in('id', ids)
      .order('question_no')
    rawQuestions.value = data
    if (data) await loadGroupsAndImages(data)
  } else if (rawQuestions.value?.length) {
    await loadGroupsAndImages(rawQuestions.value as any[])
  }
})

// 練習模式：依 sessionStorage 或 Pinia store 中記錄的 IDs 篩題
// 模擬考模式：使用全部題目；wrong_review：直接用 rawQuestions（已依 ID 載入）
const allQuestions = computed(() => {
  const all = rawQuestions.value ?? []

  if (attempt.value?.mode === 'wrong_review') return all
  if (attempt.value?.mode !== 'practice') return all

  // 優先從 sessionStorage 讀取（支援重新整理後恢復）
  if (import.meta.client) {
    const stored = sessionStorage.getItem(`attempt_qids_${attemptId}`)
    if (stored) {
      const selectedIds = new Set(JSON.parse(stored) as string[])
      const filtered = all.filter((q: any) => selectedIds.has(q.id))
      if (filtered.length > 0) return filtered
    }
  }

  // 降級：從 Pinia store 讀取（同 session 但未重新整理）
  const storeIds = quizStore.currentQuestions.map((q) => q.id)
  if (storeIds.length > 0) {
    const selectedIds = new Set(storeIds)
    const filtered = all.filter((q: any) => selectedIds.has(q.id))
    if (filtered.length > 0) return filtered
  }

  return all
})
const isMockExam = computed(() => attempt.value?.mode === 'mock_exam')

// 練習模式：目前題目索引
const currentIndex = ref(0)
const currentQuestion = computed(() => allQuestions.value[currentIndex.value])

// 記錄每題作答
const answers = ref<Record<string, string[]>>({})
const revealed = ref<Set<string>>(new Set())
const bookmarks = ref<Set<string>>(new Set())

// 模擬考：跳題 navigation
const jumpTo = ref<number | null>(null)

// 計時器（模擬考用）
const examDuration = computed(() => Math.ceil(allQuestions.value.length * 1.5) * 60)
const examExpired = ref(false)

async function handleSelect(questionId: string, key: string, type: 'single' | 'multiple') {
  if (isMockExam.value && examExpired.value) return
  if (!isMockExam.value && revealed.value.has(questionId)) return

  const current = answers.value[questionId] ?? []

  if (type === 'single') {
    answers.value[questionId] = [key]
  } else {
    if (current.includes(key)) {
      answers.value[questionId] = current.filter((k) => k !== key)
    } else {
      answers.value[questionId] = [...current, key]
    }
  }
}

async function revealAnswer(questionId: string) {
  if (!answers.value[questionId]?.length) return
  revealed.value.add(questionId)

  // 寫入作答紀錄
  const q = allQuestions.value.find((x) => x.id === questionId)
  if (!q) return
  const correctKeys = q.question_options.filter((o: any) => o.is_correct).map((o: any) => o.option_key)
  await quizStore.submitAnswer(attemptId, questionId, answers.value[questionId], correctKeys)
}

async function nextQuestion() {
  if (currentIndex.value < allQuestions.value.length - 1) {
    currentIndex.value += 1
  }
}

async function prevQuestion() {
  if (currentIndex.value > 0) {
    currentIndex.value -= 1
  }
}

async function submitExam() {
  // 批次寫入尚未透過 revealAnswer 提交的答題（已 revealed 的在確認答案時已寫入，不重複 insert）
  for (const q of allQuestions.value) {
    if (answers.value[q.id]?.length && !revealed.value.has(q.id)) {
      const correctKeys = q.question_options.filter((o: any) => o.is_correct).map((o: any) => o.option_key)
      await quizStore.submitAnswer(attemptId, q.id, answers.value[q.id], correctKeys)
    }
  }
  await quizStore.submitAttempt(attemptId)
  await navigateTo(`/result/${attemptId}`)
}

async function toggleBookmark(questionId: string) {
  if (!authStore.user) return
  const isNowBookmarked = await quizStore.toggleBookmark(authStore.user.id, questionId)
  if (isNowBookmarked) {
    bookmarks.value.add(questionId)
  } else {
    bookmarks.value.delete(questionId)
  }
}

// 進度
const answeredCount = computed(() =>
  allQuestions.value.filter((q: any) => answers.value[q.id]?.length > 0).length
)

// 目前題目所屬題組資料
const currentGroup = computed(() => {
  const gId = (currentQuestion.value as any)?.group_id
  return gId ? (groupDataMap.value[gId] ?? null) : null
})

// intro_html 去除 <img> 標籤（圖片統一由 question_assets signed URL 顯示，避免重複）
function stripImgTags(html: string): string {
  if (!html) return html
  return html.replace(/<img[^>]*\/?>/gi, '')
}

// 取題組純文字（供複製功能使用）
function groupIntroPlainText(html: string): string {
  if (!html) return ''
  if (import.meta.client) {
    const doc = new DOMParser().parseFromString(html, 'text/html')
    return doc.body.textContent?.trim() ?? ''
  }
  return html.replace(/<[^>]*>/g, '').trim()
}

// 目前題目對應的題組純文字（傳給 QuestionCard）
const currentGroupIntroText = computed(() => {
  if (!currentGroup.value?.intro_html) return null
  return groupIntroPlainText(currentGroup.value.intro_html) || null
})

</script>

<template>
  <div class="max-w-3xl mx-auto px-4 py-6">
    <!-- 頂部資訊列 -->
    <div class="flex items-center justify-between mb-6">
      <div>
        <h1 class="text-lg font-bold text-gray-900">
          {{ (attempt as any)?.papers?.title }}
        </h1>
        <p class="text-sm text-gray-500">
          {{ isMockExam ? '模擬考模式' : attempt?.mode === 'wrong_review' ? '錯題練習模式' : '練習模式' }}
          · {{ answeredCount }} / {{ allQuestions.length }} 題已作答
        </p>
      </div>

      <!-- 倒數計時（模擬考） -->
      <div class="flex items-center gap-3">
        <CountdownTimer
          v-if="isMockExam"
          :total-seconds="examDuration"
          @expired="examExpired = true; submitExam()"
        />
        <button
          v-if="isMockExam"
          class="bg-orange-500 text-white text-sm font-medium px-4 py-2 rounded-lg hover:bg-orange-600 transition-colors"
          @click="submitExam"
        >
          交卷
        </button>
      </div>
    </div>

    <!-- 模擬考：題號快速導航 -->
    <div v-if="isMockExam" class="bg-white border border-gray-200 rounded-xl p-4 mb-6">
      <div class="text-xs text-gray-500 mb-2">題號快速跳轉</div>
      <div class="flex flex-wrap gap-1.5">
        <button
          v-for="(q, idx) in allQuestions"
          :key="q.id"
          class="w-8 h-8 rounded text-xs font-medium transition-colors"
          :class="{
            'bg-primary-600 text-white': idx === currentIndex,
            'bg-green-100 text-green-700': answers[q.id]?.length > 0 && idx !== currentIndex,
            'bg-gray-100 text-gray-500 hover:bg-gray-200': !answers[q.id]?.length && idx !== currentIndex,
          }"
          @click="currentIndex = idx"
        >
          {{ q.question_no }}
        </button>
      </div>
    </div>

    <!-- 題組導言 -->
    <Transition
      enter-active-class="transition-all duration-300 ease-out"
      enter-from-class="opacity-0 -translate-y-2"
      enter-to-class="opacity-100 translate-y-0"
    >
      <div
        v-if="currentGroup"
        class="bg-amber-50 border border-amber-200 rounded-xl p-5 mb-4"
      >
        <div class="text-xs font-semibold text-amber-700 mb-2 flex items-center gap-1">
          <span>📋</span> 題組說明
        </div>
        <!-- 題組圖片（signed URL from question_assets） -->
        <div v-if="currentGroup.imageUrls.length > 0" class="mb-3 flex flex-col gap-2">
          <img
            v-for="(url, i) in currentGroup.imageUrls"
            :key="i"
            :src="url"
            class="max-w-full rounded-lg border border-amber-100"
            loading="lazy"
          >
        </div>
        <!-- 題組導言 HTML（img 標籤已移除，圖片由上方 signed URL 顯示） -->
        <div
          v-if="stripImgTags(currentGroup.intro_html)"
          class="prose prose-sm max-w-none text-gray-700"
          v-html="stripImgTags(currentGroup.intro_html)"
        />
      </div>
    </Transition>

    <!-- 題目卡片 -->
    <QuestionCard
      v-if="currentQuestion"
      :question="currentQuestion"
      :show-answer="!isMockExam && revealed.has(currentQuestion.id)"
      :selected-answers="answers[currentQuestion.id] ?? []"
      :bookmarked="bookmarks.has(currentQuestion.id)"
      :mode="attempt?.mode as any"
      :group-intro-text="currentGroupIntroText"
      @select="(key) => handleSelect(currentQuestion.id, key, currentQuestion.question_type)"
      @toggle-bookmark="toggleBookmark(currentQuestion.id)"
    />

    <!-- 練習模式操作列 -->
    <div v-if="!isMockExam" class="mt-4 flex items-center justify-between gap-3">
      <button
        :disabled="currentIndex === 0"
        class="px-4 py-2.5 text-sm font-medium border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed"
        @click="prevQuestion"
      >
        ← 上一題
      </button>

      <div class="flex gap-2">
        <button
          v-if="!revealed.has(currentQuestion?.id ?? '') && answers[currentQuestion?.id ?? '']?.length > 0"
          class="px-4 py-2.5 text-sm font-medium bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors"
          @click="revealAnswer(currentQuestion.id)"
        >
          確認答案
        </button>
        <button
          v-if="revealed.has(currentQuestion?.id ?? '') || !answers[currentQuestion?.id ?? '']?.length"
          :disabled="currentIndex === allQuestions.length - 1"
          class="px-4 py-2.5 text-sm font-medium bg-gray-800 text-white rounded-lg hover:bg-gray-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          @click="nextQuestion"
        >
          下一題 →
        </button>
      </div>

      <div class="text-sm text-gray-400">
        {{ currentIndex + 1 }} / {{ allQuestions.length }}
      </div>
    </div>

    <!-- 練習模式最後一題 -->
    <div
      v-if="!isMockExam && currentIndex === allQuestions.length - 1 && revealed.has(currentQuestion?.id ?? '')"
      class="mt-6 text-center"
    >
      <p class="text-gray-600 mb-4">已完成全部題目！</p>
      <button
        class="bg-primary-600 text-white font-medium px-6 py-3 rounded-xl hover:bg-primary-700 transition-colors"
        @click="submitExam"
      >
        查看結果
      </button>
    </div>
  </div>
</template>
