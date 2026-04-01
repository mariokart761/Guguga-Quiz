<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import { marked } from 'marked'
import { useAiExplain } from '~/composables/useAiExplain'

type AiExplainLanguage = 'zh-TW' | 'en'

interface Props {
  questionId: string
  language?: AiExplainLanguage
}

const props = withDefaults(defineProps<Props>(), {
  language: 'zh-TW',
})

const { loading, error, explanation, cached, fetchExplanation, reset } = useAiExplain()

const isOpen = ref(false)

async function toggle() {
  if (isOpen.value) {
    isOpen.value = false
    return
  }
  isOpen.value = true
  if (!explanation.value && !loading.value) {
    await fetchExplanation(props.questionId, props.language)
  }
}

async function retry() {
  reset()
  await fetchExplanation(props.questionId, props.language)
}

// 當 questionId 改變時（換題），重置狀態
watch(() => props.questionId, () => {
  isOpen.value = false
  reset()
})

// 設定 marked renderer，讓數字清單、粗體、換行在 prose 中更清晰
const renderer = new marked.Renderer()

// 開啟清單時加上間距
renderer.list = (token) => {
  const tag = token.ordered ? 'ol' : 'ul'
  return `<${tag} class="my-2 space-y-1">${token.items.map((item) => marked.parseInline(item.text) !== undefined ? `<li>${marked.parseInline(item.text)}</li>` : '').join('')}</${tag}>`
}

marked.use({
  renderer,
  breaks: true,    // 單換行也視為 <br>
  gfm: true,       // GitHub Flavored Markdown
})

const renderedHtml = computed<string>(() => {
  if (!explanation.value) return ''
  return marked.parse(explanation.value) as string
})
</script>

<template>
  <div class="mt-3">
    <!-- 觸發按鈕 -->
    <button
      class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-all select-none"
      :class="isOpen
        ? 'bg-violet-100 text-violet-700 hover:bg-violet-200'
        : 'bg-gray-100 text-gray-600 hover:bg-violet-50 hover:text-violet-600'"
      @click="toggle"
    >
      <span class="text-base leading-none">✨</span>
      <span>AI 詳解</span>
      <span
        v-if="cached && isOpen"
        class="text-xs px-1.5 py-0.5 bg-violet-200 text-violet-600 rounded-full leading-none"
      >快取</span>
      <span
        class="text-xs opacity-50 ml-0.5 transition-transform duration-200"
        :class="isOpen ? 'rotate-90' : ''"
      >▶</span>
    </button>

    <!-- 詳解面板 -->
    <Transition
      enter-active-class="transition-all duration-300 ease-out"
      enter-from-class="opacity-0 -translate-y-2"
      enter-to-class="opacity-100 translate-y-0"
      leave-active-class="transition-all duration-200 ease-in"
      leave-from-class="opacity-100 translate-y-0"
      leave-to-class="opacity-0 -translate-y-2"
    >
      <div
        v-if="isOpen"
        class="mt-2 rounded-xl border border-violet-200 bg-violet-50 overflow-hidden"
      >
        <!-- 標題列 -->
        <div class="flex items-center justify-between px-4 py-2.5 bg-violet-100/70 border-b border-violet-200">
          <div class="flex items-center gap-1.5 text-xs font-semibold text-violet-700">
            <span>✨</span>
            <span>AI 詳解</span>
            <span
              v-if="cached"
              class="px-1.5 py-0.5 bg-violet-200 text-violet-600 rounded-full font-medium"
            >快取命中</span>
          </div>
          <span class="text-xs text-violet-400">GPT-4o mini</span>
        </div>

        <!-- 內容區 -->
        <div class="px-4 py-4">
          <!-- 載入中 -->
          <div v-if="loading" class="flex items-center gap-2 text-sm text-violet-600 py-1">
            <svg class="w-4 h-4 animate-spin shrink-0" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
            </svg>
            <span>AI 正在生成詳解，請稍候…</span>
          </div>

          <!-- 錯誤 -->
          <div v-else-if="error" class="text-sm text-red-600 py-1">
            <p class="mb-2">{{ error }}</p>
            <button
              class="text-xs px-3 py-1.5 bg-red-100 hover:bg-red-200 text-red-600 rounded-lg transition-colors"
              @click="retry"
            >
              重試
            </button>
          </div>

          <!-- Markdown 詳解內容 -->
          <div
            v-else-if="renderedHtml"
            class="prose prose-sm max-w-none
                   prose-headings:text-violet-800 prose-headings:font-semibold
                   prose-strong:text-gray-800
                   prose-li:text-gray-700
                   prose-p:text-gray-700 prose-p:leading-relaxed
                   prose-ol:pl-5 prose-ul:pl-5
                   prose-hr:border-violet-200"
            v-html="renderedHtml"
          />
        </div>
      </div>
    </Transition>
  </div>
</template>
