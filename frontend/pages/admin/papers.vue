<script setup lang="ts">
definePageMeta({ layout: 'admin', middleware: 'admin' })

const { apiGet, apiPost, apiPatch, apiDelete } = useApi()

const papers = ref<any[]>([])
const loading = ref(false)
const error = ref('')
const success = ref('')

async function loadPapers() {
  loading.value = true
  try {
    papers.value = await apiGet<any[]>('/api/papers')
  } finally {
    loading.value = false
  }
}

onMounted(loadPapers)

async function togglePublish(paper: any) {
  try {
    if (paper.is_published) {
      await apiPost(`/api/papers/${paper.id}/unpublish`)
      success.value = `已取消發布：${paper.title}`
    } else {
      await apiPost(`/api/papers/${paper.id}/publish`)
      success.value = `已發布：${paper.title}`
    }
    await loadPapers()
  } catch (e: any) {
    error.value = e.message
  }
}

async function deletePaper(paper: any) {
  if (!confirm(`確定要刪除「${paper.title}」嗎？此操作無法還原。`)) return
  try {
    await apiDelete(`/api/papers/${paper.id}`)
    success.value = '刪除成功'
    await loadPapers()
  } catch (e: any) {
    error.value = e.message
  }
}
</script>

<template>
  <div>
    <div class="flex items-center justify-between mb-6">
      <h2 class="text-xl font-bold text-gray-900">試卷管理</h2>
      <NuxtLink
        to="/admin/imports"
        class="text-sm text-primary-600 hover:underline"
      >
        + 新增（匯入 HTML）
      </NuxtLink>
    </div>

    <div v-if="error" class="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-600">
      {{ error }}
    </div>
    <div v-if="success" class="mb-4 p-3 bg-green-50 border border-green-200 rounded-lg text-sm text-green-700">
      {{ success }}
    </div>

    <LoadingSpinner v-if="loading" />

    <div v-else-if="papers.length === 0" class="text-center py-16 text-gray-400">
      尚無試卷
    </div>

    <div v-else class="bg-white rounded-xl border border-gray-200 overflow-hidden">
      <table class="w-full text-sm">
        <thead class="bg-gray-50 border-b border-gray-200">
          <tr>
            <th class="text-left px-4 py-3 font-medium text-gray-600">標題</th>
            <th class="text-left px-4 py-3 font-medium text-gray-600">科目</th>
            <th class="text-left px-4 py-3 font-medium text-gray-600">年份</th>
            <th class="text-center px-4 py-3 font-medium text-gray-600">題數</th>
            <th class="text-center px-4 py-3 font-medium text-gray-600">狀態</th>
            <th class="text-right px-4 py-3 font-medium text-gray-600">操作</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-100">
          <tr v-for="paper in papers" :key="paper.id" class="hover:bg-gray-50">
            <td class="px-4 py-3 font-medium text-gray-900">
              {{ paper.title }}
            </td>
            <td class="px-4 py-3 text-gray-500">{{ paper.subject || '-' }}</td>
            <td class="px-4 py-3 text-gray-500">{{ paper.exam_year || '-' }}</td>
            <td class="px-4 py-3 text-center text-gray-700">{{ paper.total_questions }}</td>
            <td class="px-4 py-3 text-center">
              <span
                class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium"
                :class="paper.is_published ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'"
              >
                {{ paper.is_published ? '已發布' : '草稿' }}
              </span>
            </td>
            <td class="px-4 py-3 text-right">
              <div class="flex items-center justify-end gap-2">
                <button
                  class="text-xs font-medium transition-colors"
                  :class="paper.is_published ? 'text-yellow-600 hover:text-yellow-700' : 'text-green-600 hover:text-green-700'"
                  @click="togglePublish(paper)"
                >
                  {{ paper.is_published ? '取消發布' : '發布' }}
                </button>
                <NuxtLink
                  :to="`/admin/questions?paper_id=${paper.id}`"
                  class="text-xs text-blue-600 hover:underline"
                >
                  管理題目
                </NuxtLink>
                <button
                  class="text-xs text-red-500 hover:text-red-600"
                  @click="deletePaper(paper)"
                >
                  刪除
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
