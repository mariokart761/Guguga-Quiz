<script setup lang="ts">
defineProps<{
  text?: string
}>()
</script>

<template>
  <div class="flex flex-col items-center justify-center gap-3 py-16">
    <div class="w-10 h-10 border-4 border-primary-200 border-t-primary-600 rounded-full animate-spin" />
    <p v-if="text" class="text-sm text-gray-500">{{ text }}</p>
  </div>
</template>
