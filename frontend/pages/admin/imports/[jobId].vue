<script setup lang="ts">
definePageMeta({ layout: 'admin', middleware: 'admin' })

const route = useRoute()
const { apiGet, apiPost } = useApi()

const jobId = route.params.jobId as string

const { data, refresh } = await useAsyncData('import-job', async () => {
  return apiGet<{ job: any; items: any[] }>(`/api/imports/${jobId}`)
})

const job = computed(() => data.value?.job)
const items = computed(() => data.value?.items ?? [])

const paperMeta = computed(() =>
  items.value.find((i) => i.item_type === 'paper_meta')?.normalized_json ?? {}
)

const groups = computed(() =>
  items.value
    .filter((i) => i.item_type === 'group')
    .map((i) => i.normalized_json)
    .sort((a: any, b: any) => a.group_no - b.group_no)
)

const questions = computed(() =>
  items.value
    .filter((i) => i.item_type === 'question')
    .map((i) => i.normalized_json)
    .sort((a: any, b: any) => a.question_no - b.question_no)
)

// 依 group_ref 分組題目，方便預覽
const groupedQuestions = computed(() => {
  const map = new Map<number | null, any[]>()
  map.set(null, [])
  for (const g of groups.value) {
    map.set(g.group_no, [])
  }
  for (const q of questions.value) {
    const key = q.group_ref ?? null
    if (!map.has(key)) map.set(key, [])
    map.get(key)!.push(q)
  }
  return map
})

const expandedQuestion = ref<number | null>(null)
const publishing = ref(false)
const error = ref('')

async function publish() {
  if (!confirm('確定發布此試卷？')) return
  publishing.value = true
  error.value = ''
  try {
    await apiPost(`/api/imports/${jobId}/publish`)
    await navigateTo('/admin/imports')
  } catch (e: any) {
    error.value = e.message ?? '發布失敗'
    publishing.value = false
  }
}

function toggleQuestion(no: number) {
  expandedQuestion.value = expandedQuestion.value === no ? null : no
}
</script>

<template>
  <div>
    <!-- 頂部導覽 -->
    <div class="flex items-center gap-3 mb-6">
      <NuxtLink to="/admin/imports" class="text-gray-400 hover:text-gray-600 text-sm">← 返回</NuxtLink>
      <h2 class="text-xl font-bold text-gray-900">匯入預覽</h2>
    </div>

    <div v-if="!job" class="text-gray-400">載入中…</div>

    <template v-else>
      <!-- 試卷基本資訊 -->
      <div class="bg-white rounded-xl border border-gray-200 p-5 mb-5">
        <div class="flex items-start justify-between gap-4">
          <div class="min-w-0">
            <h3 class="font-semibold text-gray-900 text-lg leading-snug">
              {{ paperMeta.title || '（未解析到標題）' }}
            </h3>
            <div class="flex flex-wrap gap-x-4 gap-y-1 mt-2 text-sm text-gray-500">
              <span v-if="paperMeta.subject">科目：{{ paperMeta.subject }}</span>
              <span v-if="paperMeta.exam_year">年份：{{ paperMeta.exam_year }}</span>
              <span>題數：{{ questions.length }}</span>
              <span v-if="groups.length > 0">題組：{{ groups.length }} 組</span>
            </div>
          </div>

          <div class="flex items-center gap-2 shrink-0">
            <span
              class="text-sm px-3 py-1 rounded-full font-medium"
              :class="{
                'bg-yellow-100 text-yellow-700': job.status === 'review',
                'bg-green-100 text-green-700': job.status === 'published',
                'bg-red-100 text-red-600': job.status === 'failed',
              }"
            >
              {{ { review: '待審核', published: '已發布', failed: '失敗' }[job.status] ?? job.status }}
            </span>
            <button
              v-if="job.status === 'review'"
              :disabled="publishing"
              class="bg-green-600 text-white text-sm font-medium px-4 py-2 rounded-lg hover:bg-green-700 transition-colors disabled:opacity-50"
              @click="publish"
            >
              {{ publishing ? '發布中…' : '發布試卷' }}
            </button>
          </div>
        </div>

        <div v-if="error" class="mt-3 text-sm text-red-600 bg-red-50 rounded-lg px-3 py-2">{{ error }}</div>
      </div>

      <!-- 無題組的題目 -->
      <template v-if="groupedQuestions.get(null)?.length">
        <h3 class="text-sm font-semibold text-gray-600 mb-3">
          獨立題目（共 {{ groupedQuestions.get(null)!.length }} 題）
        </h3>
        <div class="space-y-2 mb-6">
          <QuestionPreviewCard
            v-for="q in groupedQuestions.get(null)"
            :key="q.question_no"
            :question="q"
            :expanded="expandedQuestion === q.question_no"
            @toggle="toggleQuestion(q.question_no)"
          />
        </div>
      </template>

      <!-- 題組 -->
      <template v-for="g in groups" :key="g.group_no">
        <div class="mb-6">
          <!-- 題組標頭 -->
          <div class="border border-gray-300 rounded-xl overflow-hidden mb-2">
            <div class="bg-amber-50 border-b border-amber-100 px-4 py-3 flex items-center justify-between">
              <div class="flex items-center gap-3">
                <span class="inline-flex items-center justify-center w-6 h-6 rounded-full bg-amber-500 text-white text-xs font-bold">
                  {{ g.group_no }}
                </span>
                <span class="font-semibold text-gray-800">
                  題組 {{ g.group_no }}
                  <span class="font-normal text-gray-500 text-sm ml-2">
                    第 {{ g.start_no }}–{{ g.end_no }} 題
                    （{{ groupedQuestions.get(g.group_no)?.length ?? 0 }} 題）
                  </span>
                </span>
              </div>
            </div>

            <!-- 題組說明 + 圖片 -->
            <div class="p-4 bg-white">
              <div
                v-if="g.intro_text"
                class="text-sm text-gray-700 mb-3 leading-relaxed"
              >
                {{ g.intro_text }}
              </div>

              <!-- 題組圖片 -->
              <div v-if="g.images?.length > 0" class="flex flex-wrap gap-3">
                <div
                  v-for="(img, idx) in g.images"
                  :key="idx"
                  class="rounded-lg overflow-hidden border border-gray-200 bg-gray-50 max-w-md"
                >
                  <div class="px-2 py-1 text-xs text-gray-400 bg-gray-100 border-b border-gray-200">
                    題組圖片 {{ idx + 1 }}
                    <span v-if="img.path" class="ml-1 text-green-600">（已上傳）</span>
                    <span v-else class="ml-1 text-orange-500">（原始 URL）</span>
                  </div>
                  <img
                    :src="img.original || img.path"
                    :alt="`題組 ${g.group_no} 圖片 ${idx + 1}`"
                    class="max-h-64 object-contain p-2"
                    loading="lazy"
                    @error="($event.target as HTMLImageElement).style.display = 'none'"
                  />
                </div>
              </div>
            </div>
          </div>

          <!-- 題組的題目 -->
          <div class="space-y-2 pl-4 border-l-2 border-amber-200">
            <QuestionPreviewCard
              v-for="q in groupedQuestions.get(g.group_no)"
              :key="q.question_no"
              :question="q"
              :expanded="expandedQuestion === q.question_no"
              @toggle="toggleQuestion(q.question_no)"
            />
          </div>
        </div>
      </template>
    </template>
  </div>
</template>
