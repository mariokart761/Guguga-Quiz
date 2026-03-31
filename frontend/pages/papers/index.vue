<script setup lang="ts">
definePageMeta({ middleware: 'auth' })

const quizStore = useQuizStore()

const searchQuery = ref('')
const filterSubject = ref('')
const filterYear = ref<number | null>(null)

onMounted(() => quizStore.fetchPapers())

const filteredPapers = computed(() => {
  const q = searchQuery.value.trim().toLowerCase()
  return quizStore.papers.filter((p) => {
    if (filterSubject.value && p.subject !== filterSubject.value) return false
    if (filterYear.value && p.exam_year !== filterYear.value) return false
    if (q) {
      const haystack = [p.title, p.subject, p.exam_year?.toString(), p.description]
        .filter(Boolean).join(' ').toLowerCase()
      if (!haystack.includes(q)) return false
    }
    return true
  })
})

const subjects = computed(() => [
  ...new Set(quizStore.papers.map((p) => p.subject).filter(Boolean)),
])

const years = computed(() => [
  ...new Set(quizStore.papers.map((p) => p.exam_year).filter(Boolean)),
].sort((a, b) => (b as number) - (a as number)))
</script>

<template>
  <div class="max-w-5xl mx-auto px-4 py-8">
    <div class="mb-8">
      <h1 class="text-2xl font-bold text-gray-900">題庫</h1>
      <p class="text-gray-500 mt-1">選擇試卷開始練習</p>
    </div>

    <!-- 搜尋 + 篩選 -->
    <div class="bg-white rounded-xl border border-gray-200 p-4 mb-6 flex flex-col gap-3">
      <!-- 搜尋框 -->
      <div class="relative">
        <span class="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none">🔍</span>
        <input
          v-model="searchQuery"
          type="text"
          placeholder="搜尋試卷名稱、科目、年份…"
          class="w-full text-sm border border-gray-300 rounded-lg pl-9 pr-4 py-2.5 focus:outline-none focus:ring-2 focus:ring-primary-500"
        >
        <button
          v-if="searchQuery"
          class="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
          @click="searchQuery = ''"
        >
          ✕
        </button>
      </div>

      <!-- 下拉篩選 -->
      <div class="flex flex-wrap gap-3">
        <select
          v-model="filterSubject"
          class="text-sm border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary-500"
        >
          <option value="">全部科目</option>
          <option v-for="s in subjects" :key="s" :value="s">{{ s }}</option>
        </select>

        <select
          v-model="filterYear"
          class="text-sm border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary-500"
        >
          <option :value="null">全部年份</option>
          <option v-for="y in years" :key="y" :value="y">{{ y }} 年</option>
        </select>

        <button
          v-if="filterSubject || filterYear || searchQuery"
          class="text-sm text-gray-500 hover:text-gray-700 px-2"
          @click="filterSubject = ''; filterYear = null; searchQuery = ''"
        >
          清除全部
        </button>
      </div>
    </div>

    <!-- 載入中 -->
    <LoadingSpinner v-if="quizStore.papersLoading" text="載入試卷中…" />

    <!-- 試卷列表 -->
    <template v-else>
      <div v-if="filteredPapers.length === 0" class="text-center py-16 text-gray-400">
        <div class="text-5xl mb-4">📭</div>
        <p>沒有符合條件的試卷</p>
      </div>
      <div v-else class="grid gap-4 sm:grid-cols-2">
        <PaperCard
          v-for="paper in filteredPapers"
          :key="paper.id"
          :paper="paper"
        />
      </div>
    </template>
  </div>
</template>
