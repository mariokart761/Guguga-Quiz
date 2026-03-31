export default defineNuxtRouteMiddleware(async () => {
  const user = useSupabaseUser()
  if (!user.value) {
    return navigateTo('/login')
  }

  const authStore = useAuthStore()
  // 若尚未載入角色，主動 fetch 一次
  if (!authStore.userRole) {
    await authStore.fetchUserRole()
  }

  if (!authStore.isAdmin) {
    // 給使用者看的友善提示，而非直接 throw error page
    return navigateTo('/?error=forbidden')
  }
})
