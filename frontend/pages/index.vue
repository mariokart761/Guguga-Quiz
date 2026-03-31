<script setup lang="ts">
const user = useSupabaseUser()

// 已登入的話導向試卷列表，否則到登入頁
onMounted(() => {
  if (user.value) {
    navigateTo('/papers')
  } else {
    navigateTo('/login')
  }
})
</script>

<template>
  <div />
</template>
