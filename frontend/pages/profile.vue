<script setup lang="ts">
definePageMeta({ middleware: 'auth' })

const quizStore = useQuizStore()
const authStore = useAuthStore()
const supabase = useSupabaseClient()

const { data: attempts } = await useAsyncData('my-attempts', async () => {
  if (!authStore.user) return []
  return quizStore.fetchMyAttempts(authStore.user.id)
})

const recentAttempts = computed(() => (attempts.value ?? []).slice(0, 10))

const stats = computed(() => {
  const all = attempts.value ?? []
  const total = all.length
  const avgScore = total > 0
    ? Math.round(all.reduce((sum: number, a: any) => sum + (a.score ?? 0), 0) / total)
    : 0
  const totalCorrect = all.reduce((sum: number, a: any) => sum + a.correct_count, 0)
  const totalWrong = all.reduce((sum: number, a: any) => sum + a.wrong_count, 0)
  const accuracy = totalCorrect + totalWrong > 0
    ? Math.round(totalCorrect / (totalCorrect + totalWrong) * 100)
    : 0
  return { total, avgScore, accuracy }
})

function modeLabel(mode: string) {
  return { practice: '練習', mock_exam: '模擬考', wrong_review: '錯題練習' }[mode] ?? mode
}
</script>

<template>
  <div class="max-w-3xl mx-auto px-4 py-8">
    <!-- 個人資訊 -->
    <div class="bg-white rounded-2xl border border-gray-200 p-6 mb-6 flex items-center gap-4">
      <div class="w-14 h-14 rounded-full bg-primary-100 flex items-center justify-center text-2xl font-bold text-primary-600">
        {{ authStore.user?.email?.[0]?.toUpperCase() }}
      </div>
      <div>
        <p class="font-semibold text-gray-900">{{ authStore.user?.email }}</p>
        <span
          class="text-xs px-2 py-0.5 rounded-full font-medium mt-1 inline-block"
          :class="authStore.isAdmin ? 'bg-orange-100 text-orange-600' : 'bg-gray-100 text-gray-500'"
        >
          {{ authStore.isAdmin ? '管理員' : '一般使用者' }}
        </span>
      </div>
    </div>

    <!-- 統計摘要 -->
    <div class="grid grid-cols-3 gap-4 mb-8">
      <div class="bg-white rounded-xl border border-gray-200 p-4 text-center">
        <div class="text-2xl font-bold text-primary-600">{{ stats.total }}</div>
        <div class="text-xs text-gray-500 mt-1">測驗次數</div>
      </div>
      <div class="bg-white rounded-xl border border-gray-200 p-4 text-center">
        <div class="text-2xl font-bold text-primary-600">{{ stats.avgScore }}</div>
        <div class="text-xs text-gray-500 mt-1">平均分數</div>
      </div>
      <div class="bg-white rounded-xl border border-gray-200 p-4 text-center">
        <div class="text-2xl font-bold text-primary-600">{{ stats.accuracy }}%</div>
        <div class="text-xs text-gray-500 mt-1">整體正確率</div>
      </div>
    </div>

    <!-- 最近記錄 -->
    <h2 class="text-lg font-semibold text-gray-800 mb-4">最近測驗記錄</h2>

    <div v-if="recentAttempts.length === 0" class="text-center py-8 text-gray-400 text-sm">
      還沒有測驗記錄
    </div>

    <div v-else class="space-y-3">
      <NuxtLink
        v-for="attempt in recentAttempts"
        :key="(attempt as any).id"
        :to="`/result/${(attempt as any).id}`"
        class="block bg-white rounded-xl border border-gray-200 p-4 hover:border-primary-300 hover:shadow-sm transition-all"
      >
        <div class="flex items-center justify-between">
          <div class="flex-1 min-w-0">
            <p class="font-medium text-gray-800 truncate">
              {{ (attempt as any).papers?.title }}
            </p>
            <div class="flex gap-3 mt-1 text-xs text-gray-400">
              <span>{{ modeLabel((attempt as any).mode) }}</span>
              <span>{{ new Date((attempt as any).submitted_at).toLocaleDateString('zh-TW') }}</span>
            </div>
          </div>
          <div class="text-right ml-4 shrink-0">
            <div
              class="text-xl font-bold"
              :class="{
                'text-green-600': (attempt as any).score >= 80,
                'text-yellow-500': (attempt as any).score >= 60 && (attempt as any).score < 80,
                'text-red-500': (attempt as any).score < 60,
              }"
            >
              {{ (attempt as any).score ?? '-' }}
            </div>
            <div class="text-xs text-gray-400">分</div>
          </div>
        </div>
      </NuxtLink>
    </div>

    <!-- 登出按鈕 -->
    <div class="mt-10 text-center">
      <button
        class="text-sm text-red-500 hover:text-red-600 hover:underline"
        @click="authStore.signOut()"
      >
        登出帳號
      </button>
    </div>
  </div>
</template>
