<script setup lang="ts">
definePageMeta({ middleware: 'auth' })

const route = useRoute()
const quizStore = useQuizStore()
const authStore = useAuthStore()

const paperId = route.params.id as string
const { paper, questions } = await quizStore.fetchPaperWithQuestions(paperId)

if (!paper) {
  throw createError({ statusCode: 404, statusMessage: '試卷不存在' })
}

const practiceCount = ref(Math.min(20, paper.total_questions))
const showPracticeModal = ref(false)

async function startPractice(mode: 'practice' | 'mock_exam') {
  if (!authStore.user) return
  let selectedQuestions = [...questions]

  if (mode === 'practice') {
    // 隨機抽題（spread 避免改動原陣列）
    selectedQuestions = [...questions]
      .sort(() => Math.random() - 0.5)
      .slice(0, practiceCount.value)
  }

  const attempt = await quizStore.startAttempt(
    authStore.user.id,
    paperId,
    mode,
    selectedQuestions,
  )
  await navigateTo(`/practice/${attempt.id}`)
}
</script>

<template>
  <div class="max-w-3xl mx-auto px-4 py-8">
    <!-- 麵包屑 -->
    <nav class="text-sm text-gray-500 mb-6">
      <NuxtLink to="/papers" class="hover:text-primary-600">題庫</NuxtLink>
      <span class="mx-2">/</span>
      <span class="text-gray-700">{{ paper.title }}</span>
    </nav>

    <!-- 試卷資訊卡 -->
    <div class="bg-white rounded-2xl border border-gray-200 p-6 shadow-sm mb-6">
      <div class="flex items-start gap-4">
        <div class="text-4xl">📄</div>
        <div class="flex-1 min-w-0">
          <h1 class="text-xl font-bold text-gray-900">{{ paper.title }}</h1>
          <div class="flex flex-wrap gap-2 mt-2">
            <span v-if="paper.subject" class="tag-blue">{{ paper.subject }}</span>
            <span v-if="paper.exam_year" class="tag-gray">{{ paper.exam_year }} 年</span>
            <span v-if="paper.term" class="tag-gray">{{ paper.term }}</span>
          </div>
          <p v-if="paper.description" class="text-sm text-gray-500 mt-3">{{ paper.description }}</p>
        </div>
        <div class="text-right shrink-0">
          <div class="text-3xl font-bold text-primary-600">{{ paper.total_questions }}</div>
          <div class="text-xs text-gray-400">道題目</div>
        </div>
      </div>
    </div>

    <!-- 模式選擇 -->
    <div class="grid gap-4 sm:grid-cols-2">
      <!-- 練習模式 -->
      <div class="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
        <div class="text-3xl mb-3">🎯</div>
        <h3 class="font-semibold text-gray-800 mb-1">練習模式</h3>
        <p class="text-sm text-gray-500 mb-4">隨機抽題，作答後立即顯示正解</p>

        <div class="flex items-center gap-2 mb-4">
          <label class="text-sm text-gray-600">題數</label>
          <input
            v-model.number="practiceCount"
            type="number"
            :min="1"
            :max="paper.total_questions"
            class="w-20 text-sm border border-gray-300 rounded-lg px-2 py-1.5 text-center focus:outline-none focus:ring-2 focus:ring-primary-500"
          />
          <span class="text-sm text-gray-400">/ {{ paper.total_questions }}</span>
        </div>

        <button
          class="w-full bg-primary-600 text-white font-medium py-2.5 rounded-lg hover:bg-primary-700 transition-colors text-sm"
          @click="startPractice('practice')"
        >
          開始練習
        </button>
      </div>

      <!-- 模擬考模式 -->
      <div class="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
        <div class="text-3xl mb-3">⏱️</div>
        <h3 class="font-semibold text-gray-800 mb-1">模擬考模式</h3>
        <p class="text-sm text-gray-500 mb-4">整份作答，倒數計時，交卷後才顯示結果</p>
        <div class="text-sm text-gray-500 mb-4">
          共 {{ paper.total_questions }} 題 · 建議時間 {{ Math.ceil(paper.total_questions * 2) }} 分鐘
        </div>

        <button
          class="w-full bg-orange-500 text-white font-medium py-2.5 rounded-lg hover:bg-orange-600 transition-colors text-sm"
          @click="startPractice('mock_exam')"
        >
          開始模擬考
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.tag-blue {
  @apply inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-700;
}
.tag-gray {
  @apply inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-600;
}
</style>
