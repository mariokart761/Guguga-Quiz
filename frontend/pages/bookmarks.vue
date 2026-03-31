<script setup lang="ts">
definePageMeta({ middleware: 'auth' })

const quizStore = useQuizStore()
const authStore = useAuthStore()

const { data: bookmarkList, refresh } = await useAsyncData('bookmarks', async () => {
  if (!authStore.user) return []
  return quizStore.fetchBookmarks(authStore.user.id)
})

const items = computed(() => bookmarkList.value ?? [])

async function removeBookmark(questionId: string) {
  if (!authStore.user) return
  await quizStore.toggleBookmark(authStore.user.id, questionId)
  await refresh()
}

// 展開/收合
const expandedIds = ref<string[]>([])
const isExpanded = (id: string) => expandedIds.value.includes(id)
function toggleExpand(id: string) {
  if (isExpanded(id)) expandedIds.value = expandedIds.value.filter((x) => x !== id)
  else expandedIds.value = [...expandedIds.value, id]
}

// 清理題幹 HTML（移除嵌入的選項文字，如 (A)...(B)...(C)...(D)...）
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

// 考試來源標籤文字
function paperLabel(q: any): string {
  const p = q?.papers
  if (!p) return ''
  const parts: string[] = []
  if (p.exam_year) parts.push(`${p.exam_year} 年`)
  if (p.subject) parts.push(p.subject)
  if (p.title) parts.push(p.title)
  return parts.join(' · ')
}
</script>

<template>
  <div class="max-w-3xl mx-auto px-4 py-8">
    <div class="mb-6">
      <h1 class="text-2xl font-bold text-gray-900">收藏題目</h1>
      <p class="text-gray-500 mt-1">共 {{ items.length }} 道收藏題</p>
    </div>

    <div v-if="items.length === 0" class="text-center py-16 text-gray-400">
      <div class="text-5xl mb-4">⭐</div>
      <p>還沒有收藏任何題目</p>
      <NuxtLink to="/papers" class="mt-4 inline-block text-primary-600 hover:underline text-sm">
        去練習題目
      </NuxtLink>
    </div>

    <div v-else class="space-y-3">
      <div
        v-for="item in items"
        :key="item.question_id"
        class="bg-white rounded-xl border border-gray-200 overflow-hidden"
      >
        <!-- 題目摘要列（可點擊展開） -->
        <div
          class="flex items-start gap-3 p-4 cursor-pointer hover:bg-gray-50 transition-colors select-none"
          @click="toggleExpand(item.question_id)"
        >
          <!-- 題號 -->
          <span class="shrink-0 w-7 h-7 rounded-full bg-yellow-100 text-yellow-700 text-xs font-bold flex items-center justify-center mt-0.5">
            {{ (item as any).questions?.question_no }}
          </span>

          <!-- 主體內容 -->
          <div class="flex-1 min-w-0">
            <!-- 來源標籤 -->
            <div v-if="paperLabel((item as any).questions)" class="text-xs text-primary-600 font-medium mb-1">
              {{ paperLabel((item as any).questions) }}
            </div>
            <!-- 題幹摘要（收合時截斷，展開時由下方完整顯示） -->
            <div
              v-if="!isExpanded(item.question_id)"
              class="prose prose-sm max-w-none text-gray-700 line-clamp-2 text-sm"
              v-html="cleanStemHtml((item as any).questions?.stem_html ?? '')"
            />
            <p v-else class="text-sm text-gray-400 italic">
              已展開
            </p>
          </div>

          <!-- 右側操作 -->
          <div class="shrink-0 flex items-center gap-1.5" @click.stop>
            <button
              class="text-yellow-400 hover:text-gray-400 transition-colors text-lg leading-none"
              title="取消收藏"
              @click="removeBookmark(item.question_id)"
            >
              ★
            </button>
          </div>

          <!-- 展開指示 -->
          <span
            class="shrink-0 text-gray-400 text-xs mt-1 transition-transform duration-200"
            :class="isExpanded(item.question_id) ? 'rotate-90' : ''"
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
            v-if="isExpanded(item.question_id)"
            class="border-t border-gray-100 px-4 pb-4 pt-4 bg-gray-50/40"
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
          </div>
        </Transition>
      </div>
    </div>
  </div>
</template>
