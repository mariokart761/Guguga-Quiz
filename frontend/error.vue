<script setup lang="ts">
defineProps<{
  error: { statusCode: number; statusMessage?: string; message?: string }
}>()

function handleError() {
  clearError({ redirect: '/' })
}
</script>

<template>
  <div class="min-h-screen bg-gray-50 flex items-center justify-center px-4">
    <div class="text-center">
      <div class="text-7xl font-bold text-gray-200 mb-4">{{ error.statusCode }}</div>
      <h1 class="text-2xl font-bold text-gray-900 mb-2">
        {{ error.statusCode === 404 ? '頁面不存在' : error.statusCode === 403 ? '無存取權限' : '發生錯誤' }}
      </h1>
      <p class="text-gray-500 mb-8">
        {{ error.statusMessage || error.message || '很抱歉，發生了未知的錯誤。' }}
      </p>
      <button
        class="bg-primary-600 text-white font-medium px-6 py-3 rounded-xl hover:bg-primary-700 transition-colors"
        @click="handleError"
      >
        返回首頁
      </button>
    </div>
  </div>
</template>
