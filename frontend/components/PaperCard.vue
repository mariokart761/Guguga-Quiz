<script setup lang="ts">
import type { Paper } from '~/stores/quiz'

defineProps<{ paper: Paper }>()
</script>

<template>
  <NuxtLink
    :to="`/papers/${paper.id}`"
    class="block bg-white rounded-xl border border-gray-200 p-5 hover:shadow-md hover:border-primary-300 transition-all group"
  >
    <div class="flex items-start justify-between gap-3">
      <div class="flex-1 min-w-0">
        <h3 class="font-semibold text-gray-900 group-hover:text-primary-600 transition-colors line-clamp-2">
          {{ paper.title }}
        </h3>
        <div class="flex flex-wrap gap-2 mt-2">
          <span
            v-if="paper.subject"
            class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-700"
          >
            {{ paper.subject }}
          </span>
          <span
            v-if="paper.exam_year"
            class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-600"
          >
            {{ paper.exam_year }} 年
          </span>
          <span
            v-if="paper.term"
            class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-600"
          >
            {{ paper.term }}
          </span>
        </div>
        <p v-if="paper.description" class="mt-2 text-sm text-gray-500 line-clamp-2">
          {{ paper.description }}
        </p>
      </div>
      <div class="text-right shrink-0">
        <div class="text-2xl font-bold text-primary-600">{{ paper.total_questions }}</div>
        <div class="text-xs text-gray-400">題</div>
      </div>
    </div>
  </NuxtLink>
</template>
