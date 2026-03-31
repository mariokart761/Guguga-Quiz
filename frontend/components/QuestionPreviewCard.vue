<script setup lang="ts">
defineProps<{
  question: {
    question_no: number
    question_type: 'single' | 'multiple'
    stem_text?: string
    stem_html?: string
    options?: { key: string; html?: string; text?: string }[]
    answer_raw?: string
    images?: { original?: string; path?: string }[]
    group_ref?: number | null
  }
  expanded: boolean
}>()

defineEmits<{ toggle: [] }>()
</script>

<template>
  <div class="bg-white rounded-xl border border-gray-200 overflow-hidden">
    <!-- 摺疊列 -->
    <button
      class="w-full text-left px-4 py-3 flex items-center justify-between hover:bg-gray-50 transition-colors"
      @click="$emit('toggle')"
    >
      <div class="flex items-center gap-3 min-w-0">
        <span class="font-bold text-gray-600 shrink-0">第 {{ question.question_no }} 題</span>
        <span
          class="text-xs px-1.5 py-0.5 rounded shrink-0"
          :class="question.question_type === 'multiple'
            ? 'bg-orange-100 text-orange-600'
            : 'bg-blue-100 text-blue-600'"
        >
          {{ question.question_type === 'multiple' ? '複選' : '單選' }}
        </span>
        <span v-if="question.images?.length" class="text-xs bg-gray-100 text-gray-500 px-1.5 py-0.5 rounded shrink-0">
          🖼 {{ question.images.length }}
        </span>
        <span class="text-sm text-gray-500 truncate">
          {{ question.stem_text?.replace(/^\d+[.、．]\s*/, '')?.slice(0, 60) }}
        </span>
      </div>
      <span class="text-gray-400 text-xs shrink-0 ml-2">{{ expanded ? '▲' : '▼' }}</span>
    </button>

    <!-- 展開內容 -->
    <div v-if="expanded" class="border-t border-gray-100 p-4 bg-gray-50 space-y-4">
      <!-- 題幹 -->
      <div class="prose prose-sm max-w-none text-gray-800" v-html="question.stem_html" />

      <!-- 題目自身圖片 -->
      <div v-if="question.images?.length" class="flex flex-wrap gap-3">
        <div
          v-for="(img, idx) in question.images"
          :key="idx"
          class="rounded-lg overflow-hidden border border-gray-200 bg-white max-w-sm"
        >
          <div class="px-2 py-0.5 text-xs text-gray-400 bg-gray-100 border-b border-gray-200">
            圖片 {{ idx + 1 }}
            <span v-if="img.path" class="text-green-600 ml-1">✓ 已上傳</span>
          </div>
          <img
            :src="img.original || img.path"
            :alt="`第 ${question.question_no} 題圖片 ${idx + 1}`"
            class="max-h-48 object-contain p-2"
            loading="lazy"
            @error="($event.target as HTMLImageElement).style.display = 'none'"
          />
        </div>
      </div>

      <!-- 選項 -->
      <div class="space-y-1.5">
        <div
          v-for="opt in question.options"
          :key="opt.key"
          class="flex items-start gap-2 text-sm px-3 py-2 rounded-lg"
          :class="question.answer_raw?.toUpperCase().split(',').includes(opt.key)
            ? 'bg-green-100 text-green-800 font-medium'
            : 'bg-white border border-gray-200'"
        >
          <span class="font-bold shrink-0">{{ opt.key }}.</span>
          <span class="flex-1" v-html="opt.html || opt.text" />
          <span
            v-if="question.answer_raw?.toUpperCase().split(',').includes(opt.key)"
            class="ml-auto shrink-0 text-green-600"
          >✓</span>
        </div>
      </div>

      <!-- 答案標示 -->
      <div class="flex items-center gap-3 text-xs text-gray-500">
        <span>答案：<strong class="text-gray-700">{{ question.answer_raw || '—' }}</strong></span>
        <span v-if="question.group_ref">題組：{{ question.group_ref }}</span>
      </div>
    </div>
  </div>
</template>
