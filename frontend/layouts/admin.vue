<script setup lang="ts">
definePageMeta({ middleware: 'admin' })

const authStore = useAuthStore()
const route = useRoute()

const navItems = [
  { to: '/admin', label: '首頁', icon: '🏠', exact: true },
  { to: '/admin/imports', label: '試卷匯入', icon: '📥' },
  { to: '/admin/papers', label: '試卷管理', icon: '📄' },
  { to: '/admin/questions', label: '題目管理', icon: '❓' },
]
</script>

<template>
  <div class="min-h-screen bg-gray-100 flex">
    <!-- 側邊欄 -->
    <aside class="w-56 bg-gray-900 text-white flex flex-col shrink-0">
      <div class="p-5 border-b border-gray-700">
        <NuxtLink to="/" class="text-xl font-bold text-white flex items-center gap-2">
          <img src="/apple-touch-icon.png" alt="Logo" class="w-8 h-8" />
          <span>Quiz 後台</span>
        </NuxtLink>
      </div>

      <nav class="flex-1 p-3 space-y-1">
        <NuxtLink
          v-for="item in navItems"
          :key="item.to"
          :to="item.to"
          class="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium text-gray-300 hover:bg-gray-700 hover:text-white transition-colors"
          :class="{ 'bg-gray-700 text-white': item.exact ? route.path === item.to : route.path.startsWith(item.to) }"
        >
          <span>{{ item.icon }}</span>
          <span>{{ item.label }}</span>
        </NuxtLink>
      </nav>

      <div class="p-4 border-t border-gray-700">
        <div class="text-xs text-gray-500 mb-2">{{ authStore.user?.email }}</div>
        <NuxtLink
          to="/"
          class="block text-xs text-gray-400 hover:text-white transition-colors"
        >
          ← 返回前台
        </NuxtLink>
      </div>
    </aside>

    <!-- 主內容 -->
    <div class="flex-1 flex flex-col min-w-0">
      <header class="bg-white shadow-sm border-b border-gray-200 px-6 py-4">
        <h1 class="text-lg font-semibold text-gray-900">管理後台</h1>
      </header>
      <main class="flex-1 p-6 overflow-auto">
        <slot />
      </main>
    </div>
  </div>
</template>
