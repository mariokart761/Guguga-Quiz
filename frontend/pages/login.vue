<script setup lang="ts">
definePageMeta({ layout: false })

const authStore = useAuthStore()
const route = useRoute()
const user = useSupabaseUser()

const email = ref('')
const loading = ref(false)
const sent = ref(false)
const error = ref('')

const redirectTo = computed(() =>
  (route.query.redirect as string) || '/papers'
)

// 若已登入，直接跳轉
watchEffect(() => {
  if (user.value) {
    navigateTo(redirectTo.value)
  }
})

async function handleEmailLogin() {
  if (!email.value) return
  loading.value = true
  error.value = ''
  const { error: e } = await authStore.signInWithEmail(email.value)
  loading.value = false
  if (e) {
    error.value = e.message
  } else {
    sent.value = true
  }
}

async function handleGoogleLogin() {
  loading.value = true
  const { error: e } = await authStore.signInWithGoogle()
  if (e) {
    error.value = e.message
    loading.value = false
  }
}
</script>

<template>
  <div class="min-h-screen bg-gradient-to-br from-primary-50 via-white to-blue-50 flex items-center justify-center px-4">
    <div class="w-full max-w-md">
      <!-- Logo -->
      <div class="text-center mb-8">
        <div class="text-6xl mb-4">📚</div>
        <h1 class="text-3xl font-bold text-gray-900">Guguga Quiz</h1>
        <p class="mt-2 text-gray-500">線上測驗練習平台</p>
      </div>

      <div class="bg-white rounded-2xl shadow-lg border border-gray-100 p-8">
        <template v-if="!sent">
          <h2 class="text-xl font-semibold text-gray-800 mb-6 text-center">登入帳號</h2>

          <!-- Email OTP 登入 -->
          <form class="space-y-4" @submit.prevent="handleEmailLogin">
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1.5">Email</label>
              <input
                v-model="email"
                type="email"
                placeholder="your@email.com"
                required
                class="w-full px-4 py-3 border border-gray-300 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent transition"
              />
            </div>

            <div v-if="error" class="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
              {{ error }}
            </div>

            <button
              type="submit"
              :disabled="loading"
              class="w-full bg-primary-600 text-white font-medium py-3 rounded-xl hover:bg-primary-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <span v-if="loading">傳送中…</span>
              <span v-else>傳送魔法連結</span>
            </button>
          </form>

          <div class="relative my-5">
            <div class="absolute inset-0 flex items-center">
              <div class="w-full border-t border-gray-200" />
            </div>
            <div class="relative flex justify-center">
              <span class="px-3 bg-white text-xs text-gray-400">或</span>
            </div>
          </div>

          <!-- Google 登入 -->
          <button
            class="w-full flex items-center justify-center gap-3 border border-gray-300 rounded-xl py-3 text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
            @click="handleGoogleLogin"
          >
            <svg class="w-5 h-5" viewBox="0 0 24 24">
              <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
              <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
              <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" />
              <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" />
            </svg>
            使用 Google 帳號登入
          </button>
        </template>

        <!-- 已傳送 Magic Link -->
        <template v-else>
          <div class="text-center py-4">
            <div class="text-5xl mb-4">✉️</div>
            <h2 class="text-xl font-semibold text-gray-800 mb-2">確認你的信箱</h2>
            <p class="text-gray-500 text-sm leading-relaxed">
              我們已傳送登入連結至<br />
              <span class="font-medium text-gray-700">{{ email }}</span>
            </p>
            <p class="text-xs text-gray-400 mt-4">找不到？請檢查垃圾郵件</p>
            <button
              class="mt-6 text-sm text-primary-600 hover:text-primary-700 font-medium"
              @click="sent = false"
            >
              重新傳送
            </button>
          </div>
        </template>
      </div>
    </div>
  </div>
</template>
