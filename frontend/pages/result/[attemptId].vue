<script setup lang="ts">
definePageMeta({ middleware: 'auth' })

const route = useRoute()
const supabase = useSupabaseClient()
const authStore = useAuthStore()
const quizStore = useQuizStore()

const attemptId = route.params.attemptId as string

const { data: attempt } = await useAsyncData('result-attempt', async () => {
  const { data } = await supabase
    .schema('quiz')
    .from('attempts')
    .select('*, papers(*)')
    .eq('id', attemptId)
    .single()
  return data
})

const { data: answers } = await useAsyncData('result-answers', async () => {
  const { data } = await supabase
    .schema('quiz')
    .from('attempt_answers')
    .select('*, questions(id, question_no, question_type, stem_html, stem_text, explanation_html, difficulty, question_options(*), question_assets(*))')
    .eq('attempt_id', attemptId)
    .order('questions(question_no)')
  return data
})

if (!attempt.value) {
  throw createError({ statusCode: 404 })
}

const wrongAnswers = computed(() =>
  (answers.value ?? []).filter((a: any) => !a.is_correct)
)

// 初始化收藏與錯題本狀態
const bookmarkedIds = ref<string[]>([])
const wrongBookIds = ref<string[]>([])

if (authStore.user && answers.value) {
  const wrongQIds = (answers.value as any[])
    .filter((a) => !a.is_correct)
    .map((a) => a.questions?.id)
    .filter(Boolean)

  if (wrongQIds.length > 0) {
    const [bResult, wResult] = await Promise.all([
      supabase.schema('quiz').from('bookmarks').select('question_id').eq('user_id', authStore.user.id).in('question_id', wrongQIds),
      supabase.schema('quiz').from('wrong_question_stats').select('question_id').eq('user_id', authStore.user.id).in('question_id', wrongQIds),
    ])
    bookmarkedIds.value = (bResult.data ?? []).map((b: any) => b.question_id)
    wrongBookIds.value = (wResult.data ?? []).map((w: any) => w.question_id)
  }
}

// 展開/收合狀態
const expandedIds = ref<string[]>([])
const isExpanded = (id: string) => expandedIds.value.includes(id)
function toggleExpand(id: string) {
  if (isExpanded(id)) expandedIds.value = expandedIds.value.filter((x) => x !== id)
  else expandedIds.value = [...expandedIds.value, id]
}

// 收藏 toggle
const bookmarkLoading = ref<string | null>(null)
async function toggleBookmark(questionId: string) {
  if (!authStore.user || bookmarkLoading.value) return
  bookmarkLoading.value = questionId
  try {
    const isNow = await quizStore.toggleBookmark(authStore.user.id, questionId)
    if (isNow) bookmarkedIds.value = [...bookmarkedIds.value, questionId]
    else bookmarkedIds.value = bookmarkedIds.value.filter((id) => id !== questionId)
  } finally {
    bookmarkLoading.value = null
  }
}

// 錯題本 toggle
const wrongBookLoading = ref<string | null>(null)
async function toggleWrongBook(questionId: string) {
  if (!authStore.user || wrongBookLoading.value) return
  wrongBookLoading.value = questionId
  try {
    const isNow = await quizStore.toggleWrongBook(authStore.user.id, questionId)
    if (isNow) wrongBookIds.value = [...wrongBookIds.value, questionId]
    else wrongBookIds.value = wrongBookIds.value.filter((id) => id !== questionId)
  } finally {
    wrongBookLoading.value = null
  }
}

// 清理題幹 HTML（移除嵌入的選項文字）
function cleanStemHtml(html: string): string {
  if (!html) return html
  const optionPat = /[\(（][A-Da-d][\)）]/
  if (import.meta.client) {
    const doc = new DOMParser().parseFromString(html, 'text/html')
    function stripOptions(node: Node): boolean {
      if (node.nodeType === Node.TEXT_NODE) {
        const text = node.textContent ?? ''
        const m = optionPat.exec(text)
        if (m) { node.textContent = text.slice(0, m.index); return true }
        return false
      }
      if (node.nodeType === Node.ELEMENT_NODE) {
        const children = Array.from(node.childNodes)
        for (let i = 0; i < children.length; i++) {
          if (stripOptions(children[i])) {
            for (let j = children.length - 1; j > i; j--) node.removeChild(children[j])
            return true
          }
        }
      }
      return false
    }
    stripOptions(doc.body)
    return doc.body.innerHTML
  }
  return html.replace(/[\(（][A-Da-d][\)）][\s\S]*$/, '')
}

// 選項樣式（展開檢視用）
function getOptionClass(optKey: string, selectedAnswers: string[], correctKeys: string[]) {
  const isSelected = selectedAnswers.includes(optKey)
  const isCorrect = correctKeys.includes(optKey)
  if (isCorrect) return 'border-green-400 bg-green-50 text-green-700'
  if (isSelected) return 'border-red-400 bg-red-50 text-red-700'
  return 'border-gray-200 text-gray-400'
}

function getSortedOptions(opts: any[]) {
  return [...(opts ?? [])].sort((a, b) => a.sort_order - b.sort_order)
}

const scorePercent = computed(() => attempt.value?.score ?? 0)

function scoreColor(score: number) {
  if (score >= 80) return 'text-green-600'
  if (score >= 60) return 'text-yellow-500'
  return 'text-red-500'
}
</script>

<template>
  <div class="max-w-3xl mx-auto px-4 py-8">
    <!-- 成績卡 -->
    <div class="bg-white rounded-2xl border border-gray-200 shadow-sm p-8 text-center mb-6">
      <div class="text-5xl mb-4">
        {{ scorePercent >= 80 ? '🎉' : scorePercent >= 60 ? '👍' : '📖' }}
      </div>
      <h1 class="text-xl font-bold text-gray-900 mb-2">
        {{ (attempt as any)?.papers?.title }}
      </h1>
      <p class="text-sm text-gray-500 mb-6">
        {{ attempt?.mode === 'mock_exam' ? '模擬考' : '練習' }} ·
        {{ new Date(attempt?.submitted_at ?? '').toLocaleString('zh-TW') }}
      </p>

      <!-- 分數 -->
      <div class="text-6xl font-bold mb-2" :class="scoreColor(scorePercent)">
        {{ scorePercent }}
        <span class="text-2xl text-gray-400">分</span>
      </div>

      <div class="flex justify-center gap-8 mt-6 text-center">
        <div>
          <div class="text-2xl font-bold text-green-600">{{ attempt?.correct_count }}</div>
          <div class="text-xs text-gray-500 mt-1">答對</div>
        </div>
        <div>
          <div class="text-2xl font-bold text-red-500">{{ attempt?.wrong_count }}</div>
          <div class="text-xs text-gray-500 mt-1">答錯</div>
        </div>
        <div v-if="attempt?.duration_seconds">
          <div class="text-2xl font-bold text-gray-700">
            {{ Math.floor((attempt.duration_seconds ?? 0) / 60) }}:{{ String((attempt.duration_seconds ?? 0) % 60).padStart(2, '0') }}
          </div>
          <div class="text-xs text-gray-500 mt-1">用時</div>
        </div>
      </div>

      <!-- 操作 -->
      <div class="flex justify-center gap-3 mt-8">
        <NuxtLink
          :to="`/papers/${attempt?.paper_id}`"
          class="px-5 py-2.5 border border-gray-300 rounded-lg text-sm font-medium hover:bg-gray-50 transition-colors"
        >
          回到試卷
        </NuxtLink>
        <NuxtLink
          to="/papers"
          class="px-5 py-2.5 bg-primary-600 text-white rounded-lg text-sm font-medium hover:bg-primary-700 transition-colors"
        >
          瀏覽題庫
        </NuxtLink>
      </div>
    </div>

    <!-- 答錯的題目 -->
    <div v-if="wrongAnswers.length > 0">
      <h2 class="text-lg font-semibold text-gray-800 mb-4">
        答錯的題目（{{ wrongAnswers.length }} 題）
      </h2>
      <div class="space-y-3">
        <div
          v-for="item in wrongAnswers"
          :key="item.id"
          class="bg-white rounded-xl border border-red-200 overflow-hidden"
        >
          <!-- 題目摘要列（可點擊展開） -->
          <div
            class="flex items-start gap-3 p-4 cursor-pointer hover:bg-red-50/50 transition-colors select-none"
            @click="toggleExpand(item.id)"
          >
            <!-- 題號 -->
            <span class="shrink-0 w-7 h-7 rounded-full bg-red-100 text-red-600 text-xs font-bold flex items-center justify-center mt-0.5">
              {{ (item as any).questions?.question_no }}
            </span>

            <!-- 題幹與作答摘要 -->
            <div class="flex-1 min-w-0">
              <p class="text-sm text-gray-700 mb-1.5 line-clamp-2">
                {{ (item as any).questions?.stem_text }}
              </p>
              <div class="flex flex-wrap gap-x-3 text-xs text-gray-500">
                <span>
                  你的答案：<span class="text-red-600 font-medium">{{ item.selected_answers?.join(', ') || '未作答' }}</span>
                </span>
                <span>·</span>
                <span>
                  正確答案：<span class="text-green-600 font-medium">
                    {{ (item as any).questions?.question_options?.filter((o: any) => o.is_correct).map((o: any) => o.option_key).join(', ') }}
                  </span>
                </span>
              </div>
            </div>

            <!-- 右側：操作按鈕 + 展開指示 -->
            <div class="shrink-0 flex items-center gap-1.5" @click.stop>
              <!-- 收藏 -->
              <button
                :title="bookmarkedIds.includes((item as any).questions?.id) ? '取消收藏' : '加入收藏'"
                :disabled="bookmarkLoading === (item as any).questions?.id"
                class="w-8 h-8 rounded-lg flex items-center justify-center text-base transition-colors"
                :class="bookmarkedIds.includes((item as any).questions?.id)
                  ? 'text-yellow-400 bg-yellow-50 hover:bg-yellow-100'
                  : 'text-gray-300 hover:text-yellow-400 hover:bg-yellow-50'"
                @click="toggleBookmark((item as any).questions?.id)"
              >
                {{ bookmarkedIds.includes((item as any).questions?.id) ? '★' : '☆' }}
              </button>
              <!-- 錯題本 -->
              <button
                :title="wrongBookIds.includes((item as any).questions?.id) ? '從錯題本移除' : '加入錯題本'"
                :disabled="wrongBookLoading === (item as any).questions?.id"
                class="w-8 h-8 rounded-lg flex items-center justify-center text-xs font-bold transition-colors"
                :class="wrongBookIds.includes((item as any).questions?.id)
                  ? 'text-red-500 bg-red-50 hover:bg-red-100'
                  : 'text-gray-300 hover:text-red-400 hover:bg-red-50'"
                @click="toggleWrongBook((item as any).questions?.id)"
              >
                錯
              </button>
            </div>

            <!-- 展開指示 -->
            <span
              class="shrink-0 text-gray-400 text-xs mt-1 transition-transform duration-200"
              :class="isExpanded(item.id) ? 'rotate-90' : ''"
            >
              ▶
            </span>
          </div>

          <!-- 展開的完整題目 -->
          <Transition
            enter-active-class="transition-all duration-200 ease-out"
            enter-from-class="opacity-0 -translate-y-1"
            enter-to-class="opacity-100 translate-y-0"
            leave-active-class="transition-all duration-150 ease-in"
            leave-from-class="opacity-100 translate-y-0"
            leave-to-class="opacity-0 -translate-y-1"
          >
            <div
              v-if="isExpanded(item.id)"
              class="border-t border-red-100 px-4 pb-4 pt-4 bg-gray-50/50"
            >
              <!-- 完整題幹 -->
              <div
                class="prose prose-sm max-w-none text-gray-800 mb-4"
                v-html="cleanStemHtml((item as any).questions?.stem_html ?? '')"
              />

              <!-- 選項列表 -->
              <div class="space-y-2 mb-4">
                <div
                  v-for="opt in getSortedOptions((item as any).questions?.question_options)"
                  :key="opt.id"
                  class="flex items-start gap-2 px-3 py-2.5 rounded-lg border-2 text-sm"
                  :class="getOptionClass(opt.option_key, item.selected_answers ?? [], (item as any).questions?.question_options?.filter((o: any) => o.is_correct).map((o: any) => o.option_key) ?? [])"
                >
                  <span class="font-bold shrink-0">{{ opt.option_key }}.</span>
                  <span class="flex-1" v-html="opt.option_html" />
                  <span v-if="(item as any).questions?.question_options?.filter((o: any) => o.is_correct).map((o: any) => o.option_key).includes(opt.option_key)" class="shrink-0 text-green-600 font-bold">✓</span>
                  <span v-else-if="(item.selected_answers ?? []).includes(opt.option_key)" class="shrink-0 text-red-500 font-bold">✗</span>
                </div>
              </div>

              <!-- 解析 -->
              <div
                v-if="(item as any).questions?.explanation_html"
                class="p-3 bg-blue-50 border border-blue-200 rounded-lg"
              >
                <div class="text-xs font-semibold text-blue-600 mb-1.5">解析</div>
                <div class="prose prose-sm max-w-none text-gray-700" v-html="(item as any).questions?.explanation_html" />
              </div>
            </div>
          </Transition>
        </div>
      </div>
    </div>
  </div>
</template>
