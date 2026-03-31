<script setup lang="ts">
definePageMeta({ layout: 'admin', middleware: 'admin' })

const route = useRoute()
const { apiGet, apiPatch, apiDelete } = useApi()

const paperId = computed(() => route.query.paper_id as string | undefined)
const questions = ref<any[]>([])
const loading = ref(false)
const editingId = ref<string | null>(null)
const editForm = ref<any>({})
const error = ref('')
const success = ref('')

async function loadQuestions() {
  loading.value = true
  try {
    const url = paperId.value
      ? `/api/questions?paper_id=${paperId.value}`
      : '/api/questions'
    questions.value = await apiGet<any[]>(url)
  } finally {
    loading.value = false
  }
}

onMounted(loadQuestions)

function startEdit(q: any) {
  editingId.value = q.id
  editForm.value = {
    stem_html: q.stem_html,
    explanation_html: q.explanation_html ?? '',
    difficulty: q.difficulty ?? '',
    question_type: q.question_type,
  }
}

function cancelEdit() {
  editingId.value = null
  editForm.value = {}
}

async function saveEdit(questionId: string) {
  try {
    await apiPatch(`/api/questions/${questionId}`, {
      ...editForm.value,
      difficulty: editForm.value.difficulty || null,
      explanation_html: editForm.value.explanation_html || null,
    })
    success.value = '儲存成功'
    editingId.value = null
    await loadQuestions()
  } catch (e: any) {
    error.value = e.message
  }
}

async function deleteQuestion(q: any) {
  if (!confirm(`確定刪除第 ${q.question_no} 題嗎？`)) return
  try {
    await apiDelete(`/api/questions/${q.id}`)
    success.value = '刪除成功'
    await loadQuestions()
  } catch (e: any) {
    error.value = e.message
  }
}
</script>

<template>
  <div>
    <div class="flex items-center gap-3 mb-6">
      <NuxtLink to="/admin/papers" class="text-gray-400 hover:text-gray-600 text-sm">← 試卷列表</NuxtLink>
      <h2 class="text-xl font-bold text-gray-900">題目管理</h2>
      <span v-if="paperId" class="text-sm text-gray-400">（篩選中）</span>
    </div>

    <div v-if="error" class="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-600">{{ error }}</div>
    <div v-if="success" class="mb-4 p-3 bg-green-50 border border-green-200 rounded-lg text-sm text-green-700">{{ success }}</div>

    <LoadingSpinner v-if="loading" text="載入題目中…" />

    <div v-else-if="questions.length === 0" class="text-center py-16 text-gray-400">尚無題目</div>

    <div v-else class="space-y-3">
      <div
        v-for="q in questions"
        :key="q.id"
        class="bg-white rounded-xl border border-gray-200 overflow-hidden"
      >
        <!-- 題目摘要列 -->
        <div class="flex items-start justify-between p-4">
          <div class="flex-1 min-w-0">
            <div class="flex items-center gap-2 mb-1">
              <span class="font-bold text-gray-600">第 {{ q.question_no }} 題</span>
              <span
                class="text-xs px-1.5 py-0.5 rounded"
                :class="q.question_type === 'multiple' ? 'bg-orange-100 text-orange-600' : 'bg-blue-100 text-blue-600'"
              >
                {{ q.question_type === 'multiple' ? '複選' : '單選' }}
              </span>
              <span
                v-if="q.difficulty"
                class="text-xs px-1.5 py-0.5 rounded"
                :class="{
                  'bg-green-100 text-green-600': q.difficulty === 'easy',
                  'bg-yellow-100 text-yellow-600': q.difficulty === 'medium',
                  'bg-red-100 text-red-600': q.difficulty === 'hard',
                }"
              >
                {{ { easy: '易', medium: '中', hard: '難' }[q.difficulty] }}
              </span>
            </div>
            <p class="text-sm text-gray-600 line-clamp-2">{{ q.stem_text }}</p>
          </div>

          <div class="flex items-center gap-2 ml-3 shrink-0">
            <button
              v-if="editingId !== q.id"
              class="text-xs text-blue-600 hover:underline"
              @click="startEdit(q)"
            >
              編輯
            </button>
            <button
              class="text-xs text-red-500 hover:underline"
              @click="deleteQuestion(q)"
            >
              刪除
            </button>
          </div>
        </div>

        <!-- 編輯表單 -->
        <div
          v-if="editingId === q.id"
          class="border-t border-gray-100 p-4 bg-gray-50 space-y-3"
        >
          <div>
            <label class="block text-xs font-medium text-gray-600 mb-1">題型</label>
            <select
              v-model="editForm.question_type"
              class="w-full text-sm border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary-500"
            >
              <option value="single">單選</option>
              <option value="multiple">複選</option>
            </select>
          </div>
          <div>
            <label class="block text-xs font-medium text-gray-600 mb-1">難度</label>
            <select
              v-model="editForm.difficulty"
              class="w-full text-sm border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary-500"
            >
              <option value="">未設定</option>
              <option value="easy">易</option>
              <option value="medium">中</option>
              <option value="hard">難</option>
            </select>
          </div>
          <div>
            <label class="block text-xs font-medium text-gray-600 mb-1">題幹 HTML</label>
            <textarea
              v-model="editForm.stem_html"
              rows="4"
              class="w-full text-sm border border-gray-300 rounded-lg px-3 py-2 font-mono focus:outline-none focus:ring-2 focus:ring-primary-500"
            />
          </div>
          <div>
            <label class="block text-xs font-medium text-gray-600 mb-1">解析 HTML（選填）</label>
            <textarea
              v-model="editForm.explanation_html"
              rows="3"
              class="w-full text-sm border border-gray-300 rounded-lg px-3 py-2 font-mono focus:outline-none focus:ring-2 focus:ring-primary-500"
            />
          </div>
          <div class="flex justify-end gap-2">
            <button
              class="text-sm px-3 py-1.5 border border-gray-300 rounded-lg hover:bg-gray-100"
              @click="cancelEdit"
            >
              取消
            </button>
            <button
              class="text-sm px-4 py-1.5 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
              @click="saveEdit(q.id)"
            >
              儲存
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
