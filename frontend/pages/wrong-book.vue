<script setup lang="ts">
import { useCopyQuestion } from '~/composables/useCopyQuestion'

definePageMeta({ middleware: 'auth' })

const quizStore = useQuizStore()
const authStore = useAuthStore()

const { data: wrongStats, refresh } = await useAsyncData('wrong-stats', async () => {
  if (!authStore.user) return []
  return quizStore.fetchWrongStats(authStore.user.id)
})

const stats = computed(() => wrongStats.value ?? [])

function formatDate(d: string | null) {
  if (!d) return '-'
  return new Date(d).toLocaleDateString('zh-TW')
}

// 考試來源標籤
function paperLabel(q: any): string {
  const p = q?.papers
  if (!p) return ''
  const parts: string[] = []
  if (p.exam_year) parts.push(`${p.exam_year} 年`)
  if (p.subject) parts.push(p.subject)
  if (p.title) parts.push(p.title)
  return parts.join(' · ')
}

const supabase = useSupabaseClient()

// 展開/收合
const expandedIds = ref<string[]>([])
const isExpanded = (id: string) => expandedIds.value.includes(id)

// 題組圖片 signed URL 快取（key = question_id）
const groupImageUrlsMap = ref<Record<string, string[]>>({})

async function toggleExpand(questionId: string, item: any) {
  if (isExpanded(questionId)) {
    expandedIds.value = expandedIds.value.filter((x) => x !== questionId)
    return
  }
  expandedIds.value = [...expandedIds.value, questionId]

  if (groupImageUrlsMap.value[questionId] !== undefined) return

  const assets: Array<{ id: string; bucket_name: string; object_path: string }> =
    item?.questions?.question_groups?.question_assets ?? []

  if (!assets.length) {
    groupImageUrlsMap.value[questionId] = []
    return
  }

  const urls: string[] = []
  for (const asset of assets) {
    const { data } = await supabase.storage
      .from(asset.bucket_name)
      .createSignedUrl(asset.object_path, 3600)
    if (data?.signedUrl) urls.push(data.signedUrl)
  }
  groupImageUrlsMap.value[questionId] = urls
}

// 清理題幹 HTML（移除嵌入選項文字）
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

function getSortedOptions(opts: any[]) {
  return [...(opts ?? [])].sort((a, b) => a.sort_order - b.sort_order)
}

const { copiedId, copyQuestion } = useCopyQuestion()

function handleCopy(item: any) {
  const q = item.questions
  copyQuestion(item.question_id, {
    question_no: q?.question_no,
    question_type: q?.question_type,
    stem_text: q?.stem_text,
    question_options: q?.question_options ?? [],
    groupIntroText: q?.question_groups?.intro_text ?? null,
  })
}

// 移除錯題
const removingId = ref<string | null>(null)
async function removeWrongStat(questionId: string) {
  if (!authStore.user || removingId.value) return
  removingId.value = questionId
  try {
    await quizStore.toggleWrongBook(authStore.user.id, questionId)
    await refresh()
  } finally {
    removingId.value = null
  }
}

// 練習錯題：用第一題的 paper_id 建立 attempt，題目 IDs 存 sessionStorage
// practice 頁面會依 IDs 跨試卷載入正確題目
const startingReview = ref(false)
async function startWrongReview() {
  if (!authStore.user || stats.value.length === 0 || startingReview.value) return
  startingReview.value = true
  try {
    const questions = stats.value.map((s: any) => s.questions).filter(Boolean)
    // paper_id 取第一題（questions.* 已含 paper_id）；practice 頁將依 IDs 跨卷載入
    const paperId = (questions[0] as any)?.paper_id
    if (!paperId) return
    const attempt = await quizStore.startAttempt(authStore.user.id, paperId, 'wrong_review', questions)
    await navigateTo(`/practice/${attempt.id}`)
  } finally {
    startingReview.value = false
  }
}
</script>

<template>
  <div class="max-w-3xl mx-auto px-4 py-8">
    <div class="flex items-center justify-between mb-6">
      <div>
        <h1 class="text-2xl font-bold text-gray-900">錯題本</h1>
        <p class="text-gray-500 mt-1">共 {{ stats.length }} 道錯題</p>
      </div>
      <button
        v-if="stats.length > 0"
        :disabled="startingReview"
        class="bg-primary-600 text-white text-sm font-medium px-4 py-2.5 rounded-lg hover:bg-primary-700 transition-colors disabled:opacity-60"
        @click="startWrongReview"
      >
        {{ startingReview ? '準備中…' : '練習錯題' }}
      </button>
    </div>

    <div v-if="stats.length === 0" class="text-center py-16 text-gray-400">
      <div class="text-5xl mb-4">✅</div>
      <p>目前沒有錯題，繼續保持！</p>
    </div>

    <div v-else class="space-y-3">
      <div
        v-for="item in stats"
        :key="(item as any).question_id"
        class="bg-white rounded-xl border border-gray-200 overflow-hidden"
      >
        <!-- 摘要列（可點擊展開） -->
        <div
          class="flex items-start gap-3 p-4 cursor-pointer hover:bg-gray-50 transition-colors select-none"
          @click="toggleExpand((item as any).question_id, item)"
        >
          <!-- 錯誤次數圓圈 -->
          <div class="shrink-0 w-10 h-10 rounded-full bg-red-100 text-red-600 font-bold text-sm flex items-center justify-center mt-0.5">
            {{ (item as any).wrong_count }}
          </div>

          <!-- 主體 -->
          <div class="flex-1 min-w-0">
            <!-- 來源 + 題號 -->
            <div class="flex flex-wrap items-center gap-1.5 mb-1">
              <span v-if="paperLabel((item as any).questions)" class="text-xs text-primary-600 font-medium">
                {{ paperLabel((item as any).questions) }}
              </span>
              <span class="text-xs text-gray-300">·</span>
              <span class="text-xs text-gray-400">第 {{ (item as any).questions?.question_no }} 題</span>
            </div>
            <!-- 題幹摘要（收合時） -->
            <p
              v-if="!isExpanded((item as any).question_id)"
              class="text-sm text-gray-700 line-clamp-2"
            >
              {{ (item as any).questions?.stem_text }}
            </p>
            <p v-else class="text-sm text-gray-400 italic">已展開</p>
            <!-- 統計資訊 -->
            <div class="flex gap-3 mt-1.5 text-xs text-gray-400">
              <span>錯誤 {{ (item as any).wrong_count }} 次</span>
              <span>最近答錯：{{ formatDate((item as any).last_wrong_at) }}</span>
              <span v-if="(item as any).last_correct_at">最近答對：{{ formatDate((item as any).last_correct_at) }}</span>
            </div>
          </div>

          <!-- 操作按鈕 -->
          <div class="shrink-0 flex items-center gap-1" @click.stop>
            <!-- 複製 -->
            <button
              class="w-8 h-8 rounded-lg flex items-center justify-center transition-colors"
              :class="copiedId === (item as any).question_id
                ? 'text-green-500 bg-green-50'
                : 'text-gray-300 hover:text-gray-500 hover:bg-gray-100'"
              title="複製題目文本"
              @click="handleCopy(item)"
            >
              <span v-if="copiedId === (item as any).question_id" class="text-sm">✓</span>
              <svg v-else xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
                <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
              </svg>
            </button>
            <!-- 移除 -->
            <button
              :disabled="removingId === (item as any).question_id"
              class="w-8 h-8 rounded-lg flex items-center justify-center text-gray-300 hover:text-red-400 hover:bg-red-50 transition-colors text-xs"
              title="從錯題本移除"
              @click="removeWrongStat((item as any).question_id)"
            >
              ✕
            </button>
          </div>

          <!-- 展開指示 -->
          <span
            class="shrink-0 text-gray-400 text-xs mt-1.5 transition-transform duration-200"
            :class="isExpanded((item as any).question_id) ? 'rotate-90' : ''"
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
            v-if="isExpanded((item as any).question_id)"
            class="border-t border-gray-100 px-4 pb-4 pt-4 bg-gray-50/40"
          >
            <!-- 題組說明 -->
            <div
              v-if="(item as any).questions?.question_groups?.intro_text || groupImageUrlsMap[(item as any).question_id]?.length"
              class="bg-amber-50 border border-amber-200 rounded-xl p-4 mb-4"
            >
              <div class="text-xs font-semibold text-amber-700 mb-2 flex items-center gap-1">
                <span>📋</span> 題組說明
              </div>
              <!-- 題組圖片 -->
              <div
                v-if="groupImageUrlsMap[(item as any).question_id]?.length"
                class="flex flex-col gap-2 mb-3"
              >
                <img
                  v-for="(url, i) in groupImageUrlsMap[(item as any).question_id]"
                  :key="i"
                  :src="url"
                  class="max-w-full rounded-lg border border-amber-100"
                  loading="lazy"
                >
              </div>
              <!-- 題組文字 -->
              <p
                v-if="(item as any).questions?.question_groups?.intro_text"
                class="text-sm text-gray-700 whitespace-pre-wrap leading-relaxed"
              >
                {{ (item as any).questions.question_groups.intro_text }}
              </p>
            </div>

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
                :class="opt.is_correct
                  ? 'border-green-400 bg-green-50 text-green-700'
                  : 'border-gray-200 text-gray-500'"
              >
                <span class="font-bold shrink-0">{{ opt.option_key }}.</span>
                <span class="flex-1" v-html="opt.option_html" />
                <span v-if="opt.is_correct" class="shrink-0 text-green-600 font-bold">✓</span>
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

            <!-- AI 詳解 -->
            <AiExplainPanel
              v-if="(item as any).questions?.id"
              :question-id="(item as any).questions.id"
            />
          </div>
        </Transition>
      </div>
    </div>
  </div>
</template>
