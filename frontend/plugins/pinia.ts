// Pinia 與 auth store 初始化
// @nuxtjs/pinia 會自動引入 stores，此 plugin 確保 auth store 在 app 啟動時初始化
export default defineNuxtPlugin(async () => {
  const authStore = useAuthStore()
  // 確保登入狀態在 SSR 與 CSR 都同步
  await authStore.fetchUserRole()
})
