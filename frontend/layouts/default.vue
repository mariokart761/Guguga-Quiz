<script setup lang="ts">
const authStore = useAuthStore()
const route = useRoute()

const mobileMenuOpen = ref(false)

function toggleMobileMenu() {
  mobileMenuOpen.value = !mobileMenuOpen.value
}

function closeMobileMenu() {
  mobileMenuOpen.value = false
}

watch(() => route.fullPath, () => {
  mobileMenuOpen.value = false
})
</script>

<template>
  <div class="min-h-screen bg-gray-50 flex flex-col">
    <!-- 頂部導覽列 -->
    <header class="bg-white shadow-sm border-b border-gray-200 sticky top-0 z-40">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="flex items-center justify-between h-16">
          <!-- Logo -->
          <NuxtLink to="/" class="flex items-center gap-2 font-bold text-xl text-primary-600" @click="closeMobileMenu">
            <img src="/apple-touch-icon.png" alt="Logo" class="w-10 h-10" />
            <span>Guguga Quiz</span>
          </NuxtLink>

          <!-- 桌面版導覽選單 -->
          <nav v-if="authStore.isLoggedIn" class="hidden md:flex items-center gap-6 text-sm font-medium">
            <NuxtLink
              to="/papers"
              class="text-gray-600 hover:text-primary-600 transition-colors"
              active-class="text-primary-600"
            >題庫</NuxtLink>
            <NuxtLink
              to="/wrong-book"
              class="text-gray-600 hover:text-primary-600 transition-colors"
              active-class="text-primary-600"
            >錯題本</NuxtLink>
            <NuxtLink
              to="/bookmarks"
              class="text-gray-600 hover:text-primary-600 transition-colors"
              active-class="text-primary-600"
            >收藏</NuxtLink>
            <NuxtLink
              to="/profile"
              class="text-gray-600 hover:text-primary-600 transition-colors"
              active-class="text-primary-600"
            >個人</NuxtLink>
            <NuxtLink
              v-if="authStore.isAdmin"
              to="/admin"
              class="text-orange-500 hover:text-orange-600 transition-colors font-semibold"
            >後台</NuxtLink>
          </nav>

          <!-- 右側操作區 -->
          <div class="flex items-center gap-3">
            <template v-if="authStore.isLoggedIn">
              <!-- 桌面版 email + 登出 -->
              <span class="text-sm text-gray-500 hidden md:block">
                {{ authStore.user?.email }}
              </span>
              <button
                class="text-sm text-gray-500 hover:text-red-500 transition-colors px-3 py-1.5 rounded-lg hover:bg-red-50 hidden md:block"
                @click="authStore.signOut()"
              >
                登出
              </button>

              <!-- 手機版漢堡選單按鈕 -->
              <button
                class="md:hidden flex flex-col justify-center items-center w-9 h-9 rounded-lg hover:bg-gray-100 transition-colors gap-1.5"
                aria-label="開啟選單"
                @click="toggleMobileMenu"
              >
                <span
                  class="block w-5 h-0.5 bg-gray-700 transition-transform duration-300"
                  :class="mobileMenuOpen ? 'translate-y-2 rotate-45' : ''"
                />
                <span
                  class="block w-5 h-0.5 bg-gray-700 transition-opacity duration-300"
                  :class="mobileMenuOpen ? 'opacity-0' : ''"
                />
                <span
                  class="block w-5 h-0.5 bg-gray-700 transition-transform duration-300"
                  :class="mobileMenuOpen ? '-translate-y-2 -rotate-45' : ''"
                />
              </button>
            </template>
            <template v-else>
              <NuxtLink
                to="/login"
                class="bg-primary-600 text-white text-sm font-medium px-4 py-2 rounded-lg hover:bg-primary-700 transition-colors"
              >
                登入
              </NuxtLink>
            </template>
          </div>
        </div>
      </div>

      <!-- 手機版展開選單 -->
      <Transition
        enter-active-class="transition-all duration-300 ease-out"
        enter-from-class="opacity-0 -translate-y-2"
        enter-to-class="opacity-100 translate-y-0"
        leave-active-class="transition-all duration-200 ease-in"
        leave-from-class="opacity-100 translate-y-0"
        leave-to-class="opacity-0 -translate-y-2"
      >
        <div
          v-if="mobileMenuOpen && authStore.isLoggedIn"
          class="md:hidden border-t border-gray-100 bg-white"
        >
          <nav class="px-4 py-3 flex flex-col gap-1">
            <NuxtLink
              to="/papers"
              class="flex items-center gap-3 px-3 py-2.5 rounded-lg text-gray-700 hover:bg-primary-50 hover:text-primary-600 transition-colors text-sm font-medium"
              active-class="bg-primary-50 text-primary-600"
            >
              <span>📄</span>題庫
            </NuxtLink>
            <NuxtLink
              to="/wrong-book"
              class="flex items-center gap-3 px-3 py-2.5 rounded-lg text-gray-700 hover:bg-primary-50 hover:text-primary-600 transition-colors text-sm font-medium"
              active-class="bg-primary-50 text-primary-600"
            >
              <span>❌</span>錯題本
            </NuxtLink>
            <NuxtLink
              to="/bookmarks"
              class="flex items-center gap-3 px-3 py-2.5 rounded-lg text-gray-700 hover:bg-primary-50 hover:text-primary-600 transition-colors text-sm font-medium"
              active-class="bg-primary-50 text-primary-600"
            >
              <span>🔖</span>收藏
            </NuxtLink>
            <NuxtLink
              to="/profile"
              class="flex items-center gap-3 px-3 py-2.5 rounded-lg text-gray-700 hover:bg-primary-50 hover:text-primary-600 transition-colors text-sm font-medium"
              active-class="bg-primary-50 text-primary-600"
            >
              <span>👤</span>個人
            </NuxtLink>
            <NuxtLink
              v-if="authStore.isAdmin"
              to="/admin"
              class="flex items-center gap-3 px-3 py-2.5 rounded-lg text-orange-600 hover:bg-orange-50 transition-colors text-sm font-semibold"
              active-class="bg-orange-50"
            >
              <span>⚙️</span>後台管理
            </NuxtLink>
            <div class="border-t border-gray-100 mt-2 pt-2">
              <p class="px-3 py-1 text-xs text-gray-400 truncate">{{ authStore.user?.email }}</p>
              <button
                class="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-red-500 hover:bg-red-50 transition-colors text-sm font-medium"
                @click="authStore.signOut()"
              >
                <span>🚪</span>登出
              </button>
            </div>
          </nav>
        </div>
      </Transition>
    </header>

    <!-- 主內容 -->
    <main class="flex-1">
      <slot />
    </main>

    <!-- 底部 -->
    <footer class="bg-white border-t border-gray-200 py-6 mt-auto">
      <div class="max-w-7xl mx-auto px-4 text-center text-sm text-gray-400">
        © {{ new Date().getFullYear() }} Guguga Quiz
      </div>
    </footer>
  </div>
</template>
