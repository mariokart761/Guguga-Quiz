<script setup lang="ts">
definePageMeta({ layout: 'admin', middleware: 'admin' })

const { apiGet } = useApi()

const stats = ref({
  papers: 0,
  publishedPapers: 0,
  pendingImports: 0,
})

onMounted(async () => {
  try {
    const [papers, imports] = await Promise.all([
      apiGet<any[]>('/api/papers'),
      apiGet<any[]>('/api/imports'),
    ])
    stats.value.papers = papers.length
    stats.value.publishedPapers = papers.filter((p) => p.is_published).length
    stats.value.pendingImports = imports.filter((j: any) =>
      ['pending', 'processing', 'review'].includes(j.status)
    ).length
  } catch {}
})
</script>

<template>
  <div>
    <h2 class="text-xl font-bold text-gray-900 mb-6">後台總覽</h2>

    <div class="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
      <div class="bg-white rounded-xl border border-gray-200 p-5">
        <div class="text-3xl font-bold text-primary-600">{{ stats.papers }}</div>
        <div class="text-sm text-gray-500 mt-1">試卷總數</div>
      </div>
      <div class="bg-white rounded-xl border border-gray-200 p-5">
        <div class="text-3xl font-bold text-green-600">{{ stats.publishedPapers }}</div>
        <div class="text-sm text-gray-500 mt-1">已發布試卷</div>
      </div>
      <div class="bg-white rounded-xl border border-gray-200 p-5">
        <div class="text-3xl font-bold text-orange-500">{{ stats.pendingImports }}</div>
        <div class="text-sm text-gray-500 mt-1">待處理匯入</div>
      </div>
    </div>

    <div class="grid gap-4 sm:grid-cols-2">
      <NuxtLink
        to="/admin/imports"
        class="bg-white rounded-xl border border-gray-200 p-5 hover:border-primary-300 hover:shadow-sm transition-all block"
      >
        <div class="text-2xl mb-2">📥</div>
        <h3 class="font-semibold text-gray-800">試卷匯入</h3>
        <p class="text-sm text-gray-500 mt-1">上傳 HTML 試卷，解析並發布</p>
      </NuxtLink>
      <NuxtLink
        to="/admin/papers"
        class="bg-white rounded-xl border border-gray-200 p-5 hover:border-primary-300 hover:shadow-sm transition-all block"
      >
        <div class="text-2xl mb-2">📄</div>
        <h3 class="font-semibold text-gray-800">試卷管理</h3>
        <p class="text-sm text-gray-500 mt-1">檢視、編輯、發布或刪除試卷</p>
      </NuxtLink>
      <NuxtLink
        to="/admin/questions"
        class="bg-white rounded-xl border border-gray-200 p-5 hover:border-primary-300 hover:shadow-sm transition-all block"
      >
        <div class="text-2xl mb-2">❓</div>
        <h3 class="font-semibold text-gray-800">題目管理</h3>
        <p class="text-sm text-gray-500 mt-1">編輯題幹、選項、解析</p>
      </NuxtLink>
    </div>
  </div>
</template>
