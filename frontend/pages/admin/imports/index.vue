<script setup lang="ts">
definePageMeta({ layout: 'admin', middleware: 'admin' })

const { apiGet, apiUpload, apiPost, apiDelete } = useApi()

const jobs = ref<any[]>([])
const loading = ref(false)
const uploading = ref(false)
const htmlFileInput = ref<HTMLInputElement>()
const jsonFileInput = ref<HTMLInputElement>()
const error = ref('')
const success = ref('')

async function loadJobs() {
  loading.value = true
  try {
    jobs.value = await apiGet<any[]>('/api/imports')
  } finally {
    loading.value = false
  }
}

onMounted(loadJobs)

async function handleUpload(event: Event, type: 'html' | 'json') {
  const file = (event.target as HTMLInputElement).files?.[0]
  if (!file) return
  uploading.value = true
  error.value = ''
  success.value = ''
  try {
    const endpoint = type === 'json' ? '/api/imports/upload-json' : '/api/imports/upload'
    const result = await apiUpload<{ job_id: string }>(endpoint, file)
    success.value = `上傳成功，任務 ID：${result.job_id}，正在解析…`
    await loadJobs()
  } catch (e: any) {
    error.value = e.message || '上傳失敗'
  } finally {
    uploading.value = false
    if (htmlFileInput.value) htmlFileInput.value.value = ''
    if (jsonFileInput.value) jsonFileInput.value.value = ''
  }
}

async function handleProcess(jobId: string) {
  try {
    await apiPost(`/api/imports/${jobId}/process`)
    await loadJobs()
  } catch (e: any) {
    error.value = e.message
  }
}

async function handlePublish(jobId: string) {
  if (!confirm('確定要發布此試卷嗎？')) return
  try {
    await apiPost(`/api/imports/${jobId}/publish`)
    success.value = '發布成功！'
    await loadJobs()
  } catch (e: any) {
    error.value = e.message
  }
}

async function handleDelete(jobId: string) {
  if (!confirm('確定要刪除此匯入任務嗎？')) return
  try {
    await apiDelete(`/api/imports/${jobId}`)
    await loadJobs()
  } catch (e: any) {
    error.value = e.message
  }
}

const statusLabel: Record<string, string> = {
  pending: '等待中',
  processing: '解析中',
  review: '待審核',
  published: '已發布',
  failed: '失敗',
}

const statusColor: Record<string, string> = {
  pending: 'bg-gray-100 text-gray-600',
  processing: 'bg-blue-100 text-blue-600',
  review: 'bg-yellow-100 text-yellow-700',
  published: 'bg-green-100 text-green-700',
  failed: 'bg-red-100 text-red-600',
}

function fileTypeLabel(path: string) {
  return path?.toLowerCase().endsWith('.json') ? 'JSON' : 'HTML'
}
</script>

<template>
  <div>
    <div class="flex items-center justify-between mb-6">
      <h2 class="text-xl font-bold text-gray-900">試卷匯入</h2>

      <div class="flex items-center gap-2">
        <!-- HTML 上傳 -->
        <label class="cursor-pointer">
          <input
            ref="htmlFileInput"
            type="file"
            accept=".html"
            class="hidden"
            :disabled="uploading"
            @change="handleUpload($event, 'html')"
          />
          <span
            class="inline-flex items-center gap-1.5 border border-gray-300 text-gray-700 text-sm font-medium px-4 py-2.5 rounded-lg hover:bg-gray-50 transition-colors"
            :class="{ 'opacity-50 cursor-not-allowed': uploading }"
          >
            <span class="text-xs font-bold text-orange-500">HTML</span>
            <span>{{ uploading ? '上傳中…' : '上傳試卷' }}</span>
          </span>
        </label>

        <!-- JSON 上傳 -->
        <label class="cursor-pointer">
          <input
            ref="jsonFileInput"
            type="file"
            accept=".json"
            class="hidden"
            :disabled="uploading"
            @change="handleUpload($event, 'json')"
          />
          <span
            class="inline-flex items-center gap-1.5 bg-primary-600 text-white text-sm font-medium px-4 py-2.5 rounded-lg hover:bg-primary-700 transition-colors"
            :class="{ 'opacity-50 cursor-not-allowed': uploading }"
          >
            <span class="text-xs font-bold text-primary-200">JSON</span>
            <span>{{ uploading ? '上傳中…' : '上傳試卷' }}</span>
          </span>
        </label>
      </div>
    </div>

    <div v-if="error" class="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-600">
      {{ error }}
    </div>
    <div v-if="success" class="mb-4 p-3 bg-green-50 border border-green-200 rounded-lg text-sm text-green-700">
      {{ success }}
    </div>

    <LoadingSpinner v-if="loading" />

    <div v-else-if="jobs.length === 0" class="text-center py-16 text-gray-400">
      <div class="text-4xl mb-3">📭</div>
      <p>還沒有匯入任務</p>
      <p class="text-sm mt-1">上傳 HTML 或 JSON 格式的試卷開始匯入</p>
    </div>

    <div v-else class="bg-white rounded-xl border border-gray-200 overflow-hidden">
      <table class="w-full text-sm">
        <thead class="bg-gray-50 border-b border-gray-200">
          <tr>
            <th class="text-left px-4 py-3 font-medium text-gray-600">格式</th>
            <th class="text-left px-4 py-3 font-medium text-gray-600">檔案路徑</th>
            <th class="text-left px-4 py-3 font-medium text-gray-600">狀態</th>
            <th class="text-left px-4 py-3 font-medium text-gray-600">建立時間</th>
            <th class="text-right px-4 py-3 font-medium text-gray-600">操作</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-100">
          <tr v-for="job in jobs" :key="job.id" class="hover:bg-gray-50">
            <td class="px-4 py-3">
              <span
                class="inline-flex items-center px-2 py-0.5 rounded text-xs font-bold"
                :class="fileTypeLabel(job.source_file_path) === 'JSON'
                  ? 'bg-primary-100 text-primary-700'
                  : 'bg-orange-100 text-orange-700'"
              >
                {{ fileTypeLabel(job.source_file_path) }}
              </span>
            </td>
            <td class="px-4 py-3">
              <NuxtLink
                :to="`/admin/imports/${job.id}`"
                class="text-primary-600 hover:underline font-mono text-xs"
              >
                {{ job.source_file_path }}
              </NuxtLink>
              <p v-if="job.error_message" class="text-xs text-red-500 mt-0.5">
                {{ job.error_message }}
              </p>
            </td>
            <td class="px-4 py-3">
              <span
                class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium"
                :class="statusColor[job.status]"
              >
                {{ statusLabel[job.status] ?? job.status }}
              </span>
            </td>
            <td class="px-4 py-3 text-gray-400 text-xs">
              {{ new Date(job.created_at).toLocaleString('zh-TW') }}
            </td>
            <td class="px-4 py-3 text-right">
              <div class="flex items-center justify-end gap-2">
                <button
                  v-if="job.status === 'failed' || job.status === 'pending'"
                  class="text-xs text-blue-600 hover:underline"
                  @click="handleProcess(job.id)"
                >
                  重新解析
                </button>
                <button
                  v-if="job.status === 'review'"
                  class="text-xs text-green-600 hover:underline font-medium"
                  @click="handlePublish(job.id)"
                >
                  發布
                </button>
                <NuxtLink
                  v-if="job.status === 'review'"
                  :to="`/admin/imports/${job.id}`"
                  class="text-xs text-gray-600 hover:underline"
                >
                  預覽
                </NuxtLink>
                <button
                  class="text-xs text-red-500 hover:underline"
                  @click="handleDelete(job.id)"
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
