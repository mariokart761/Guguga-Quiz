<script setup lang="ts">
import { ref, computed } from 'vue'
import { useCopyQuestion } from '~/composables/useCopyQuestion'
import type { Question } from '~/stores/quiz'

interface Props {
  question: Question
  showAnswer?: boolean
  selectedAnswers?: string[]
  bookmarked?: boolean
  mode?: 'practice' | 'mock_exam' | 'wrong_review'
  groupIntroText?: string | null
}

const props = withDefaults(defineProps<Props>(), {
  showAnswer: false,
  selectedAnswers: () => [],
  bookmarked: false,
  mode: 'practice',
  groupIntroText: null,
})

const emit = defineEmits<{
  select: [key: string]
  toggleBookmark: []
}>()

const { copiedId, copyQuestion } = useCopyQuestion()

function handleCopy() {
  copyQuestion(props.question.id, {
    question_no: props.question.question_no,
    question_type: props.question.question_type,
    stem_text: props.question.stem_text,
    question_options: props.question.question_options,
    groupIntroText: props.groupIntroText,
  })
}

const correctKeys = computed(() =>
  props.question.question_options
    .filter((o) => o.is_correct)
    .map((o) => o.option_key),
)

const isCorrect = computed(() => {
  if (!props.showAnswer || props.selectedAnswers.length === 0) return null
  return (
    props.selectedAnswers.length === correctKeys.value.length &&
    props.selectedAnswers.every((k) => correctKeys.value.includes(k))
  )
})

function getOptionClass(key: string) {
  const isSelected = props.selectedAnswers.includes(key)
  const isCorrectOption = correctKeys.value.includes(key)

  if (!props.showAnswer) {
    return isSelected
      ? 'border-primary-500 bg-primary-50 text-primary-700'
      : 'border-gray-200 hover:border-primary-300 hover:bg-gray-50'
  }

  if (isCorrectOption) return 'border-green-500 bg-green-50 text-green-700'
  if (isSelected && !isCorrectOption) return 'border-red-400 bg-red-50 text-red-700'
  return 'border-gray-200 text-gray-400'
}

const sortedOptions = computed(() =>
  [...props.question.question_options].sort((a, b) => a.sort_order - b.sort_order),
)

// 從題幹 HTML 移除夾雜在其中的選項文字（如 (A)...(B)...(C)...(D)...）
// 某些來源的 stem_html 包含整段題目（含選項），需前端清理後再顯示
const cleanStemHtml = computed(() => {
  const html = props.question.stem_html
  if (!html) return html

  // 比對選項起始符：(A) / (B) / (C) / (D) 及全形版本 （A）等
  const optionPat = /[\(（][A-Da-d][\)）]/

  if (import.meta.client) {
    const doc = new DOMParser().parseFromString(html, 'text/html')

    function stripOptions(node: Node): boolean {
      if (node.nodeType === Node.TEXT_NODE) {
        const text = node.textContent ?? ''
        const m = optionPat.exec(text)
        if (m) {
          node.textContent = text.slice(0, m.index)
          return true
        }
        return false
      }
      if (node.nodeType === Node.ELEMENT_NODE) {
        const children = Array.from(node.childNodes)
        for (let i = 0; i < children.length; i++) {
          if (stripOptions(children[i])) {
            for (let j = children.length - 1; j > i; j--) {
              node.removeChild(children[j])
            }
            return true
          }
        }
      }
      return false
    }

    stripOptions(doc.body)
    return doc.body.innerHTML
  }

  // SSR fallback：直接對 HTML 字串做正則截斷
  return html.replace(/[\(（][A-Da-d][\)）][\s\S]*$/, '')
})
</script>

<template>
  <div class="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
    <!-- 題號與類型 -->
    <div class="flex items-center justify-between mb-4">
      <div class="flex items-center gap-2">
        <span class="text-lg font-bold text-gray-700">第 {{ question.question_no }} 題</span>
        <span
          class="text-xs px-2 py-0.5 rounded-full font-medium"
          :class="question.question_type === 'multiple' ? 'bg-orange-100 text-orange-600' : 'bg-blue-100 text-blue-600'"
        >
          {{ question.question_type === 'multiple' ? '複選' : '單選' }}
        </span>
        <span
          v-if="question.difficulty"
          class="text-xs px-2 py-0.5 rounded-full font-medium"
          :class="{
            'bg-green-100 text-green-600': question.difficulty === 'easy',
            'bg-yellow-100 text-yellow-600': question.difficulty === 'medium',
            'bg-red-100 text-red-600': question.difficulty === 'hard',
          }"
        >
          {{ { easy: '易', medium: '中', hard: '難' }[question.difficulty] }}
        </span>
      </div>

      <!-- 右側工具列 -->
      <div class="flex items-center gap-1.5">
        <!-- 複製按鈕 -->
        <button
          class="w-8 h-8 rounded-lg flex items-center justify-center transition-colors text-sm"
          :class="copiedId === question.id
            ? 'text-green-500 bg-green-50'
            : 'text-gray-300 hover:text-gray-500 hover:bg-gray-100'"
          title="複製題目文本"
          @click="handleCopy"
        >
          <span v-if="copiedId === question.id">✓</span>
          <svg v-else xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
            <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
          </svg>
        </button>
        <!-- 收藏按鈕 -->
        <button
          class="text-xl transition-transform hover:scale-110"
          :class="bookmarked ? 'text-yellow-400' : 'text-gray-300 hover:text-yellow-300'"
          @click="emit('toggleBookmark')"
        >
          {{ bookmarked ? '★' : '☆' }}
        </button>
      </div>
    </div>

    <!-- 題幹 -->
    <div
      class="prose prose-base max-w-none text-gray-800 mb-5 leading-relaxed"
      v-html="cleanStemHtml"
    />

    <!-- 選項 -->
    <div class="space-y-2">
      <button
        v-for="opt in sortedOptions"
        :key="opt.id"
        :disabled="showAnswer"
        class="w-full text-left px-4 py-3 rounded-lg border-2 transition-all cursor-pointer"
        :class="getOptionClass(opt.option_key)"
        @click="emit('select', opt.option_key)"
      >
        <span class="font-bold mr-2">{{ opt.option_key }}.</span>
        <span v-html="opt.option_html" />
        <span v-if="showAnswer && correctKeys.includes(opt.option_key)" class="ml-2 text-green-600">✓</span>
        <span v-if="showAnswer && selectedAnswers.includes(opt.option_key) && !correctKeys.includes(opt.option_key)" class="ml-2 text-red-500">✗</span>
      </button>
    </div>

    <!-- 作答結果 -->
    <div
      v-if="showAnswer && selectedAnswers.length > 0"
      class="mt-4 p-3 rounded-lg text-sm font-medium"
      :class="isCorrect ? 'bg-green-50 text-green-700 border border-green-200' : 'bg-red-50 text-red-700 border border-red-200'"
    >
      {{ isCorrect ? '✓ 答對了！' : `✗ 答錯了，正確答案：${correctKeys.join(', ')}` }}
    </div>

    <!-- 解析 -->
    <div
      v-if="showAnswer && question.explanation_html"
      class="mt-4 p-4 bg-blue-50 border border-blue-200 rounded-lg"
    >
      <div class="text-xs font-semibold text-blue-600 mb-2">解析</div>
      <div class="prose prose-sm max-w-none text-gray-700" v-html="question.explanation_html" />
    </div>

    <!-- AI 詳解 -->
    <AiExplainPanel
      v-if="showAnswer"
      :question-id="question.id"
    />
  </div>
</template>
